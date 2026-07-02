import numpy as np
from app.models import MacroData, SentimentData

class RegimeEngine:
    def classify(self, macro: MacroData, sent: SentimentData) -> dict:
        risk_off = float(np.clip((sent.vix - 15.0) / 10.0 + (50.0 - sent.fear_greed) / 30.0, 0, 1))
        inflation = float(np.clip((macro.cpi_yoy - 2.5) / 2.0, 0, 1))
        recession = float(np.clip((50.0 - macro.pmi) / 10.0 + (macro.us2y - macro.us10y) / 2.0, 0, 1))
        easing = float(np.clip((4.0 - macro.fed_funds) / 2.0, 0, 1))
        tightening = float(np.clip((macro.fed_funds - 4.0) / 2.0, 0, 1))
        
        risk_on = float(max(0.0, 1.0 - risk_off))
        
        scores = {"RISK_ON": risk_on, "RISK_OFF": risk_off, "INFLATION": inflation,
                  "RECESSION": recession, "EASING": easing, "TIGHTENING": tightening}
                  
        total = sum(scores.values())
        if total == 0:
            return {"RISK_ON": 1.0}
        return {k: v / total for k, v in scores.items()}
