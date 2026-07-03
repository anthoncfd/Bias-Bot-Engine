import asyncio
import logging
from fastapi import APIRouter, Request, Response
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from datetime import datetime
import pandas as pd
import html
import re
import httpx
from prometheus_client import generate_latest, Counter, Histogram

from app.config import TELEGRAM_TOKEN, ASSET_MAP, RAPIDAPI_KEY
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

VALID_TOKEN = TELEGRAM_TOKEN if (TELEGRAM_TOKEN and ":" in TELEGRAM_TOKEN) else "123456:ABCdefGhIJKlmNoPQRsTUVwxyZ"
bot_app = Application.builder().token(VALID_TOKEN).build()

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

def convert_md_to_html(text: str) -> str:
    """Converts basic Markdown markers into stable HTML strings to avoid Telegram parsing failures."""
    if not text:
        return ""
    text = html.escape(text)
    text = text.replace("&amp;#x27;", "'").replace("&amp;quot;", '"')
    text = re.sub(r'\*(.*?)\*', r'<b>\1</b>', text)
    text = re.sub(r'_(.*?)_', r'<i>\1</i>', text)
    return text

def fetch_metal_sentinel_spot_gold() -> pd.DataFrame:
    """
    Fallback mechanism leveraging the Metal Sentinel API on RapidAPI.
    Fetches raw spot gold (XAU) vs USD history, guaranteeing zero reliance on futures contracts.
    """
    url = "https://metal-sentinel.p.rapidapi.com/metal-history"
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY or "YOUR-FALLBACK-KEY",
        "x-rapidapi-host": "metal-sentinel.p.rapidapi.com"
    }
    # Requests 60 days of spot gold depth explicitly mapped to historical close arrays
    params = {"metal": "gold", "currency": "USD", "days": "60"}
    
    with httpx.Client() as client:
        response = client.get(url, headers=headers, params=params, timeout=12.0)
        
    if response.status_code != 200:
        raise RuntimeError(f"Metal Sentinel Spot API returned bad status code: {response.status_code}")
        
    data = response.json()
    history = data.get("history", []) # Expected raw timeline array from provider
    
    records = []
    for entry in history:
        # Expected response structure: {"date": "YYYY-MM-DD", "price": 2345.67}
        date_val = pd.to_datetime(entry.get("date"))
        price_val = float(entry.get("price", 0))
        
        if price_val > 0:
            records.append({
                "Date": date_val, 
                "Open": price_val, 
                "High": price_val, 
                "Low": price_val, 
                "Close": price_val, 
                "Volume": 0
            })
            
    df = pd.DataFrame(records)
    if df.empty:
        raise ValueError("Metal Sentinel Spot historical transformation generated empty dataframe.")
        
    return df.set_index("Date").sort_index()

async def fetch_all_data(asset):
    macro_task = asyncio.create_task(asyncio.to_thread(macro_cb.call, macro_engine.fetch))
    sent_task = asyncio.create_task(asyncio.to_thread(sent_engine.fetch))
    news_task = asyncio.create_task(news_engine.fetch_async(asset))
    macro_data, macro_ts = await macro_task
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
        price_data = price_cb.call(price_service.get_price, asset)
        
        # Resilient Spot Data Pipeline Routing Layer
        try:
            hist = price_service.get_historical_data(asset, days=60)
        except Exception as e:
            logger.warning(f"Primary historical service failed for {asset}: {e}. Calling secondary spot layer...")
            if asset == "xauusd":
                hist = fetch_metal_sentinel_spot_gold()
            else:
                # Core forex pairs fall back to native spot ticker tracks safely
                import yfinance as yf
                hist = yf.download(f"{asset.upper()}=X", period="60d")
                
            if hist.empty:
                raise RuntimeError(f"Primary and secondary spot historical systems both failed for {asset}")

        price_data = DataValidationEngine.validate_price(price_data, hist)

        tech_indicators = TechnicalEngine.calculate(hist, price_data.current_price)
        tech_score = TechnicalEngine.score(tech_indicators)

        macro_data, macro_ts, sent_data, news_items = await fetch_all_data(asset)
        macro_score = macro_engine.score(macro_data, asset, {})
        sent_score = sent_engine.score(sent_data, asset)
        news_score = news_engine.score(news_items)

        regime_probs = regime_engine.classify(macro_data, sent_data)
        dominant_regime = max(regime_probs, key=regime_probs.get)

        corr_score = correlation_engine.get_correlation_score(asset, price_data.current_price)
        scores = asset_intelligence.combine(asset, tech_score, macro_score, sent_score, news_score, dominant_regime)

        atr_ratio = tech_indicators.atr / price_data.current_price if price_data.current_price > 0 else 0.01
        prob_result = probability_engine.calculate(scores, atr_ratio, asset, regime_probs, corr_score, abs(news_score))

        trade_q = trade_quality.score(asset, tech_score, macro_score, sent_score, news_score, atr_ratio, corr_score, prob_result["confidence"])

        if hasattr(macro_ts, "get"):
            raw_macro_ts = macro_ts.get('dxy') or macro_ts.get('fed')
        else:
            raw_macro_ts = macro_ts

        if raw_macro_ts:
            try:
                clean_macro_ts = pd.to_datetime(raw_macro_ts).to_pydatetime()
            except Exception:
                clean_macro_ts = datetime.utcnow()
        else:
            clean_macro_ts = datetime.utcnow()

        explanation = ExplanationEngine.generate(
            asset, price_data.current_price, scores, prob_result["bullish_probability"], prob_result["confidence"],
            dominant_regime, macro_data, sent_data, corr_score, tech_indicators=tech_indicators, news_items=news_items,
            source_reliabilities={"GoldAPI": 0.98, "MetalSentinel": 0.97, "FRED": 0.98, "Gemini": 0.95}, proxy_used=price_data.proxy_used,
            macro_timestamp=clean_macro_ts, news_timestamp=datetime.utcnow(), sent_timestamp=datetime.utcnow(),
            model_version=prob_result.get('model_version', MODEL_VERSION), sample_size=prob_result.get('sample_size', 0)
        )
        
        html_explanation = convert_md_to_html(explanation)
        
        html_explanation += f"\n\n📈 <b>Calculated Alpha Quality:</b> {trade_q*100:.0f}%"
        if trade_q > 0.68:
            html_explanation += " ✅ High Conviction Execution Profile"
        elif trade_q > 0.48:
            html_explanation += " ⚡ Neutral Conviction Strategy Holding"
        else:
            html_explanation += " ⏳ Low Conviction Signal Warning"

        await update.message.reply_text(html_explanation, parse_mode="HTML")

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
            logger.warning(f"Auditing tracking engine prediction log bypassed: {e}")

    except DataValidationError as e:
        await update.message.reply_text(f"⚠️ Inbound Validation Rejection: {html.escape(str(e))}")
    except Exception as e:
        ERROR_COUNT.inc()
        logger.error(f"Execution Error processing requests on signature /{asset}: {e}", exc_info=True)
        await update.message.reply_text(f"System processing error parsing {asset.upper()} asset matrix. Reason: {html.escape(str(e))}")
        
    REQUEST_LATENCY.observe((datetime.utcnow() - start).total_seconds())

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
