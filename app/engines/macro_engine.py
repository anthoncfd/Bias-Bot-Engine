import yfinance as yf
from fredapi import Fred
from app.config import FRED_API_KEY
from app.models import MacroData
from datetime import datetime
import numpy as np
import json
import logging

logger = logging.getLogger(__name__)

class MacroEngine:
    def __init__(self):
        self.fred = Fred(api_key=FRED_API_KEY) if FRED_API_KEY else None
        with open('app/config/weights.json') as f:
            self.weights_config = json.load(f)

    def _fetch_yf_safely(self, symbol: str, default_val: float) -> float:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d")
            if not hist.empty:
                return float(hist['Close'].iloc[-1])
        except Exception as e:
            logger.warning(f"Macro parser anomaly processing token index symbol {symbol}: {e}")
        return default_val

    def fetch(self):
        dxy = self._fetch_yf_safely("DX-Y.NYB", 102.0)
        us10y = self._fetch_yf_safely("^TNX", 4.2)
        us2y = self._fetch_yf_safely("^FVX", 4.5)
        
        fed_funds, cpi, payrolls, pmi = 5.25, 3.0, 180.0, 49.5
        fed_ts = cpi_ts = datetime.utcnow()
        
        if self.fred:
            try:
                fed_series = self.fred.get_series('FEDFUNDS')
                if not fed_series.empty:
                    fed_funds = float(fed_series.iloc[-1])
                    fed_ts = fed_series.index[-1]
                
                cpi_series = self.fred.get_series('CPIAUCSL')
                if len(cpi_series) >= 13:
                    cpi = float(cpi_series.pct_change(12).iloc[-1] * 100)
                    cpi_ts = cpi_series.index[-1]
                    
                payrolls_series = self.fred.get_series('PAYEMS')
                if len(payrolls_series) >= 2:
                    payrolls = float(payrolls_series.diff().iloc[-1] / 1000)
                    
                pmi_series = self.fred.get_series('NAPM')
                if not pmi_series.empty:
                    pmi = float(pmi_series.iloc[-1])
            except Exception as e:
                logger.error(f"FRED pipeline parse fault. Engaging software fallbacks: {e}")

        macro = MacroData(dxy=dxy, us10y=us10y, us2y=us2y, fed_funds=fed_funds,
                          cpi_yoy=cpi, payrolls=payrolls, pmi=pmi)
        timestamps = {'dxy': datetime.utcnow(), 'us10y': datetime.utcnow(), 'fred_fed': fed_ts, 'fred_cpi': cpi_ts}
        return macro, timestamps

    def score(self, macro: MacroData, asset: str, surprises: dict = None) -> float:
        weights = self.weights_config.get(asset, {}).get('macro_weights', {})
        if not weights:
            weights = {'dxy': -0.3, 'us10y': -0.2, 'cpi_yoy': -0.2, 'fed_funds': -0.2, 'pmi': 0.1}
            
        dxy_score = (101.5 - macro.dxy) / 4.0
        us10y_score = (4.0 - macro.us10y) / 1.5
        cpi_score = (2.5 - macro.cpi_yoy) / 1.5
        fed_score = (4.25 - macro.fed_funds) / 1.5
        pmi_score = (macro.pmi - 50.0) / 7.0
        
        raw = (weights.get('dxy', 0) * dxy_score + 
               weights.get('us10y', 0) * us10y_score +
               weights.get('cpi_yoy', 0) * cpi_score + 
               weights.get('fed_funds', 0) * fed_score +
               weights.get('pmi', 0) * pmi_score)
               
        return float(np.clip(raw, -1, 1))
