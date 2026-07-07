from app.services.base_client import BaseAsyncClient
from app.config import settings
from app.logger import logger

class MarketDataService(BaseAsyncClient):
    """Direct targeting financial data fetching mechanism mapping individual asset classes."""
    
    def __init__(self):
        super().__init__(
            base_url="https://api.twelvedata.com", 
            default_params={"apikey": settings.market_api_key}
        )

    async def get_asset_report(self, symbol: str, display_name: str) -> str:
        """Fetches market arrays and dynamically builds a complete operational report based on prior close."""
        logger.info(f"Asynchronously calculating target reporting vectors for: {symbol}")
        
        data = await self._get("time_series", params={
            "symbol": symbol,
            "interval": "1day",
            "outputsize": "2"
        })
        
        if not data or "values" not in data:
            logger.error(f"Upstream API mapping structure failed or refused arrays for: {symbol}")
            return f"⚠️ **Data Fetch Error:** Unable to retrieve live calculation streams for `{display_name}` right now."
            
        try:
            time_series = data["values"]
            live_price = float(time_series[0]["close"])
            
            # CORE RULE COMPLIANCE: Calculate data strictly off the preceding trading day close
            prior_close = float(time_series[1]["close"])
            
            net_change = live_price - prior_close
            change_pct = (net_change / prior_close) * 100
            
            # Automated classification layout optimization mapping precision metrics
            is_jpy = "JPY" in symbol or "JP225" in display_name
            is_forex = "/" in symbol
            is_crypto = "BTC" in symbol or "ETH" in symbol or "BNB" in symbol
            
            if is_forex and not is_jpy:
                val_fmt = f"{live_price:.5f}"
                cls_fmt = f"{prior_close:.5f}"
                chg_fmt = f"{net_change:+.5f}"
            elif is_crypto or "US30" in display_name or "US100" in display_name or is_jpy:
                val_fmt = f"{live_price:,.2f}"
                cls_fmt = f"{prior_close:,.2f}"
                chg_fmt = f"{net_change:+,.2f}"
            else:
                val_fmt = f"{live_price:.2f}"
                cls_fmt = f"{prior_close:.2f}"
                chg_fmt = f"{net_change:+.2f}"
                
            direction_icon = "🟢 BULLISH BIAS" if change_pct >= 0 else "🔴 BEARISH BIAS"
            trend_arrow = "📈" if change_pct >= 0 else "📉"
            
            report = (
                f"{trend_arrow} **{display_name} INTELLIGENCE METRICS**\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"• **Current Market Price:** `{val_fmt}`\n"
                f"• **Prior Session Close:** `{cls_fmt}`\n"
                f"• **Net Deviation Vector:** `{chg_fmt}`\n"
                f"• **Percentage Variance:** `{change_pct:+.2f}%`\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📊 **Engine Core Bias:** `{direction_icon}`"
            )
            return report
            
        except (KeyError, IndexError, ValueError) as err:
            logger.critical(f"Data payload corruption or transformation anomaly on {symbol}: {err}")
            return f"❌ **Processing Error:** Structural schema failure while parsing `{display_name}` feeds."
