import httpx
import asyncio
import yfinance as yf
import numpy as np
from datetime import datetime
from app.config import settings
from app.logger import logger
from app.services.quant_math import QuantitativeMathEngine

class MarketDataService:
    """Enterprise-grade hybrid financial broker utilizing cloud-resilient public streams,
    browser-emulated index/crypto scrapers, and local database caches.
    """
    
    def __init__(self):
        self.twelve_base = "https://api.twelvedata.com"
        self.db_headers = {
            "apikey": settings.supabase_key,
            "Authorization": f"Bearer {settings.supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates"
        }
        self.db_url = f"{settings.supabase_url}/rest/v1/market_history"
        self.browser_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    async def get_live_crypto_price(self, symbol: str) -> float | None:
        """Queries cloud-friendly public exchange endpoints natively accessible from US hosting regions."""
        try:
            clean_symbol = symbol.replace("/", "").strip().upper()
            base_currency = "BTC" if "BTC" in clean_symbol else "ETH" if "ETH" in clean_symbol else "BNB"
            
            async with httpx.AsyncClient(timeout=10.0, headers=self.browser_headers) as client:
                res = await client.get(f"https://api.coinbase.com/v2/prices/{base_currency}-USD/spot")
                if res.status_code == 200:
                    return float(res.json()["data"]["amount"])
        except Exception as err:
            logger.error(f"Cloud crypto infrastructure retrieval failure for {symbol}: {err}")
        return None

    async def _fetch_yf_live_cloud_safe(self, symbol: str) -> float | None:
        """Asynchronously scrapes Yahoo's underlying chart feed directly using browser emulation."""
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1d&interval=1m"
            async with httpx.AsyncClient(timeout=10.0, headers=self.browser_headers) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    result = res.json().get("chart", {}).get("result", [])
                    if result:
                        meta = result[0].get("meta", {})
                        live_price = meta.get("regularMarketPrice")
                        if live_price:
                            return float(live_price)
        except Exception as err:
            logger.error(f"Emulated index query execution failure for {symbol}: {err}")
            
        try:
            ticker = yf.Ticker(symbol)
            val = ticker.fast_info.get('last_price')
            if val is not None and val > 0:
                return float(val)
        except Exception:
            pass
        return None

    async def get_live_market_price(self, symbol: str) -> float | None:
        """Routes index assets directly to safe cloud scrapers and fiat pairs to Twelve Data."""
        clean_symbol = symbol.replace("/", "").strip().upper()
        if clean_symbol.startswith("^") or "=" in clean_symbol:
            return await self._fetch_yf_live_cloud_safe(clean_symbol)
            
        async with httpx.AsyncClient(timeout=10.0, headers=self.browser_headers) as client:
            try:
                twelve_symbol = f"{clean_symbol[:3]}/{clean_symbol[3:]}"
                res = await client.get(f"{self.twelve_base}/price", params={"symbol": twelve_symbol, "apikey": settings.market_api_key})
                if res.status_code == 200:
                    data = res.json()
                    if "price" in data:
                        return float(data["price"])
            except Exception as err:
                logger.error(f"Twelve Data upstream live pricing retrieval exception on asset {symbol}: {err}")
            return None

    async def fetch_cached_history(self, symbol: str) -> list | None:
        """Retrieves 30-day structural daily close profiles from Supabase local cache."""
        clean_symbol = symbol.replace("/", "").strip().upper()
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                url = f"{self.db_url}?symbol=eq.{clean_symbol}&select=historical_bars"
                res = await client.get(url, headers=self.db_headers)
                if res.status_code == 200 and res.json():
                    return res.json()[0]["historical_bars"]
            except Exception as err:
                logger.error(f"Local Supabase data synchronization read breakdown on {clean_symbol}: {err}")
            return None

    def _fetch_yf_history(self, symbol: str) -> list | None:
        """Fetches historical daily bars via standard structural back-end arrays."""
        try:
            clean_symbol = symbol.replace("/", "").strip().upper()
            yf_ticker = clean_symbol
            if clean_symbol == "BTCUSD": yf_ticker = "BTC-USD"
            elif clean_symbol == "ETHUSD": yf_ticker = "ETH-USD"
            elif clean_symbol == "BNBUSD": yf_ticker = "BNB-USD"

            ticker = yf.Ticker(yf_ticker)
            hist = ticker.history(period="45d")
            if not hist.empty:
                hist = hist.sort_index(ascending=False).head(30)
                bars = []
                for idx, row in hist.iterrows():
                    bars.append({
                        "datetime": idx.strftime("%Y-%m-%d"),
                        "close": str(row['Close'])
                    })
                return bars
        except Exception as err:
            logger.error(f"Yahoo Finance historical download failure for {clean_symbol}: {err}")
        return None

    async def sync_asset_historical_cache(self, symbol: str) -> list | None:
        """Checks Supabase first. Utilizes custom routing to separate API pipelines entirely."""
        clean_symbol = symbol.replace("/", "").strip().upper()
        existing_cache = await self.fetch_cached_history(clean_symbol)
        if existing_cache and len(existing_cache) > 0:
            return existing_cache

        logger.info(f"📡 Cache Miss: Fetching fresh 30-day historical data for target: {clean_symbol}")
        
        is_crypto = clean_symbol in ["BTCUSD", "ETHUSD", "BNBUSD"]
        if clean_symbol.startswith("^") or "=" in clean_symbol or is_crypto:
            formatted_bars = await asyncio.to_thread(self._fetch_yf_history, clean_symbol)
            if formatted_bars:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    payload = {"symbol": clean_symbol, "historical_bars": formatted_bars, "updated_at": datetime.utcnow().isoformat()}
                    await client.post(self.db_url, headers=self.db_headers, json=payload)
                return formatted_bars
            return None

        # Forex Pairs tracking fallback
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                twelve_symbol = f"{clean_symbol[:3]}/{clean_symbol[3:]}"
                params = {"symbol": twelve_symbol, "interval": "1day", "outputsize": "30", "apikey": settings.market_api_key}
                res = await client.get(f"{self.twelve_base}/time_series", params=params)
                if res.status_code == 200:
                    data = res.json()
                    values = data.get("values")
                    if values:
                        payload = {"symbol": clean_symbol, "historical_bars": values, "updated_at": datetime.utcnow().isoformat()}
                        await client.post(self.db_url, headers=self.db_headers, json=payload)
                        return values
            except Exception as err:
                logger.error(f"System error updating historical tracking tables for {clean_symbol}: {err}")
        return None

    async def get_asset_report(self, symbol: str, display_name: str) -> str:
        """Combines structural daily data with live pricing and enforces unified probabilistic bias routing."""
        try:
            clean_symbol = symbol.replace("/", "").strip().upper()
            is_crypto = clean_symbol in ["BTCUSD", "ETHUSD", "BNBUSD"]
            
            if is_crypto:
                live_price = await self.get_live_crypto_price(clean_symbol)
            else:
                live_price = await self.get_live_market_price(clean_symbol)
                
            if not live_price:
                return f"⚠️ **Data Fetch Error:** Unable to retrieve real-time data ticks for `{display_name}`."

            historical_bars = await self.fetch_cached_history(clean_symbol)
            if not historical_bars or len(historical_bars) == 0:
                historical_bars = await self.sync_asset_historical_cache(clean_symbol)
                
            if not historical_bars or len(historical_bars) < 2:
                return f"⚠️ **Cache Warm-up:** Building records for `{display_name}`. Try again in 5 seconds."

            latest_bar_date = historical_bars[0]["datetime"]
            target_index = 0
            
            local_today = datetime.now().strftime("%Y-%m-%d")
            if latest_bar_date == local_today or len(historical_bars) > 1:
                target_index = 1
                    
            prior_close = float(historical_bars[target_index]["close"])
            
            if abs(live_price - prior_close) < 0.00001 and len(historical_bars) > target_index + 1:
                target_index += 1
                prior_close = float(historical_bars[target_index]["close"])

            net_change = live_price - prior_close
            change_pct = (net_change / prior_close) * 100
            
            # Execute mathematical path simulation
            mc = QuantitativeMathEngine.calculate_monte_carlo(live_price, historical_bars)
            prob_up = mc['prob_up']
            prob_down = mc['prob_down']
            
            # 🧠 HARDENED DUAL-FILTER BIAS LOGIC MATRIX (Mathematical Intersection Lock)
            if prob_up > prob_down and net_change > 0:
                direction_icon = "🟢 BULLISH BIAS"
                trend_arrow = "📈"
                distribution_edge = f"🟢 Long Advantage ({prob_up:.1f}%)"
            elif prob_down > prob_up and net_change < 0:
                direction_icon = "🔴 BEARISH BIAS"
                trend_arrow = "📉"
                distribution_edge = f"🔴 Short Advantage ({prob_down:.1f}%)"
            elif prob_up > prob_down and net_change <= 0:
                # Simulation indicates upside drift edge, but daily session candle is currently bearish
                direction_icon = "🟡 CONDITIONAL BULLISH DRIFT"
                trend_arrow = "⚡"
                distribution_edge = f"🟡 Long Skew / Counter-Trend ({prob_up:.1f}%)"
            elif prob_down > prob_up and net_change >= 0:
                # Simulation indicates downside drift edge, but daily session candle is currently bullish
                direction_icon = "🟡 CONDITIONAL BEARISH DRIFT"
                trend_arrow = "⚡"
                distribution_edge = f"🔴 Short Skew / Counter-Trend ({prob_down:.1f}%)"
            else:
                direction_icon = "⚪ NEUTRAL RANDOM WALK"
                trend_arrow = "⚡"
                distribution_edge = "⚪ Balanced Distribution"
            
            # 🛠️ HARDENED DECIMAL STRING DISPLAY FORMATTING
            is_index_or_jpy = "JPY" in clean_symbol or clean_symbol.startswith("^") or "=" in clean_symbol
            
            if is_crypto:
                # Enforce clean 2-decimal precision for crypto spot assets
                val_fmt, cls_fmt, chg_fmt = f"{live_price:,.2f}", f"{prior_close:,.2f}", f"{net_change:+,.2f}"
                ev_fmt = f"{mc['expected_value']:,.2f}"
            elif is_index_or_jpy:
                # Enforce index/jpy 2-decimal presentation format
                val_fmt, cls_fmt, chg_fmt = f"{live_price:,.2f}", f"{prior_close:,.2f}", f"{net_change:+,.2f}"
                ev_fmt = f"{mc['expected_value']:,.2f}"
            else:
                # Standard 5-decimal precision strictly reserved for traditional fiat Forex currency pairs
                val_fmt, cls_fmt, chg_fmt = f"{live_price:.5f}", f"{prior_close:.5f}", f"{net_change:+.5f}"
                ev_fmt = f"{mc['expected_value']:.5f}"
                
            kelly_str = f"`{mc['kelly_suggested_allocation_pct']:.1f}%` Max Account Risk Limit" if mc['kelly_suggested_allocation_pct'] > 0 else "`0.0%` (No Active Distribution Edge)"

            return (
                f"{trend_arrow} **{display_name} METRICS**\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"• **Current Price:** `{val_fmt}`\n"
                f"• **Previous Close:** `{cls_fmt}`\n"
                f"• **Net Deviation:** `{chg_fmt}` (`{change_pct:+.2f}%`)\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🎲 **MONTE CARLO SESSION PROBABILITIES**\n"
                f"• **Simulated Expected Value:** `{ev_fmt}`\n"
                f"• **Historical Period Volatility:** `{mc['sigma_pct']:.2f}%`\n"
                f"• **Distribution Edge:** `{distribution_edge}`\n"
                f"• **Fractional Kelly Capital Allocation:** {kelly_str}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📊 **Engine Bias:** `{direction_icon}`"
            )
        except Exception as err:
            logger.critical(f"Schema compilation exception parsing metrics block for {clean_symbol}: {err}", exc_info=True)
            return f"❌ **Processing Error:** Infrastructure fault processing metrics for `{display_name}`."
