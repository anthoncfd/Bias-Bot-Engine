import yfinance as yf
import pandas as pd
import requests
from datetime import datetime
from cachetools import TTLCache
import logging
import time
from app.models import PriceData
from app.config import ASSET_MAP

logger = logging.getLogger(__name__)
price_cache = TTLCache(maxsize=100, ttl=10)

class YahooFinanceProvider:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

    def get_live_price(self, symbol: str, retries=5, backoff=2) -> PriceData:
        yf_sym = ASSET_MAP.get(symbol.lower())
        if not yf_sym:
            raise ValueError(f"No execution ticker mapped for asset key: {symbol}")
        
        for attempt in range(retries):
            try:
                df = yf.download(yf_sym, period="3d", session=self.session, progress=False)
                if df.empty:
                    raise ValueError(f"Null data frame from Yahoo engine for asset signature {yf_sym}")
                current = float(df['Close'].iloc[-1])
                prev = float(df['Close'].iloc[-2]) if len(df) > 1 else current
                return PriceData(
                    symbol=symbol,
                    current_price=current,
                    open=float(df['Open'].iloc[-1]),
                    high=float(df['High'].iloc[-1]),
                    low=float(df['Low'].iloc[-1]),
                    previous_close=prev,
                    timestamp=datetime.utcnow(),
                    provider="yahoo",
                    provider_confidence=0.85,
                    proxy_used=False,
                    data_type="last"
                )
            except Exception as e:
                if attempt == retries - 1:
                    raise e
                logger.warning(f"Yahoo data matrix extraction throttled. Retrying in {backoff}s...")
                time.sleep(backoff)
                backoff *= 2

    def get_historical(self, symbol: str, days: int = 60, retries=5, backoff=2) -> pd.DataFrame:
        yf_sym = ASSET_MAP.get(symbol.lower())
        if not yf_sym:
            raise ValueError(f"No execution ticker mapped for asset key: {symbol}")
        
        for attempt in range(retries):
            try:
                df = yf.download(yf_sym, period=f"{days + 10}d", session=self.session, progress=False)
                if df.empty:
                    raise ValueError(f"Historical index stream empty for asset matrix {yf_sym}")
                df.index = pd.to_datetime(df.index)
                return df[['Open', 'High', 'Low', 'Close', 'Volume']].tail(days)
            except Exception as e:
                if attempt == retries - 1:
                    raise e
                logger.warning(f"Yahoo history mapping exception encountered. Retrying in {backoff}s...")
                time.sleep(backoff)
                backoff *= 2

class PriceService:
    def __init__(self):
        self.yahoo = YahooFinanceProvider()

    def get_price(self, symbol: str) -> PriceData:
        cache_key = f"price_{symbol.lower()}"
        if cache_key in price_cache:
            return price_cache[cache_key]

        data = self.yahoo.get_live_price(symbol)

        if data is None:
            raise ValueError(f"Price resolution fault occurred across execution layer processing {symbol}")

        price_cache[cache_key] = data
        return data

    def get_historical_data(self, symbol: str, days: int = 60) -> pd.DataFrame:
        return self.yahoo.get_historical(symbol, days)
