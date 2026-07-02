import numpy as np
from app.engines.calibration import load_model, MODEL_VERSION
from app.services.supabase_client import supabase
from cachetools import TTLCache
import json

with open('app/config/thresholds.json') as f:
    THRESHOLDS = json.load(f)

class ProbabilityEngine:
    _cache = TTLCache(maxsize=50, ttl=86400)
    _model_cache = TTLCache(maxsize=50, ttl=86400)

    def __init__(self, horizon='1d'):
        self.horizon = horizon

    def _get_model(self, asset: str):
        if asset in self._model_cache:
            return self._model_cache[asset]
        model, scaler, model_data = load_model(asset, self.horizon)
        if model_data is not None:
            coefs = np.array(model_data['coefs'])
            intercept = np.array(model_data['intercept'])
            scaler_mean = np.array(model_data['scaler_mean'])
            scaler_scale = np.array(model_data['scaler_scale'])
            def predict_proba(features):
                z = np.dot(features, coefs.T) + intercept
                return 1 / (1 + np.exp(-z))
            def transform(features):
                return (features - scaler_mean) / scaler_scale
            self._model_cache[asset] = (predict_proba, transform, model_data)
        else:
            self._model_cache[asset] = (None, None, None)
        return self._model_cache[asset]

    def calculate(self, scores, atr_ratio, asset: str, regime_probs: dict, corr_score: float, news_conf: float):
        predict_func, transform_func, model_data = self._get_model(asset)
        if predict_func is not None and transform_func is not None:
            features = np.array([
                scores.tech_score, scores.macro_score, scores.sent_score, scores.news_score,
                atr_ratio, corr_score,
                regime_probs.get('RISK_OFF', 0), regime_probs.get('INFLATION', 0),
                regime_probs.get('RECESSION', 0), regime_probs.get('EASING', 0),
                regime_probs.get('TIGHTENING', 0), news_conf
            ]).reshape(1, -1)
            X_scaled = transform_func(features)
            prob = float(predict_func(X_scaled)[0])
            model_used = model_data['model_version']
            sample_size = model_data['n_samples']
        else:
            k = THRESHOLDS['probability']['logistic_k']
            bias = THRESHOLDS['probability']['logistic_bias']
            prob = float(1 / (1 + np.exp(-(k * scores.composite + bias))))
            model_used = "calibrated_fallback_v4.2"
            sample_size = 0

        acc = self._get_historical_accuracy(asset)
        raw_conf = abs(scores.composite) * 0.7 + 0.3 * (1 - min(1, atr_ratio * THRESHOLDS['confidence']['volatility_penalty_factor']))
        raw_conf = np.clip(raw_conf, THRESHOLDS['confidence']['min_confidence'], THRESHOLDS['confidence']['max_confidence'])
        calibrated_conf = raw_conf * min(1.0, acc / 0.7)
        
        return {
            "bullish_probability": prob * 100,
            "bearish_probability": (1 - prob) * 100,
            "confidence": float(np.clip(calibrated_conf, 0.1, 0.95) * 100),
            "regime": max(regime_probs, key=regime_probs.get),
            "model_version": model_used,
            "sample_size": sample_size
        }

    def _get_historical_accuracy(self, asset: str) -> float:
        if not supabase:
            return 0.7
        try:
            result = supabase.table('predictions').select('outcome_correct').eq('outcome_evaluated', True).eq('asset', asset).execute()
            if not result.data:
                return 0.7
            correct = sum(1 for p in result.data if p['outcome_correct'])
            return correct / len(result.data)
        except Exception:
            return 0.7
