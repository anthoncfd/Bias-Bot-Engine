from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, List

class PriceData(BaseModel):
    symbol: str
    current_price: float
    open: float
    high: float
    low: float
    previous_close: float
    timestamp: datetime
    provider: str = "unknown"
    provider_confidence: float = 0.0
    proxy_used: bool = False
    data_type: str = "last"

class TechnicalIndicators(BaseModel):
    sma20: float
    sma50: float
    z_score: float
    atr: float
    momentum: float
    slope: float
    distance_from_sma20: float

class MacroData(BaseModel):
    dxy: float
    us10y: float
    us2y: float
    fed_funds: float
    cpi_yoy: float
    payrolls: float
    pmi: float

class SentimentData(BaseModel):
    vix: float
    fear_greed: float
    oil: float
    risk_on: bool

class NewsItem(BaseModel):
    headline: str
    source: str
    asset_mentioned: str
    direction: int
    confidence: float

class AggregatedScores(BaseModel):
    tech_score: float
    macro_score: float
    sent_score: float
    news_score: float
    composite: float
