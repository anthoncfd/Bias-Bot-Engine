import httpx
from typing import Dict, Any
from app.logger import logger

class MacroSentimentEngine:
    """Processes macroeconomic variables and market risk metrics into normalized 
    directional values, ensuring consistency across all asset analysis models.
    """
    
    def __init__(self, http_client: httpx.AsyncClient):
        self.client = http_client
        self.browser_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    async def fetch_macro_raw_metrics(self) -> Dict[str, float]:
        """Queries live data tickers asynchronously to extract baseline macro metrics and risk gauges."""
        metrics = {
            "dxy": 103.50, "us10y": 4.10, "fed_rate": 5.25,
            "vix": 15.00, "fear_greed": 50.0
        }
        try:
            # Synchronize live indexes via browser-emulated public REST channels
            fng_res = await self.client.get("https://api.alternative.me/fng/?limit=1", headers=self.browser_headers, timeout=8.0)
            if fng_res.status_code == 200:
                fng_data = fng_res.json()
                metrics["fear_greed"] = float(fng_data.get("data", [{}])[0].get("value", 50.0))
                
            vix_res = await self.client.get("https://query1.finance.yahoo.com/v8/finance/chart/^VIX?range=1d&interval=1m", headers=self.browser_headers, timeout=8.0)
            if vix_res.status_code == 200:
                vix_meta = vix_res.json().get("chart", {}).get("result", [{}])[0].get("meta", {})
                vix_price = vix_meta.get("regularMarketPrice")
                if vix_price:
                    metrics["vix"] = float(vix_price)

            dxy_res = await self.client.get("https://query1.finance.yahoo.com/v8/finance/chart/DX-Y.NYB?range=1d&interval=1m", headers=self.browser_headers, timeout=8.0)
            if dxy_res.status_code == 200:
                dxy_meta = dxy_res.json().get("chart", {}).get("result", [{}])[0].get("meta", {})
                dxy_price = dxy_meta.get("regularMarketPrice")
                if dxy_price:
                    metrics["dxy"] = float(dxy_price)

        except Exception as err:
            logger.error(f"⚠️ Secondary macro data fetch warning: Underlying variables defaulted. Error: {err}")
            
        return metrics

    @staticmethod
    def calculate_normalized_scores(raw: Dict[str, float]) -> Dict[str, Any]:
        """Maps raw data points onto our standardized directional score scale
        (-100% to +100%), keeping everything aligned with our technical indicators.
        """
        # A higher VIX represents increased market fear, creating a bearish drag on risk assets
        vix_val = raw.get("vix", 15.0)
        vix_score = -100.0 if vix_val > 25.0 else 100.0 if vix_val < 12.0 else -float((vix_val - 12.0) / 13.0) * 200.0 + 100.0
        
        # Scale the Fear & Greed reading (0-100) symmetrically onto our center-zero grid (-100 to +100)
        fng_val = raw.get("fear_greed", 50.0)
        fng_score = float((fng_val - 50.0) * 2.0)
        
        sentiment_score = (vix_score * 0.40) + (fng_score * 0.60)
        
        # Higher interest rates and an aggressively strong dollar contract macro liquidity
        macro_score = 0.0
        if raw.get("dxy", 100.0) > 102.50: macro_score -= 40.0
        else: macro_score += 40.0
        if raw.get("us10y", 4.0) > 4.15: macro_score -= 30.0
        else: macro_score += 30.0
        if raw.get("fed_rate", 5.0) > 5.00: macro_score -= 30.0
        else: macro_score += 30.0
        
        return {
            "macro_score_pct": max(-100.0, min(100.0, macro_score)),
            "sentiment_score_pct": max(-100.0, min(100.0, sentiment_score)),
            "raw_data": raw
        }

