import httpx
import asyncio
import yfinance as yf
import numpy as np
from datetime import datetime
from app.config import settings
from app.logger import logger
from app.services.quant_math import QuantitativeMathEngine

class MarketDataService:
    """Institutional-grade financial broker utilizing explicit routing boundaries and zero-fail fallbacks."""
    
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
        """Queries uncapped public Binance endpoints with strict explicit fallback mappings."""
        try:
            # Explicit String Mapping Matrix - Completely removes automated string parsing risks
            mapping = {
                "BTCUSD": "BTCUSDT",
                "ETHUSD": "ETHUSDT",
                "BNBUSD": "BNBUSDT",
                "BTC/USD": "BTCUSDT",
                "ETH/USD": "ETHUSDT",
                "BNB/USD": "BNBUSDT"
            }
            
            clean_symbol = symbol.strip().upper()
            binance_symbol = mapping.get(clean_symbol, f"{clean_symbol.replace('/', '')}USDT")

            # Enforce clear, explicit string checks
            if binance_symbol == "BTCUSDUSDT": binance_symbol = "BTCUSDT"
            if binance_symbol == "ETHUSDUSDT": binance_symbol = "ETHUSDT"
            if binance_symbol == "BNBUSDUSDT": binance_symbol = "BNBUSDT"

            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                res = await client.get(f"{self.binance_base}/ticker/price", params={"symbol": binance_symbol})
                if res.status_code == 200:
                    return float(res.json()["price"])
                
                # Internal Failover Path: If Binance encounters a geo-restriction, leverage alternative public stream
                alt_res = await client.get(f"https://api.coingecko.com/api/v3/simple/price", params={
                    "ids": "bitcoin" if "BTC" in binance_symbol else "ethereum" if "ETH" in binance_symbol else "binancecoin",
                    "vs_currencies": "usd"
                })
                if alt_res.status_code == 200:
                    key = "bitcoin" if "BTC" in binance_symbol else "ethereum" if "ETH" in binance_symbol else "binancecoin"
                    return float(alt_res.json()[key]["usd"])

        except Exception as err:
            logger.error(f"Failed pulling public crypto matrix feed for {symbol}: {err}")
        return None

    def _fetch_yf_live(self, symbol: str) -> float | None:
        """Synchronous isolated helper with strict thread-safe download parameters."""
        try:
            # Use direct network downloading instead of accessing ticker dictionary variables
            data = yf.download(tickers=symbol, period="1d", interval="1m", progress=False, verbose=False)
            if not data.empty and 'Close' in data.columns:
                # Target the absolute latest live 1-minute candle tick price node
                return float(data['Close'].iloc[-1])
        except Exception as err:
            logger.error(f"Yahoo Finance live download network execution failure for {symbol}: {err}")
        
        # Emergency Index Recovery Track: Attempt standard fast_info parsing if the downloader drops
        try:
            ticker = yf.Ticker(symbol)
            val = ticker.fast_info.get('last_price')
            if val is not None and val > 0:
                return float(val)
        except Exception:
            pass
        return None

    async def get_live_market_price(self, symbol: str) -> float | None:
        """Routes index assets directly to Yahoo Finance threads and fiat pairs to Twelve Data."""
        if symbol.startswith("^"):
            return await asyncio.to_thread(self._fetch_yf_live, symbol)
            
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
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
        async with httpx.AsyncClient(timeout=15.0) as client:
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
                async with httpx.AsyncClient(timeout=15.0) as client:
                    payload = {"symbol": symbol, "historical_bars": formatted_bars, "updated_at": datetime.utcnow().isoformat()}
                    await client.post(self.db_url, headers=self.db_headers, json=payload)
            return

        async with httpx.AsyncClient(timeout=15.0) as client:
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
        """Combines structural daily data with live pricing and routes statistical arrays to the Math Engine module."""
        is_crypto = symbol.replace("/", "").strip().upper() in ["BTCUSD", "ETHUSD", "BNBUSD"]
        
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
            if not historical_bars or len(historical_bars) < 2:
                return f"⚠️ **Cache Warm-up:** Building records for `{display_name}`. Try again in 5 seconds."
            
            today_str = datetime.utcnow().strftime("%Y-%m-%d")
            target_index = 0
            
            if historical_bars[0]["datetime"] == today_str:
                if len(historical_bars) > 1:
                    target_index = 1
                    
            prior_close = float(historical_bars[target_index]["close"])
            net_change = live_price - prior_close
            change_pct = (net_change / prior_close) * 100
            
            # Call our isolated math engine layer
            mc = QuantitativeMathEngine.calculate_monte_carlo(live_price, historical_bars)
            
            is_index_or_jpy = "JPY" in symbol or symbol.startswith("^")
            if "/" in symbol and not is_index_or_jpy:
                val_fmt, cls_fmt, chg_fmt = f"{live_price:.5f}", f"{prior_close:.5f}", f"{net_change:+.5f}"
                ev_fmt = f"{mc['expected_value']:.5f}"
            else:
                val_fmt, cls_fmt, chg_fmt = f"{live_price:,.3f}", f"{prior_close:,.3f}", f"{net_change:+,.3f}"
                ev_fmt = f"{mc['expected_value']:,.3f}"
                
            direction_icon = "🟢 BULLISH BIAS" if change_pct >= 0 else "🔴 BEARISH BIAS"
            trend_arrow = "📈" if change_pct >= 0 else "📉"
            
            distribution_edge = f"🟢 Long Advantage ({mc['prob_up']:.1f}%)" if mc['prob_up'] >= 52.0 else \
                                f"🔴 Short Advantage ({mc['prob_down']:.1f}%)" if mc['prob_down'] >= 52.0 else \
                                "⚪ Balanced Random Walk"
            
            kelly_str = f"`{mc['kelly_suggested_allocation_pct']:.1f}%` Max Account Risk Limit" if mc['kelly_suggested_allocation_pct'] > 0 else "`0.0%` (No Mathematical Edge Present)"

            return (
                f"{trend_arrow} **{display_name} METRICS**\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"• **Current Price:** `{val_fmt}`\n"
                f"• **Previous Close:** `{cls_fmt}`\n"
                f"• **Net Deviation:** `{chg_fmt}`\n"
                f"• **Percentage Shift:** `{change_pct:+.2f}%`\n"
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
            logger.critical(f"Schema compilation exception parsing metrics block for {symbol}: {err}")
            return f"❌ **Processing Error:** Infrastructure fault processing metrics for `{display_name}`."
