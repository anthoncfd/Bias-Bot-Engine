import httpx
import asyncio
import yfinance as yf
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from app.config import settings
from app.logger import logger
from app.services.quant_math import QuantitativeMathEngine
from app.services.macro_sentiment import MacroSentimentEngine
from app.services.news_intelligence import NewsIntelligenceEngine
from app.services.composite_engine import MarketIntelligenceEngine

class MarketDataService:
    """Enterprise-grade hybrid financial brokerage interface layer.
    Manages state-isolated, non-blocking asynchronous streaming pools while standardizing
    multi-vendor storage schemas dynamically using explicit timezone execution.
    """
    
    def __init__(self, http_client: Optional[httpx.AsyncClient] = None):
        """Initializes client configuration and establishes persistent, shared session connection pooling."""
        self.twelve_base = "https://api.twelvedata.com"
        self.db_url = f"{settings.supabase_url}/rest/v1/market_history"
        
        self.db_headers = {
            "apikey": settings.supabase_key,
            "Authorization": f"Bearer {settings.supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates"
        }
        
        self.browser_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        self.client = http_client if http_client is not None else httpx.AsyncClient(timeout=15.0)

    def _normalize_symbol(self, symbol: str) -> str:
        """Standardizes input vectors into raw capitalized strings."""
        return symbol.replace("/", "").strip().upper()

    def _get_asset_class_route(self, clean_symbol: str) -> str:
        """Abstracted Registry Router mapping asset character configurations cleanly."""
        if clean_symbol in ["BTCUSD", "ETHUSD", "BNBUSD"]:
            return "CRYPTO"
        if clean_symbol.startswith("^") or "=" in clean_symbol or clean_symbol in ["YM=F", "NQ=F", "NKD=F"]:
            return "INDEX_FUTURE"
        return "FOREX"

    async def get_live_crypto_price(self, symbol: str) -> Optional[float]:
        """Queries public exchange endpoints natively accessible from cloud hosting regions."""
        try:
            clean_symbol = self._normalize_symbol(symbol)
            base_currency = "BTC" if "BTC" in clean_symbol else "ETH" if "ETH" in clean_symbol else "BNB"
            
            res = await self.client.get(
                f"https://api.coinbase.com/v2/prices/{base_currency}-USD/spot", 
                headers=self.browser_headers
            )
            if res.status_code == 200:
                return float(res.json()["data"]["amount"])
        except Exception as err:
            logger.error(f"Cloud crypto infrastructure retrieval failure for {symbol}: {err}")
        return None

    async def _fetch_yf_live_cloud_safe(self, symbol: str) -> Optional[float]:
        """Scrapes Yahoo's underlying chart feed directly using browser emulation loops."""
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1d&interval=1m"
            res = await self.client.get(url, headers=self.browser_headers)
            if res.status_code == 200:
                result = res.json().get("chart", {}).get("result", [])
                if result:
                    meta = result[0].get("meta", {})
                    live_price = meta.get("regularMarketPrice")
                    if live_price:
                        return float(live_price)
        except Exception as err:
            logger.error(f"Emulated index query execution failure for {symbol}: {err}")
        return None

    async def get_live_market_price(self, symbol: str) -> Optional[float]:
        """Routes real-time price tick evaluation channels to respective vendor clients."""
        clean_symbol = self._normalize_symbol(symbol)
        asset_class = self._get_asset_class_route(clean_symbol)
        
        if asset_class in ["CRYPTO", "INDEX_FUTURE"]:
            if asset_class == "CRYPTO":
                crypto_price = await self.get_live_crypto_price(clean_symbol)
                if crypto_price:
                    return crypto_price
            return await self._fetch_yf_live_cloud_safe(clean_symbol)
            
        try:
            twelve_symbol = f"{clean_symbol[:3]}/{clean_symbol[3:]}"
            res = await self.client.get(
                f"{self.twelve_base}/price", 
                params={"symbol": twelve_symbol, "apikey": settings.market_api_key},
                headers=self.browser_headers
            )
            if res.status_code == 200:
                data = res.json()
                if "price" in data:
                    return float(data["price"])
        except Exception as err:
            logger.error(f"Twelve Data upstream live pricing retrieval exception on asset {symbol}: {err}")
        return None

    async def fetch_cached_history(self, symbol: str) -> Optional[List[Dict[str, str]]]:
        """Retrieves and compiles an expanded 65-bar array cleanly from our continuous database rows."""
        clean_symbol = self._normalize_symbol(symbol)
        try:
            url = f"{self.db_url}?symbol=eq.{clean_symbol}&order=date.desc&limit=65"
            res = await self.client.get(url, headers=self.db_headers)
            if res.status_code == 200 and res.json():
                return [{"datetime": row["date"], "close": str(row["close"])} for row in res.json()]
        except Exception as err:
            logger.error(f"Local Supabase transaction read breakdown on {clean_symbol}: {err}")
        return None

    async def sync_asset_historical_cache(self, symbol: str, force_refresh: bool = False) -> Optional[List[Dict[str, str]]]:
        """Executes defensive historical lookback synchronizations avoiding data duplicates."""
        clean_symbol = self._normalize_symbol(symbol)
        existing = await self.fetch_cached_history(clean_symbol)
        asset_class = self._get_asset_class_route(clean_symbol)
        
        utc_now = datetime.now(timezone.utc)
        utc_today = utc_now.strftime("%Y-%m-%d")
        utc_yesterday = (utc_now - timedelta(days=1)).strftime("%Y-%m-%d")
        
        if not force_refresh and existing and len(existing) >= 50:
            if existing[0]["datetime"] in [utc_today, utc_yesterday]:
                return existing

        logger.info(f"📡 Synchronization Lock Released: Updating historical tables for {clean_symbol}")
        bars = []
        
        is_empty_cache = not existing or len(existing) < 45 or force_refresh
        fetch_period = "90d" if is_empty_cache else "5d"
        twelve_output_size = "60" if is_empty_cache else "5"

        if asset_class in ["CRYPTO", "INDEX_FUTURE"]:
            yf_ticker = "BTC-USD" if clean_symbol == "BTCUSD" else "ETH-USD" if clean_symbol == "ETHUSD" else "BNB-USD" if clean_symbol == "BNBUSD" else clean_symbol
            ticker = yf.Ticker(yf_ticker)
            hist = await asyncio.to_thread(ticker.history, period=fetch_period)
            if not hist.empty:
                hist = hist.sort_index(ascending=False)
                if fetch_period == "5d":
                    hist = hist.head(3)
                for idx, row in hist.iterrows():
                    bars.append({"symbol": clean_symbol, "date": idx.strftime("%Y-%m-%d"), "close": float(row['Close'])})
        else:
            try:
                twelve_symbol = f"{clean_symbol[:3]}/{clean_symbol[3:]}"
                params = {"symbol": twelve_symbol, "interval": "1day", "outputsize": twelve_output_size, "apikey": settings.market_api_key}
                res = await self.client.get(f"{self.twelve_base}/time_series", params=params)
                if res.status_code == 200 and "values" in res.json():
                    values_payload = res.json()["values"]
                    if fetch_period == "5d" and values_payload:
                        values_payload = values_payload[:3]
                    for val in values_payload:
                        bars.append({"symbol": clean_symbol, "date": val["datetime"], "close": float(val["close"])})
            except Exception as err:
                logger.error(f"Twelve Data history call crash for {clean_symbol}: {err}")

        if bars:
            try:
                await self.client.post(self.db_url, headers=self.db_headers, json=bars, timeout=15.0)
            except Exception as post_err:
                logger.error(f"Failed to upsert updated transaction rows to Supabase: {post_err}")
                
        return await self.fetch_cached_history(clean_symbol)

    async def get_asset_report(self, symbol: str, display_name: str) -> str:
        """Compiles time-series matrix points into quantitative reporting telemetry layers."""
        try:
            clean_symbol = self._normalize_symbol(symbol)
            asset_class = self._get_asset_class_route(clean_symbol)
            
            live_price = await self.get_live_market_price(clean_symbol)
            if not live_price:
                return f"⚠️ **Data Fetch Error:** Unable to retrieve real-time data ticks for `{display_name}`."

            historical_bars = await self.fetch_cached_history(clean_symbol)
            if not historical_bars or len(historical_bars) < 45:
                historical_bars = await self.sync_asset_historical_cache(clean_symbol, force_refresh=False)
                
            if not historical_bars or len(historical_bars) < 2:
                return f"⚠️ **Cache Warm-up:** Building your historical archive for `{display_name}`. Re-query in 5 seconds."

            utc_now = datetime.now(timezone.utc)
            utc_today = utc_now.strftime("%Y-%m-%d")
            utc_yesterday = (utc_now - timedelta(days=1)).strftime("%Y-%m-%d")
            
            prior_close = None
            has_yesterday = False
            
            if historical_bars[0]["datetime"] == utc_yesterday:
                prior_close = float(historical_bars[0]["close"])
                has_yesterday = True
            elif len(historical_bars) > 1 and historical_bars[1]["datetime"] == utc_yesterday:
                prior_close = float(historical_bars[1]["close"])
                has_yesterday = True
            else:
                for bar in historical_bars:
                    if bar["datetime"] == utc_yesterday:
                        prior_close = float(bar["close"])
                        has_yesterday = True
                        break
                    elif bar["datetime"] < utc_today and prior_close is None:
                        prior_close = float(bar["close"])

            if not has_yesterday:
                try:
                    if asset_class in ["CRYPTO", "INDEX_FUTURE"]:
                        yf_ticker = "BTC-USD" if clean_symbol == "BTCUSD" else "ETH-USD" if clean_symbol == "ETHUSD" else "BNB-USD" if clean_symbol == "BNBUSD" else clean_symbol
                        ticker = yf.Ticker(yf_ticker)
                        live_info = await asyncio.to_thread(getattr, ticker, "info")
                        if "previousClose" in live_info and live_info["previousClose"]:
                            prior_close = float(live_info["previousClose"])
                    else:
                        twelve_symbol = f"{clean_symbol[:3]}/{clean_symbol[3:]}"
                        res = await self.client.get(
                            f"{self.twelve_base}/quote", 
                            params={"symbol": twelve_symbol, "apikey": settings.market_api_key}
                        )
                        if res.status_code == 200 and "previous_close" in res.json():
                            prior_close = float(res.json()["previous_close"])
                except Exception as gap_err:
                    logger.error(f"Failed to fill historical gap live for {clean_symbol}: {gap_err}")

            if prior_close is None:
                prior_close = float(historical_bars[0]["close"])

            if prior_close == 0:
                return f"❌ **Data Contamination:** Absolute previous close processed as zero. Halting calculations."

            net_change = live_price - prior_close
            change_pct = (net_change / prior_close) * 100
            
            # ━━━━ 🏛️ RUN MULTI-FACTOR ENGINES ━━━━
            macro_engine = MacroSentimentEngine(http_client=self.client)
            news_engine = NewsIntelligenceEngine(http_client=self.client)
            composite_engine = MarketIntelligenceEngine(http_client=self.client)
            
            raw_macro = await macro_engine.fetch_macro_raw_metrics()
            macro_data = macro_engine.calculate_normalized_scores(raw_macro)
            news_score = await news_engine.generate_news_confluence_score(clean_symbol)
            
            tech = QuantitativeMathEngine.calculate_technical_indicators(historical_bars, live_price, prior_close, asset_class)
            
            matrix = composite_engine.calculate_composite_matrix(
                tech=tech['technical_score_pct'],
                macro=macro_data['macro_score_pct'],
                sent=macro_data['sentiment_score_pct'],
                news=news_score
            )
            
            ai_briefing = await composite_engine.generate_institutional_briefing(clean_symbol, matrix, tech['technical_score_pct'])
            
            bias_emoji = "🚀" if "BULLISH" in matrix['market_bias'] else "💥" if "BEARISH" in matrix['market_bias'] else "⚖️"
            is_high_value = asset_class == "CRYPTO" or "JPY" in clean_symbol or clean_symbol.startswith("^") or "=" in clean_symbol or clean_symbol in ["YM=F", "NQ=F", "NKD=F"]
            
            if is_high_value:
                val_fmt, cls_fmt, chg_fmt = f"{live_price:,.2f}", f"{prior_close:,.2f}", f"{net_change:+,.2f}"
            else:
                val_fmt, cls_fmt, chg_fmt = f"{live_price:.5f}", f"{prior_close:.5f}", f"{net_change:+.5f}"

            return (
                f"{tech['bias_icon']} **{display_name} COMPOSITE INTEL**\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"• **Current Price:** `{val_fmt}`\n"
                f"• **Net Deviation:** `{chg_fmt}` (`{change_pct:+.2f}%`)\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📊 **Sub-Score Matrices:**\n"
                f" ├ Technical: `{tech['technical_score_pct']:+.1f}%`\n"
                f" ├ Macro Setup: `{macro_data['macro_score_pct']:+.1f}%`\n"
                f" ├ Risk Sentiment: `{macro_data['sentiment_score_pct']:+.1f}%`\n"
                f" └ News Intelligence: `{news_score:+.1f}%`\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🎲 **Composite Matrix Probabilities:**\n"
                f"• Bullish Path: `{matrix['prob_up']:.1f}%` | Bearish Path: `{matrix['prob_down']:.1f}%`\n"
                f"• Engine Conviction: `{matrix['confidence_level']:.1f}%` Scale\n"
                f"📊 **Final Engine Bias:** `{bias_emoji} {matrix['market_bias'].replace('_', ' ')}`\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📝 **Executive Macro Briefing:**\n_{ai_briefing}_\n"
            )
            
        except Exception as err:
            logger.critical(f"Schema compilation exception parsing metrics block for {clean_symbol}: {err}", exc_info=True)
            return f"❌ **Processing Error:** Infrastructure fault processing metrics for `{display_name}`."
