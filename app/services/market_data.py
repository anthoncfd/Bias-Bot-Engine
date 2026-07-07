import httpx
import asyncio
import yfinance as yf
from datetime import datetime
from app.config import settings
from app.logger import logger

class MarketDataService:
    """Enterprise-grade hybrid financial broker utilizing local DB caches and public streams."""
    
    def __init__(self):
        self.twelve_base = "https://api.twelvedata.com"
        self.binance_base = "https://api.binance.com/api/v3"
        self.db_headers = {
            "apikey": settings.supabase_key,
            "Authorization": f"Bearer {settings.supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates"
        }
        self.db_url = f"{settings.supabase_url}/rest/v1/market_history"

    async def get_live_crypto_price(self, symbol: str) -> float | None:
        """Queries uncapped public exchange endpoints. Consumes 0 Twelve Data credits."""
        try:
            # Explicitly force clean formatting: turn BTCUSD or BTC/USD straight into BTCUSDT
            clean_symbol = symbol.replace("/", "").upper()
            if clean_symbol.endswith("USD") and not clean_symbol.endswith("USDT"):
                binance_symbol = clean_symbol.replace("USD", "USDT")
            else:
                binance_symbol = clean_symbol

            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(f"{self.binance_base}/ticker/price", params={"symbol": binance_symbol})
                if res.status_code == 200:
                    return float(res.json()["price"])
                else:
                    logger.error(f"Binance API returned status {res.status_code} for {binance_symbol}: {res.text}")
        except Exception as err:
            logger.error(f"Failed pulling public crypto matrix feed for {symbol}: {err}")
        return None

    def _fetch_yf_live(self, symbol: str) -> float | None:
        """Synchronous helper with multi-layered fallback running inside an isolated worker thread."""
        try:
            ticker = yf.Ticker(symbol)
            
            # Primary attempt: Get fast info attributes (Extremely reliable and fast)
            try:
                live_price = ticker.fast_info.get('last_price')
                if live_price and live_price > 0:
                    return float(live_price)
            except Exception:
                pass

            # Secondary fallback: Extract from current history matrix
            todays_data = ticker.history(period="1d")
            if not todays_data.empty and 'Close' in todays_data.columns:
                return float(todays_data['Close'].iloc[-1])
                
        except Exception as err:
            logger.error(f"Yahoo Finance live price extraction failure for {symbol}: {err}")
        return None

    async def get_live_market_price(self, symbol: str) -> float | None:
        """Routes indices to Yahoo Finance and fiat pairs to Twelve Data."""
        if symbol.startswith("^"):
            return await asyncio.to_thread(self._fetch_yf_live, symbol)
            
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                res = await client.get(f"{self.twelve_base}/price", params={"symbol": symbol, "apikey": settings.market_api_key})
                if res.status_code == 200:
                    data = res.json()
                    if "price" in data:
                        return float(data["price"])
            except Exception as err:
                logger.error(f"Upstream live pricing retrieval exception on asset {symbol}: {err}")
            return None

    async def fetch_cached_history(self, symbol: str) -> list | None:
        """Retrieves 30-day structural daily close profiles from Supabase local cache."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                url = f"{self.db_url}?symbol=eq.{symbol}&select=historical_bars"
                res = await client.get(url, headers=self.db_headers)
                if res.status_code == 200 and res.json():
                    return res.json()[0]["historical_bars"]
            except Exception as err:
                logger.error(f"Local Supabase data synchronization read breakdown on {symbol}: {err}")
            return None

    def _fetch_yf_history(self, symbol: str) -> list | None:
        """Fetches daily bars from Yahoo Finance and formats them to match Twelve Data structure."""
        try:
            ticker = yf.Ticker(symbol)
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
            logger.error(f"Yahoo Finance historical download failure for {symbol}: {err}")
        return None

    async def sync_asset_historical_cache(self, symbol: str):
        """Checks Supabase first. Utilizes custom routing to separate API pipelines entirely."""
        existing_cache = await self.fetch_cached_history(symbol)
        if existing_cache and len(existing_cache) > 0:
            return

        logger.info(f"📡 Cache Miss: Fetching fresh 30-day historical data for target: {symbol}")
        
        if symbol.startswith("^"):
            formatted_bars = await asyncio.to_thread(self._fetch_yf_history, symbol)
            if formatted_bars:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    payload = {"symbol": symbol, "historical_bars": formatted_bars, "updated_at": datetime.utcnow().isoformat()}
                    await client.post(self.db_url, headers=self.db_headers, json=payload)
            return

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                params = {"symbol": symbol, "interval": "1day", "outputsize": "30", "apikey": settings.market_api_key}
                res = await client.get(f"{self.twelve_base}/time_series", params=params)
                if res.status_code == 200:
                    data = res.json()
                    if "values" in data:
                        payload = {"symbol": symbol, "historical_bars": data["values"], "updated_at": datetime.utcnow().isoformat()}
                        await client.post(self.db_url, headers=self.db_headers, json=payload)
            except Exception as err:
                logger.error(f"System error updating historical tracking tables for {symbol}: {err}")

    async def get_asset_report(self, symbol: str, display_name: str) -> str:
        """Combines local historical boundaries with live single pricing nodes for structural analysis."""
        is_crypto = symbol.replace("/", "").upper() in ["BTCUSD", "ETHUSD", "BNBUSD"]
        
        if is_crypto:
            live_price = await self.get_live_crypto_price(symbol)
        else:
            live_price = await self.get_live_market_price(symbol)
            
        if not live_price:
            return f"⚠️ **Data Fetch Error:** Unable to retrieve real-time data ticks for `{display_name}`."

        historical_bars = await self.fetch_cached_history(symbol)
        if not historical_bars:
            await self.sync_asset_historical_cache(symbol)
            historical_bars = await self.fetch_cached_history(symbol)
            
        try:
            if not historical_bars:
                return f"⚠️ **Cache Warm-up:** Building records for `{display_name}`. Try again in 5 seconds."
            
            today_str = datetime.utcnow().strftime("%Y-%m-%d")
            target_index = 0
            
            if historical_bars[0]["datetime"] == today_str:
                if len(historical_bars) > 1:
                    target_index = 1
                    
            prior_close = float(historical_bars[target_index]["close"])
            net_change = live_price - prior_close
            change_pct = (net_change / prior_close) * 100
            
            is_index_or_jpy = "JPY" in symbol or symbol.startswith("^")
            if "/" in symbol and not is_index_or_jpy:
                val_fmt, cls_fmt, chg_fmt = f"{live_price:.5f}", f"{prior_close:.5f}", f"{net_change:+.5f}"
            else:
                val_fmt, cls_fmt, chg_fmt = f"{live_price:,.3f}", f"{prior_close:,.3f}", f"{net_change:+,.3f}"
                
            direction_icon = "🟢 BULLISH BIAS" if change_pct >= 0 else "🔴 BEARISH BIAS"
            trend_arrow = "📈" if change_pct >= 0 else "📉"
            
            return (
                f"{trend_arrow} **{display_name} METRICS**\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"• **Current Price:** `{val_fmt}`\n"
                f"• **Previous Close:** `{cls_fmt}`\n"
                f"• **Net Deviation:** `{chg_fmt}`\n"
                f"• **Percentage Shift:** `{change_pct:+.2f}%`\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📊 **Engine Bias:** `{direction_icon}`"
            )
        except Exception as err:
            logger.critical(f"Schema compilation exception parsing metrics block for {symbol}: {err}")
            return f"❌ **Processing Error:** Infrastructure fault processing metrics for `{display_name}`."
