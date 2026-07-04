from app.services.supabase_client import supabase
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import cross_val_score
import numpy as np
from datetime import datetime

MODEL_VERSION = "v4.3.1"
FEATURE_SET_VERSION = "v1"

def get_training_data(asset: str, horizon='1d', min_samples=40):
    if not supabase:
        return None, None, None
    try:
        result = supabase.table('predictions').select(
            'tech_score, macro_score, sent_score, news_score, atr_ratio, corr_score, regime_probs, confidence, outcome_correct'
        ).eq('outcome_evaluated', True).eq('asset', asset).eq('horizon', horizon).execute()
        data = result.data
        if len(data) < min_samples:
            return None, None, None
        X, y = [], []
        for p in data:
            rp = p.get('regime_probs', {})
            X.append([
                p['tech_score'], p['macro_score'], p['sent_score'], p['news_score'],
                p.get('atr_ratio', 0.01), p.get('corr_score', 0),
                rp.get('RISK_OFF', 0), rp.get('INFLATION', 0), rp.get('RECESSION', 0),
                rp.get('EASING', 0), rp.get('TIGHTENING', 0), p.get('confidence', 50.0) / 100.0
            ])
            y.append(1 if p['outcome_correct'] else 0)
        return np.array(X), np.array(y), len(data)
    except Exception:
        return None, None, None

def train_model(asset: str, horizon='1d'):
    X, y, n = get_training_data(asset, horizon)
    if X is None or len(np.unique(y)) < 2:
        return None, None, None, None
    try:
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        base = LogisticRegression(C=0.5, max_iter=1000, class_weight='balanced')
        calibrated = CalibratedClassifierCV(base, method='sigmoid', cv=3)
        calibrated.fit(X_scaled, y)
        cv_score = cross_val_score(calibrated, X_scaled, y, cv=3).mean()
        return calibrated, scaler, n, cv_score
    except Exception:
        return None, None, None, None

def save_model(asset: str, horizon: str, model, scaler, n, cv_score):
    if not supabase or model is None:
        return
    try:
        if hasattr(model, 'calibrated_classifiers_') and len(model.calibrated_classifiers_) > 0:
            base_est = model.calibrated_classifiers_[0].base_estimator
            coefs = base_est.coef_.tolist()
            intercept = base_est.intercept_.tolist()
        else:
            coefs = [[0.0] * scaler.mean_.shape[0]]
            intercept = [0.0]
            
        model_data = {
            "asset": asset, "horizon": horizon, "model_version": MODEL_VERSION,
            "feature_set_version": FEATURE_SET_VERSION, "calibration_date": datetime.utcnow().isoformat(),
            "n_samples": n, "cv_score": float(cv_score), "coefs": coefs, "intercept": intercept,
            "scaler_mean": scaler.mean_.tolist(), "scaler_scale": scaler.scale_.tolist()
        }
        supabase.table('calibration_models').upsert(
            {"asset": asset, "horizon": horizon, "model_data": model_data},
            on_conflict=["asset", "horizon"]
        ).execute()
    except Exception as e:
        print(f"Failed model export configurations upload: {e}")

def load_model(asset: str, horizon='1d'):
    if not supabase:
        return None, None, None
    try:
        result = supabase.table('calibration_models').select('model_data').eq('asset', asset).eq('horizon', horizon).execute()
        if not result.data:
            return None, None, None
        return None, None, result.data[0]['model_data']
    except Exception:
        return None, None, None
