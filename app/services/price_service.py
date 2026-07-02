import yfinance as yf
import pandas as pd
import requests
from datetime import datetime
from cachetools import TTLCache
import logging
import time
from app.models import PriceData
from app.config import ASSET_MAP, GOLDAPI_KEY
from app.services.gold_data_cacher import get_historical_from_cache

logger = logging.getLogger(__name__)
price_cache = TTLCache(maxsize=100, ttl=10)

class GoldAPIProvider:
    BASE_URL = "https://www.goldapi.io"
    SYMBOL_MAP = {"xauusd": "XAU", "xagusd": "XAG"}
    CURRENCY = "USD"

    def __init__(self):
        if not GOLDAPI_KEY:
            raise ValueError("GOLDAPI_KEY is missing from configuration parameters.")

    def get_live_price(self, symbol: str) -> PriceData:
        metal = self.SYMBOL_MAP.get(symbol.lower())
        if not metal:
            raise ValueError(f"GoldAPI unsupported asset profile: {symbol}")
        url = f"{self.BASE_URL}/api/{metal}/{self.CURRENCY}"
        headers = {"x-access-token": GOLDAPI_KEY, "Content-Type": "application/json"}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        price = float(data.get('price', 0))
        if price <= 0:
            raise ValueError(f"Anomalous market metric delivered from GoldAPI matrix: {data}")
        return PriceData(
            symbol=symbol,
            current_price=price,
            open=float(data.get('open_price', price)),
            high=float(data.get('high_price', price)),
            low=float(data.get('low_price', price)),
            previous_close=float(data.get('prev_close_price', price)),
            timestamp=datetime.utcnow(),
            provider="goldapi",
            provider_confidence=0.98,
            proxy_used=False,
            data_type="last"
        )

    def get_historical(self, symbol: str, days: int = 60) -> pd.DataFrame:
        metal = self.SYMBOL_MAP.get(symbol.lower())
        if not metal:
            raise ValueError(f"GoldAPI unsupported asset profile: {symbol}")
        df = get_historical_from_cache(metal, days)
        if df is not None and len(df) >= days - 5:
            return df[['Open', 'High', 'Low', 'Close']]

        logger.warning(f"Cache miss for structural metals matrix ({symbol}). Querying API directly...")
        url = f"{self.BASE_URL}/api/{metal}/{self.CURRENCY}/history/{days}"
        headers = {"x-access-token": GOLDAPI_KEY, "Content-Type": "application/json"}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            raise ValueError("Historical ledger returned null metrics from upstream GoldAPI provider.")
        records = []
        for item in data:
            date_str = item.get('date')
            if not date_str:
                continue
            try:
                date = datetime.fromtimestamp(date_str) if isinstance(date_str, (int, float)) else pd.to_datetime(date_str)
            except Exception:
                continue
            records.append({
                'Date': date,
                'Open': float(item.get('open', 0)),
                'High': float(item.get('high', 0)),
                'Low': float(item.get('low', 0)),
                'Close': float(item.get('close', 0)),
            })
        if not records:
            raise ValueError("No historical indices resolved successfully from data stream.")
        df = pd.DataFrame(records).sort_values('Date').set_index('Date')
        return df

class YahooFinanceProvider:
    def get_live_price(self, symbol: str, retries=3, backoff=1.5) -> PriceData:
        yf_sym = ASSET_MAP.get(symbol.lower())
        if not yf_sym:
            raise ValueError(f"No execution ticker mapped for asset key: {symbol}")
        
        for attempt in range(retries):
            try:
                ticker = yf.Ticker(yf_sym)
                hist = ticker.history(period="3d")
                if hist.empty:
                    raise ValueError(f"Null data frame from Yahoo engine for asset signature {yf_sym}")
                current = float(hist['Close'].iloc[-1])
                prev = float(hist['Close'].iloc[-2]) if len(hist) > 1 else current
                return PriceData(
                    symbol=symbol,
                    current_price=current,
                    open=float(hist['Open'].iloc[-1]),
                    high=float(hist['High'].iloc[-1]),
                    low=float(hist['Low'].iloc[-1]),
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

    def get_historical(self, symbol: str, days: int = 60, retries=3, backoff=1.5) -> pd.DataFrame:
        yf_sym = ASSET_MAP.get(symbol.lower())
        if not yf_sym:
            raise ValueError(f"No execution ticker mapped for asset key: {symbol}")
        
        for attempt in range(retries):
            try:
                ticker = yf.Ticker(yf_sym)
                df = ticker.history(period=f"{days + 10}d")
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
        self.metals_provider = GoldAPIProvider() if GOLDAPI_KEY else None
        self.yahoo = YahooFinanceProvider()
        self.gold_silver_assets = {"xauusd", "xagusd"}

    def get_price(self, symbol: str) -> PriceData:
        cache_key = f"price_{symbol.lower()}"
        if cache_key in price_cache:
            return price_cache[cache_key]

        if symbol.lower() in self.gold_silver_assets:
            if not self.metals_provider:
                logger.warning("GoldAPI key unavailable. Routing precious metals requests to Yahoo Finance platform...")
                data = self.yahoo.get_live_price(ASSET_MAP.get(symbol.lower(), symbol))
            else:
                data = self.metals_provider.get_live_price(symbol)
        else:
            data = self.yahoo.get_live_price(symbol)

        if data is None:
            raise ValueError(f"Price resolution fault occurred across execution layer processing {symbol}")

        price_cache[cache_key] = data
        return data

    def get_historical_data(self, symbol: str, days: int = 60) -> pd.DataFrame:
        if symbol.lower() in self.gold_silver_assets:
            if not self.metals_provider:
                return self.yahoo.get_historical(ASSET_MAP.get(symbol.lower(), symbol), days)
            return self.metals_provider.get_historical(symbol, days)
        return self.yahoo.get_historical(symbol, days)
