import httpx
import asyncio
import yfinance as yf
from datetime import datetime, timezone, timedelta
from app.config import settings
from app.logger import logger
from app.services.quant_math import QuantitativeMathEngine

class MarketDataService:
    """Enterprise-grade hybrid financial broker utilizing transaction-style time-series 
    storage to build proprietary historical data stores efficiently.
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
        """Retrieves and compiles a 30-bar array from our continuous, cumulative table rows."""
        clean_symbol = symbol.replace("/", "").strip().upper()
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                url = f"{self.db_url}?symbol=eq.{clean_symbol}&order=date.desc&limit=35"
                res = await client.get(url, headers=self.db_headers)
                if res.status_code == 200 and res.json():
                    return [{"datetime": row["date"], "close": str(row["close"])} for row in res.json()]
            except Exception as err:
                logger.error(f"Local Supabase transaction read breakdown on {clean_symbol}: {err}")
            return None

    async def sync_asset_historical_cache(self, symbol: str, force_refresh: bool = False) -> list | None:
        """Saves daily closes into unique, cumulative historical rows without wiping anything."""
        clean_symbol = symbol.replace("/", "").strip().upper()
        existing = await self.fetch_cached_history(clean_symbol)
        
        # Calculate localized system dates
        local_today = datetime.now().strftime("%Y-%m-%d")
        local_yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # 🛡️ SYSTEM DATA SHIELD: Skip upstream vendors if local database storage layer is perfectly fresh
        if not force_refresh and existing and len(existing) >= 20:
            if existing[0]["datetime"] in [local_today, local_yesterday]:
                return existing

        logger.info(f"📡 Processing asset transaction adjustments for: {clean_symbol}")
        is_crypto = clean_symbol in ["BTCUSD", "ETHUSD", "BNBUSD"]
        bars = []
        
        # 🛠️ DELTA OPTIMIZATION: If data exists but needs an update, fetch only the single latest day
        fetch_period = "45d" if (not existing or len(existing) < 5 or force_refresh) else "3d"
        twelve_output_size = "30" if (not existing or len(existing) < 5 or force_refresh) else "3"

        if clean_symbol.startswith("^") or "=" in clean_symbol or is_crypto:
            yf_ticker = "BTC-USD" if clean_symbol == "BTCUSD" else "ETH-USD" if clean_symbol == "ETHUSD" else "BNB-USD" if clean_symbol == "BNBUSD" else clean_symbol
            ticker = yf.Ticker(yf_ticker)
            hist = ticker.history(period=fetch_period)
            if not hist.empty:
                hist = hist.sort_index(ascending=False)
                # For standard updates, safely slice only the single newest candle bar
                if fetch_period == "3d":
                    hist = hist.head(1)
                for idx, row in hist.iterrows():
                    bars.append({"symbol": clean_symbol, "date": idx.strftime("%Y-%m-%d"), "close": float(row['Close'])})
        else:
            async with httpx.AsyncClient(timeout=10.0) as client:
                try:
                    twelve_symbol = f"{clean_symbol[:3]}/{clean_symbol[3:]}"
                    params = {"symbol": twelve_symbol, "interval": "1day", "outputsize": twelve_output_size, "apikey": settings.market_api_key}
                    res = await client.get(f"{self.twelve_base}/time_series", params=params)
                    if res.status_code == 200 and "values" in res.json():
                        values_payload = res.json()["values"]
                        if fetch_period == "3d" and values_payload:
                            values_payload = [values_payload[0]]
                        for val in values_payload:
                            bars.append({"symbol": clean_symbol, "date": val["datetime"], "close": float(val["close"])})
                except Exception as err:
                    logger.error(f"Twelve Data history call crash for {clean_symbol}: {err}")

        if bars:
            async with httpx.AsyncClient(timeout=15.0) as client:
                await client.post(self.db_url, headers=self.db_headers, json=bars)
                
        return await self.fetch_cached_history(clean_symbol)

    async def get_asset_report(self, symbol: str, display_name: str) -> str:
        """Processes and parses our multi-row data store tables into our mathematical risk templates."""
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
            if not historical_bars or len(historical_bars) < 20:
                logger.info(f"🔄 JIT Activation: Re-building background lookbacks on-demand for {clean_symbol}")
                historical_bars = await self.sync_asset_historical_cache(clean_symbol, force_refresh=True)
                
            if not historical_bars or len(historical_bars) < 2:
                return f"⚠️ **Cache Warm-up:** Building your historical archive for `{display_name}`. Re-query in 5 seconds."

            # 🧠 HARDENED PREVIOUS CLOSE CALCULATOR
            local_today = datetime.now().strftime("%Y-%m-%d")
            prior_close = None
            
            for bar in historical_bars:
                if bar["datetime"] < local_today:
                    prior_close = float(bar["close"])
                    break
                    
            if prior_close is None:
                prior_close = float(historical_bars[0]["close"])

            net_change = live_price - prior_close
            change_pct = (net_change / prior_close) * 100
            
            mc = QuantitativeMathEngine.calculate_monte_carlo(live_price, historical_bars)
            prob_up = mc['prob_up']
            prob_down = mc['prob_down']
            
            if prob_up > prob_down and net_change > 0:
                direction_icon = "🟢 BULLISH BIAS"
                trend_arrow = "📈"
                distribution_edge = f"🟢 Long Advantage ({prob_up:.1f}%)"
            elif prob_down > prob_up and net_change < 0:
                direction_icon = "🔴 BEARISH BIAS"
                trend_arrow = "📉"
                distribution_edge = f"🔴 Short Advantage ({prob_down:.1f}%)"
            elif prob_up > prob_down and net_change <= 0:
                direction_icon = "🟡 CONDITIONAL BULLISH DRIFT"
                trend_arrow = "⚡"
                distribution_edge = f"🟡 Long Skew / Counter-Trend ({prob_up:.1f}%)"
            elif prob_down > prob_up and net_change >= 0:
                direction_icon = "🟡 CONDITIONAL BEARISH DRIFT"
                trend_arrow = "⚡"
                distribution_edge = f"🔴 Short Skew / Counter-Trend ({prob_down:.1f}%)"
            else:
                direction_icon = "⚪ NEUTRAL RANDOM WALK"
                trend_arrow = "⚡"
                distribution_edge = "⚪ Balanced Distribution"
            
            is_index_or_jpy = "JPY" in clean_symbol or clean_symbol.startswith("^") or "=" in clean_symbol
            
            if is_crypto or is_index_or_jpy:
                val_fmt, cls_fmt, chg_fmt = f"{live_price:,.2f}", f"{prior_close:,.2f}", f"{net_change:+,.2f}"
                ev_fmt = f"{mc['expected_value']:,.2f}"
            else:
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
