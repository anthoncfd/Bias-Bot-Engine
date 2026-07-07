import httpx
from datetime import datetime
from app.config import settings
from app.logger import logger

class MarketDataService:
    """Enterprise-grade hybrid financial broker utilizing local DB caches and public streams."""
    
    def __init__(self):
        self.twelve_base = "https://api.twelvedata.com"
        self.binance_base = "https://api.binance.com/api/v3"
        # Direct async headers targeting Supabase REST API
        self.db_headers = {
            "apikey": settings.supabase_key,
            "Authorization": f"Bearer {settings.supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates"
        }
        self.db_url = f"{settings.supabase_url}/rest/v1/market_history"

    async def get_live_crypto_price(self, symbol: str) -> float | None:
        """Queries uncapped public exchange endpoints. Consumes 0 Twelve Data credits."""
        binance_symbol = f"{symbol.replace('/', '').upper()}T" if not symbol.endswith("USDT") else symbol
        if binance_symbol == "BNBUSDT": binance_symbol = "BNBUSDT"
        
        async with httpx.AsyncClient() as client:
            try:
                res = await client.get(f"{self.binance_base}/ticker/price", params={"symbol": binance_symbol})
                if res.status_code == 200:
                    return float(res.json()["price"])
            except Exception as err:
                logger.error(f"Failed pulling public crypto matrix feed for {symbol}: {err}")
            return None

    async def get_live_market_price(self, symbol: str) -> float | None:
        """Fetches lightweight current tick value only. Minimal payload fingerprint."""
        async with httpx.AsyncClient() as client:
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
        async with httpx.AsyncClient() as client:
            try:
                url = f"{self.db_url}?symbol=eq.{symbol}&select=historical_bars"
                res = await client.get(url, headers=self.db_headers)
                if res.status_code == 200 and res.json():
                    return res.json()[0]["historical_bars"]
            except Exception as err:
                logger.error(f"Local Supabase data synchronization read breakdown on {symbol}: {err}")
            return None

    async def sync_asset_historical_cache(self, symbol: str):
        """Checks Supabase first. Only pulls from Twelve Data if the record is missing completely."""
        # Check if historical bars already exist inside the local database
        existing_cache = await self.fetch_cached_history(symbol)
        
        if existing_cache and len(existing_cache) > 0:
            logger.info(f"💾 Cache Match: Data for {symbol} already exists in Supabase. Skipping Twelve Data API call (0 credits used).")
            return

        # If cache is absent, proceed to safely execute an external pull
        logger.info(f"📡 Cache Miss: Fetching fresh 30-day historical data for target: {symbol}")
        async with httpx.AsyncClient() as client:
            try:
                params = {"symbol": symbol, "interval": "1day", "outputsize": "30", "apikey": settings.market_api_key}
                res = await client.get(f"{self.twelve_base}/time_series", params=params)
                if res.status_code == 200:
                    data = res.json()
                    if "values" in data:
                        payload = {"symbol": symbol, "historical_bars": data["values"], "updated_at": datetime.utcnow().isoformat()}
                        save_res = await client.post(self.db_url, headers=self.db_headers, json=payload)
                        if save_res.status_code in [200, 201]:
                            logger.info(f"Successfully cached 30 historical sessions for {symbol} into Supabase.")
                            return
                logger.error(f"Upstream refusal compiling daily matrix array historical records for {symbol}")
            except Exception as err:
                logger.error(f"System error updating historical tracking tables for {symbol}: {err}")

    async def get_asset_report(self, symbol: str, display_name: str) -> str:
        """Combines local historical boundaries with live single pricing nodes for structural analysis."""
        is_crypto = symbol.replace("/", "") in ["BTCUSD", "ETHUSD", "BNBUSD"]
        
        # 1. Fetch current price from correct source
        if is_crypto:
            live_price = await self.get_live_crypto_price(symbol)
        else:
            live_price = await self.get_live_market_price(symbol)
            
        if not live_price:
            return f"⚠️ **Data Fetch Error:** Unable to retrieve real-time data ticks for `{display_name}`."

        # 2. Extract Prior Session Close from local storage
        historical_bars = await self.fetch_cached_history(symbol)
        
        if not historical_bars:
            await self.sync_asset_historical_cache(symbol)
            historical_bars = await self.fetch_cached_history(symbol)
            
        try:
            if not historical_bars:
                return f"⚠️ **Cache Warm-up:** Building records for `{display_name}`. Try again in 5 seconds."
                
            prior_close = float(historical_bars[0]["close"])
            
            # Mathematical engine computations pinned exactly to prior session boundary
            net_change = live_price - prior_close
            change_pct = (net_change / prior_close) * 100
            
            is_jpy = "JPY" in symbol or symbol == "N225"
            if "/" in symbol and not is_jpy:
                val_fmt, cls_fmt, chg_fmt = f"{live_price:.5f}", f"{prior_close:.5f}", f"{net_change:+.5f}"
            else:
                val_fmt, cls_fmt, chg_fmt = f"{live_price:,.2f}", f"{prior_close:,.2f}", f"{net_change:+,.2f}"
                
            direction_icon = "🟢 BULLISH BIAS" if change_pct >= 0 else "🔴 BEARISH BIAS"
            trend_arrow = "📈" if change_pct >= 0 else "📉"
            
            return (
                f"{trend_arrow} **{display_name} METRICS**\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"• **Current Price:** `{val_fmt}`\n"
                f"• **Prior Session Close:** `{cls_fmt}`\n"
                f"• **Net Deviation:** `{chg_fmt}`\n"
                f"• **Percentage Shift:** `{change_pct:+.2f}%`\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📊 **Engine Bias:** `{direction_icon}`"
            )
        except Exception as err:
            logger.critical(f"Schema compilation exception parsing metrics block for {symbol}: {err}")
            return f"❌ **Processing Error:** Infrastructure fault processing metrics for `{display_name}`."
