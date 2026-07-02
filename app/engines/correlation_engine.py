import yfinance as yf
import pandas as pd
import numpy as np
from app.services.price_service import PriceService
import logging

logger = logging.getLogger(__name__)

class CorrelationEngine:
    CORRELATION_MAP = {
        "xauusd": ["DX-Y.NYB", "^TNX", "^VIX"],
        "xagusd": ["DX-Y.NYB", "GC=F", "^VIX"],
        "eurusd": ["DX-Y.NYB", "^TNX"],
        "gbpusd": ["DX-Y.NYB", "^TNX"],
        "audusd": ["DX-Y.NYB", "CL=F"],
        "usdcad": ["CL=F", "DX-Y.NYB"],
        "btcusd": ["ETH-USD", "^IXIC", "DX-Y.NYB"],
        "ethusd": ["BTC-USD", "^IXIC", "DX-Y.NYB"],
        "us30": ["^VIX", "DX-Y.NYB"],
        "jp225": ["^VIX", "DX-Y.NYB"]
    }

    def __init__(self, lookback=30):
        self.lookback = lookback

    def get_correlation_score(self, asset: str, current_price: float) -> float:
        symbols = self.CORRELATION_MAP.get(asset, [])
        if not symbols:
            return 0.0
        price_service = PriceService()
        try:
            asset_df = price_service.get_historical_data(asset, days=self.lookback + 5)
            asset_ret = asset_df['Close'].pct_change().iloc[-self.lookback:]
        except Exception as e:
            logger.warning(f"Unable to process mathematical regression data frames for {asset}: {e}")
            return 0.0

        agreements = []
        for sym in symbols:
            try:
                ticker = yf.Ticker(sym)
                hist = ticker.history(period=f"{self.lookback + 8}d")
                if len(hist) < self.lookback:
                    continue
                returns = hist['Close'].pct_change().iloc[-self.lookback:]
                min_len = min(len(asset_ret), len(returns))
                if min_len < 12:
                    continue
                corr = asset_ret.iloc[-min_len:].corr(returns.iloc[-min_len:])
                
                z_corr = (hist['Close'].iloc[-1] - hist['Close'].tail(self.lookback).mean()) / hist['Close'].tail(self.lookback).std()
                z_asset = (current_price - asset_df['Close'].tail(self.lookback).mean()) / asset_df['Close'].tail(self.lookback).std()
                
                if not np.isnan(z_corr) and not np.isnan(z_asset):
                    agreement = 1 if (z_corr * z_asset) > 0 else -1
                    agreements.append(agreement * abs(corr))
            except Exception:
                continue

        if not agreements:
            return 0.0
        return float(np.clip(np.mean(agreements), -1, 1))
