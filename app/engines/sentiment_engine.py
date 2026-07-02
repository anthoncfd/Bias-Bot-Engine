import yfinance as yf
import requests
from app.models import SentimentData
import numpy as np
import logging

logger = logging.getLogger(__name__)

class SentimentEngine:
    def _fetch_yf_safely(self, symbol: str, default_val: float) -> float:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="3d")
            if not hist.empty:
                return float(hist['Close'].iloc[-1])
        except Exception:
            pass
        return default_val

    def fetch(self) -> SentimentData:
        vix = self._fetch_yf_safely("^VIX", 16.5)
        oil = self._fetch_yf_safely("CL=F", 75.0)
        
        # Robust CNN Fear & Greed parser with backup tracking formulas
        fear_greed = 50.0
        try:
            url = "https://production.dataviz.cnn.io/index/fearandgreed/current"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                fear_greed = float(resp.json().get('fear_and_greed', {}).get('score', 50.0))
            else:
                raise ValueError("API error response code")
        except Exception as e:
            logger.warning(f"CNN parsing execution broken ({e}). Executing fallback calculations via volatility index calculations.")
            fear_greed = float(max(5.0, min(95.0, 90.0 - (vix - 12.0) * 2.8)))
            
        risk_on = not (vix > 24.0 or fear_greed < 38.0)
        return SentimentData(vix=vix, fear_greed=fear_greed, oil=oil, risk_on=risk_on)

    def score(self, sent: SentimentData, asset: str) -> float:
        fg_score = (sent.fear_greed - 50.0) / 50.0
        vix_score = (20.0 - sent.vix) / 15.0
        score = 0.0
        
        if asset in ["xauusd", "xagusd"]:
            score += (sent.vix - 16.0) / 15.0 * 0.4
            score += fg_score * -0.3
        elif asset in ["us30", "jp225"]:
            score += fg_score * 0.5
            score += vix_score * 0.3
        elif asset in ["btcusd", "ethusd", "bnbusd"]:
            score += fg_score * 0.5
            score += (0.3 if sent.risk_on else -0.4)
        else:
            if asset in ["eurusd", "gbpusd", "audusd"]:
                score += (0.2 if sent.risk_on else -0.2)
            elif asset in ["usdchf", "usdcad"]:
                score += (-0.2 if sent.risk_on else 0.2)
                
        return float(np.clip(score, -1, 1))
