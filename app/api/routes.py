import asyncio
import logging
from fastapi import APIRouter, Request, Response
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from datetime import datetime
from prometheus_client import generate_latest, Counter, Histogram

from app.config import TELEGRAM_TOKEN, ASSET_MAP
from app.services.price_service import PriceService
from app.services.circuit_breaker import CircuitBreaker
from app.engines.technical_engine import TechnicalEngine
from app.engines.macro_engine import MacroEngine
from app.engines.sentiment_engine import SentimentEngine
from app.engines.news_engine import NewsEngine
from app.engines.asset_intelligence import AssetIntelligenceEngine
from app.engines.probability_engine import ProbabilityEngine
from app.engines.explanation_engine import ExplanationEngine
from app.engines.data_validation import DataValidationEngine, DataValidationError
from app.engines.regime_engine import RegimeEngine
from app.engines.correlation_engine import CorrelationEngine
from app.engines.trade_quality_engine import TradeQualityEngine
from app.services.supabase_client import log_prediction
from app.engines.calibration import MODEL_VERSION

router = APIRouter()
logger = logging.getLogger(__name__)
bot_app = Application.builder().token(TELEGRAM_TOKEN).build()

REQUEST_COUNT = Counter('bot_requests_total', 'Total bot requests')
REQUEST_LATENCY = Histogram('bot_request_latency_seconds', 'Request latency')
ERROR_COUNT = Counter('bot_errors_total', 'Total errors')

price_cb = CircuitBreaker(fail_threshold=3, timeout=60)
macro_cb = CircuitBreaker(fail_threshold=2, timeout=30)

price_service = PriceService()
macro_engine = MacroEngine()
sent_engine = SentimentEngine()
news_engine = NewsEngine()
regime_engine = RegimeEngine()
correlation_engine = CorrelationEngine()
asset_intelligence = AssetIntelligenceEngine()
probability_engine = ProbabilityEngine()
trade_quality = TradeQualityEngine()

async def fetch_all_data(asset):
    macro_task = asyncio.create_task(asyncio.to_thread(macro_cb.call, macro_engine.fetch))
    sent_task = asyncio.create_task(asyncio.to_thread(sent_engine.fetch))
    news_task = asyncio.create_task(news_engine.fetch_async(asset))
    
    # FIXED: Unpack 3 arguments instead of 2 to match macro_engine.fetch return signature
    macro_data, macro_ts, _ = await macro_task
    sent_data = await sent_task
    news_items = await news_task
    return macro_data, macro_ts, sent_data, news_items

async def handle_asset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    asset = update.message.text.split()[0][1:].lower()
    if asset not in ASSET_MAP:
        return
    REQUEST_COUNT.inc()
    start = datetime.utcnow()
    try:
        price_data = await asyncio.to_thread(price_cb.call, price_service.get_price, asset)
        hist = await asyncio.to_thread(price_service.get_historical_data, asset, 60)
        price_data = DataValidationEngine.validate_price(price_data, hist)

        tech_indicators = await asyncio.to_thread(TechnicalEngine.calculate, hist, price_data.current_price)
        tech_score = await asyncio.to_thread(TechnicalEngine.score, tech_indicators)

        macro_data, macro_ts, sent_data, news_items = await fetch_all_data(asset)
        macro_score = await asyncio.to_thread(macro_engine.score, macro_data, asset, {})
        macro_extra = macro_engine.get_extra()

        # Ensure macro_extra is a dict with expected keys
        if not macro_extra or not isinstance(macro_extra, dict):
            macro_extra = {
                "bias": "N/A",
                "confidence": 0.0,
                "regime": "N/A",
                "news": "No news",
                "quote": ""
            }
        # Ensure all keys exist
        required_keys = {"bias", "confidence", "regime", "news", "quote"}
        for key in required_keys:
            if key not in macro_extra:
                macro_extra[key] = "N/A" if key != "confidence" else 0.0

        sent_score = await asyncio.to_thread(sent_engine.score, sent_data, asset)
        news_score = await asyncio.to_thread(news_engine.score, news_items)

        regime_probs = await asyncio.to_thread(regime_engine.classify, macro_data, sent_data)
        dominant_regime = max(regime_probs, key=regime_probs.get)

        corr_score = await asyncio.to_thread(correlation_engine.get_correlation_score, asset, price_data.current_price)
        scores = asset_intelligence.combine(asset, tech_score, macro_score, sent_score, news_score, dominant_regime)

        atr_ratio = tech_indicators.atr / price_data.current_price if price_data.current_price > 0 else 0.01
        prob_result = probability_engine.calculate(scores, atr_ratio, asset, regime_probs, corr_score, abs(news_score))

        trade_q = trade_quality.score(asset, tech_score, macro_score, sent_score, news_score, atr_ratio, corr_score, prob_result["confidence"])

        explanation = ExplanationEngine.generate(
            asset, price_data.current_price, scores, prob_result["bullish_probability"], prob_result["confidence"],
            dominant_regime, macro_data, sent_data, corr_score, tech_indicators=tech_indicators, news_items=news_items,
            source_reliabilities={"Yahoo": 0.85, "FRED": 0.98, "Gemini": 0.95}, proxy_used=price_data.proxy_used,
            macro_timestamp=macro_ts.get('dxy'), news_timestamp=datetime.utcnow(), sent_timestamp=datetime.utcnow(),
            model_version=prob_result.get('model_version', MODEL_VERSION), sample_size=prob_result.get('sample_size', 0),
            macro_extra=macro_extra
        )
        
        explanation += f"\n\n📈 *Calculated Alpha Quality:* {trade_q*100:.0f}%"
        if trade_q > 0.68:
            explanation += " ✅ High Conviction Execution Profile"
        elif trade_q > 0.48:
            explanation += " ⚡ Neutral Conviction Strategy Holding"
        else:
            explanation += " ⏳ Low Conviction Signal Warning"

        await update.message.reply_text(explanation, parse_mode="Markdown")

        try:
            log_prediction(
                asset=asset, price=price_data.current_price, bull_prob=prob_result["bullish_probability"],
                confidence=prob_result["confidence"], composite=scores.composite, tech=tech_score, macro=macro_score,
                sent=sent_score, news=news_score, regime=dominant_regime, regime_probs=regime_probs, atr_ratio=atr_ratio,
                corr_score=corr_score, horizon='1d', gate="BULLISH" if scores.composite > 0.05 else "BEARISH" if scores.composite < -0.05 else "NEUTRAL",
                model_version=prob_result.get('model_version', MODEL_VERSION), sample_size=prob_result.get('sample_size', 0),
                data_source=price_data.provider, proxy_used=price_data.proxy_used
            )
        except Exception as e:
            logger.warning(f"Auditing tracking engine log skipped: {e}")

    except DataValidationError as e:
        await update.message.reply_text(f"⚠️ Inbound Validation Rejection: {e}")
    except Exception as e:
        ERROR_COUNT.inc()
        logger.error(f"Execution Error processing requests on signature /{asset}: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Error: {e}")

    REQUEST_LATENCY.observe((datetime.utcnow() - start).total_seconds())

# Register all command handlers
for cmd in ASSET_MAP.keys():
    bot_app.add_handler(CommandHandler(cmd, handle_asset_command))

@router.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        update = Update.de_json(data, bot_app.bot)
        if update:
            await bot_app.process_update(update)
    except Exception as e:
        logger.error(f"Error executing inbound parsing workflows inside webhook interface: {e}")
    return {"status": "ok"}

@router.get("/health")
async def health():
    return {"status": "healthy"}

@router.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
