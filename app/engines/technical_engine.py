import pandas as pd
import numpy as np
from app.models import TechnicalIndicators
import json

with open('app/config/thresholds.json') as f:
    THRESHOLDS = json.load(f)

class TechnicalEngine:
    @staticmethod
    def calculate(df: pd.DataFrame, current_price: float) -> TechnicalIndicators:
        if len(df) < 50:
            raise ValueError("Upstream tracking historical footprint threshold unsatisfied (< 50 data segments)")
        closes = df['Close']
        sma20 = closes.tail(20).mean()
        sma50 = closes.tail(50).mean()
        
        # Accurate Z-Score using rolling window standardization
        rolling_mean = closes.rolling(window=20).mean().iloc[-1]
        rolling_std = closes.rolling(window=20).std().iloc[-1]
        z_score = (current_price - rolling_mean) / rolling_std if rolling_std != 0 else 0
        
        high, low, close = df['High'], df['Low'], df['Close']
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Institutional standard Wilder's Smoothing for ATR
        atr = tr.ewm(alpha=1/14, adjust=False).mean().iloc[-1]
        
        momentum = ((current_price / closes.iloc[-5]) - 1) * 100 if len(closes) >= 5 else 0
        
        x = np.arange(len(closes.tail(20)))
        y = closes.tail(20).values
        slope, _ = np.polyfit(x, y, 1)
        normalized_slope = slope / current_price * 100
        distance_from_sma20 = ((current_price - sma20) / sma20) * 100
        
        return TechnicalIndicators(
            sma20=sma20,
            sma50=sma50,
            z_score=z_score,
            atr=atr,
            momentum=momentum,
            slope=normalized_slope,
            distance_from_sma20=distance_from_sma20
        )

    @staticmethod
    def score(indicators: TechnicalIndicators) -> float:
        t = THRESHOLDS['technical']
        z_score_raw = np.clip(indicators.z_score / t['z_score_clip'], -1, 1)
        dist_raw = np.clip(indicators.distance_from_sma20 / t['distance_clip'], -1, 1)
        mom_raw = np.clip(indicators.momentum / t['momentum_clip'], -1, 1)
        slope_raw = np.clip(indicators.slope / t['slope_clip'], -1, 1)
        
        vol_regime = 1 - (indicators.atr / indicators.sma20) * t['atr_volatility_factor'] if indicators.sma20 > 0 else 1
        vol_regime = np.clip(vol_regime, 0, 1)
        
        raw_score = 0.35 * z_score_raw + 0.25 * dist_raw + 0.20 * mom_raw + 0.20 * slope_raw
        return float(np.clip(raw_score * vol_regime, -1, 1))
