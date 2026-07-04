import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from app.services.supabase_client import supabase

class TradeQualityEngine:
    _models = {}
    _scalers = {}

    @classmethod
    def get_model(cls, asset: str):
        if asset not in cls._models:
            if not supabase:
                return None, None
            try:
                result = supabase.table('predictions').select(
                    'tech_score, macro_score, sent_score, news_score, atr_ratio, corr_score, confidence, outcome_correct'
                ).eq('outcome_evaluated', True).eq('asset', asset).execute()
                data = result.data
                if len(data) < 20: 
                    return None, None
                    
                X = np.array([[p['tech_score'], p['macro_score'], p['sent_score'], p['news_score'],
                               p.get('atr_ratio', 0.01), p.get('corr_score', 0), p.get('confidence', 0.5) / 100.0] for p in data])
                y = np.array([1 if p['outcome_correct'] else 0 for p in data])
                
                scaler = StandardScaler()
                X_scaled = scaler.fit_transform(X)
                model = LogisticRegression(class_weight='balanced').fit(X_scaled, y)
                
                cls._models[asset] = model
                cls._scalers[asset] = scaler
            except Exception:
                return None, None
        return cls._models.get(asset), cls._scalers.get(asset)

    @classmethod
    def score(cls, asset: str, tech, macro, sent, news, atr_ratio, corr, confidence):
        model, scaler = cls.get_model(asset)
        if model is None:
            q = 0.0
            if abs(tech) > 0.15: q += 0.2
            if abs(macro) > 0.15: q += 0.2
            if abs(sent) > 0.15: q += 0.15
            if abs(news) > 0.15: q += 0.15
            if confidence > 65.0: q += 0.15
            if corr > 0.25: q += 0.15
            return float(min(1.0, q))
        try:
            features = np.array([[tech, macro, sent, news, atr_ratio, corr, confidence / 100.0]])
            X_scaled = scaler.transform(features)
            prob = model.predict_proba(X_scaled)[0][1]
            return float(prob)
        except Exception:
            return 0.5
