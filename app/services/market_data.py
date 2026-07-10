import httpx
import asyncio
import yfinance as yf
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from app.config import settings
from app.logger import logger
from app.services.quant_math import QuantitativeMathEngine

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
        
        # 🛡️ CONNECTION POOL OPTIMIZATION: Fallback to context client to stop socket starvation
        self.client = http_client if http_client is not None else httpx.AsyncClient(timeout=10.0)

    def _normalize_symbol(self, symbol: str) -> str:
        """Standardizes input vectors into raw capitalized strings."""
        return symbol.replace("/", "").strip().upper()

    def _get_asset_class_route(self, clean_symbol: str) -> str:
        """Abstracted Registry Router mapping asset character configurations cleanly."""
        if clean_symbol in ["BTCUSD", "ETHUSD", "BNBUSD"]:
            return "CRYPTO"
        if clean_symbol.startswith("^") or "=" in clean_symbol:
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
        """Retrieves and compiles a 35-bar array cleanly from our continuous database rows."""
        clean_symbol = self._normalize_symbol(symbol)
        try:
            url = f"{self.db_url}?symbol=eq.{clean_symbol}&order=date.desc&limit=35"
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
        
        # 🌍 STABILIZED TIMEZONE ANCHOR: Enforce global UTC to align database dates with vendor endpoints
        utc_now = datetime.now(timezone.utc)
        utc_today = utc_now.strftime("%Y-%m-%d")
        utc_yesterday = (utc_now - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # 🛡️ COOLDOWN GUARD: Block outbound API connection usage if database cache is completely fresh
        if not force_refresh and existing and len(existing) >= 20:
            if existing[0]["datetime"] in [utc_today, utc_yesterday]:
                return existing

        logger.info(f"📡 Synchronization Lock Released: Updating historical tables for {clean_symbol}")
        bars = []
        
        # Dynamic lookback slicing configuration based on active cache health
        is_empty_cache = not existing or len(existing) < 5 or force_refresh
        fetch_period = "45d" if is_empty_cache else "5d"
        twelve_output_size = "30" if is_empty_cache else "5"

        if asset_class in ["CRYPTO", "INDEX_FUTURE"]:
            yf_ticker = "BTC-USD" if clean_symbol == "BTCUSD" else "ETH-USD" if clean_symbol == "ETHUSD" else "BNB-USD" if clean_symbol == "BNBUSD" else clean_symbol
            ticker = yf.Ticker(yf_ticker)
            # Run blocking I/O loop thread safely in executor context
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
            if not historical_bars or len(historical_bars) < 15:
                historical_bars = await self.sync_asset_historical_cache(clean_symbol, force_refresh=False)
                
            if not historical_bars or len(historical_bars) < 2:
                return f"⚠️ **Cache Warm-up:** Building your historical archive for `{display_name}`. Re-query in 5 seconds."

            # 🌍 STANDARD TIMEZONE ANCHOR
            utc_now = datetime.now(timezone.utc)
            utc_today = utc_now.strftime("%Y-%m-%d")
            utc_yesterday = (utc_now - timedelta(days=1)).strftime("%Y-%m-%d")
            
            prior_close = None
            has_yesterday = False
            
            # 🏎️ $O(1)$ SCANNED SEARCH ACCESS (Optimized for date-descending indexed data blocks)
            if historical_bars[0]["datetime"] == utc_yesterday:
                prior_close = float(historical_bars[0]["close"])
                has_yesterday = True
            elif len(historical_bars) > 1 and historical_bars[1]["datetime"] == utc_yesterday:
                prior_close = float(historical_bars[1]["close"])
                has_yesterday = True
            else:
                # O(N) Fallback loop scanning sequence if gap condition requires evaluation
                for bar in historical_bars:
                    if bar["datetime"] == utc_yesterday:
                        prior_close = float(bar["close"])
                        has_yesterday = True
                        break
                    elif bar["datetime"] < utc_today and prior_close is None:
                        prior_close = float(bar["close"])

            # 🛡️ CREDIT-SAFE SINGLE QUOTE FALLBACK GAP FILLING
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

            # Safe database absolute baseline fallback
            if prior_close is None:
                prior_close = float(historical_bars[0]["close"])

            # Prevent zero-division calculation crashes
            if prior_close == 0:
                return f"❌ **Data Contamination:** Absolute previous close for `{display_name}` processed as zero. Halting equations."

            net_change = live_price - prior_close
            change_pct = (net_change / prior_close) * 100
            
            mc = QuantitativeMathEngine.calculate_monte_carlo(live_price, historical_bars)
            prob_up = mc['prob_up']
            prob_down = mc['prob_down']
            
            # 🎨 HIGH-END VISUAL PRESENTER DECOUPLING
            return AssetReportPresenter.render(
                display_name=display_name,
                clean_symbol=clean_symbol,
                asset_class=asset_class,
                live_price=live_price,
                prior_close=prior_close,
                net_change=net_change,
                change_pct=change_pct,
                mc_data=mc,
                prob_up=prob_up,
                prob_down=prob_down
            )
            
        except Exception as err:
            logger.critical(f"Schema compilation exception parsing metrics block for {clean_symbol}: {err}", exc_info=True)
            return f"❌ **Processing Error:** Infrastructure fault processing metrics for `{display_name}`."


class AssetReportPresenter:
    """Dedicated presentation formatting layer decoupling business engine calculation logic
    from front-end string construction interfaces.
    """
    
    @staticmethod
    def render(display_name: str, clean_symbol: str, asset_class: str, live_price: float, 
               prior_close: float, net_change: float, change_pct: float, mc_data: dict, 
               prob_up: float, prob_down: float) -> str:
        """Assembles variables into production-ready scannable Markdown data blocks."""
        
        if prob_up > prob_down and net_change > 0:
            direction_icon, trend_arrow, distribution_edge = "🟢 BULLISH BIAS", "📈", f"🟢 Long Advantage ({prob_up:.1f}%)"
        elif prob_down > prob_up and net_change < 0:
            direction_icon, trend_arrow, distribution_edge = "🔴 BEARISH BIAS", "📉", f"🔴 Short Advantage ({prob_down:.1f}%)"
        elif prob_up > prob_down and net_change <= 0:
            direction_icon, trend_arrow, distribution_edge = "🟡 CONDITIONAL BULLISH DRIFT", "⚡", f"🟡 Long Skew / Counter-Trend ({prob_up:.1f}%)"
        elif prob_down > prob_up and net_change >= 0:
            direction_icon, trend_arrow, distribution_edge = "🟡 CONDITIONAL BEARISH DRIFT", "⚡", f"🔴 Short Skew / Counter-Trend ({prob_down:.1f}%)"
        else:
            direction_icon, trend_arrow, distribution_edge = "⚪ NEUTRAL RANDOM WALK", "⚡", "⚪ Balanced Distribution"
        
        is_high_value = asset_class == "CRYPTO" or "JPY" in clean_symbol or clean_symbol.startswith("^") or "=" in clean_symbol
        
        if is_high_value:
            val_fmt, cls_fmt, chg_fmt = f"{live_price:,.2f}", f"{prior_close:,.2f}", f"{net_change:+,.2f}"
            ev_fmt = f"{mc_data['expected_value']:,.2f}"
        else:
            val_fmt, cls_fmt, chg_fmt = f"{live_price:.5f}", f"{prior_close:.5f}", f"{net_change:+.5f}"
            ev_fmt = f"{mc_data['expected_value']:.5f}"
            
        kelly_str = f"`{mc_data['kelly_suggested_allocation_pct']:.1f}%` Max Account Risk Limit" if mc_data['kelly_suggested_allocation_pct'] > 0 else "`0.0%` (No Active Distribution Edge)"

        return (
            f"{trend_arrow} **{display_name} METRICS**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"• **Current Price:** `{val_fmt}`\n"
            f"• **Previous Close:** `{cls_fmt}`\n"
            f"• **Net Deviation:** `{chg_fmt}` (`{change_pct:+.2f}%`)\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🎲 **MONTE CARLO SESSION PROBABILITIES**\n"
            f"• **Simulated Expected Value:** `{ev_fmt}`\n"
            f"• **Historical Period Volatility:** `{mc_data['sigma_pct']:.2f}%`\n"
            f"• **Distribution Edge:** `{distribution_edge}`\n"
            f"• **Fractional Kelly Capital Allocation:** {kelly_str}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📊 **Engine Bias:** `{direction_icon}`"
        )
