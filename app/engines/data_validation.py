from app.models import PriceData
import pandas as pd
from datetime import datetime
import numpy as np

class DataValidationError(Exception):
    pass

class DataValidationEngine:
    @staticmethod
    def validate_price(price: PriceData, hist: pd.DataFrame, max_age_seconds=300, outlier_std=4.5) -> PriceData:
        age = (datetime.utcnow() - price.timestamp).total_seconds()
        if age > max_age_seconds:
            raise DataValidationError(f"Inbound stream parsing halted: Data stale by {age:.0f}s")
            
        if hist is not None and len(hist) > 20:
            recent = hist['Close'].tail(20)
            mean = recent.mean()
            std = recent.std()
            if std > 0 and abs(price.current_price - mean) / std > outlier_std:
                raise DataValidationError(f"Outlier threshold violated. Current asset metric data anomalous: {price.current_price}")
                
        if any(np.isnan([price.current_price, price.open, price.high, price.low, price.previous_close])):
            raise DataValidationError("System NaN exception triggered in numerical verification step.")
            
        return price
