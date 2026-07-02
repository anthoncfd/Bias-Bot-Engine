from supabase import create_client, Client
from app.config import SUPABASE_URL, SUPABASE_KEY
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

def log_prediction(
    asset, price, bull_prob, confidence, composite,
    tech, macro, sent, news, regime, regime_probs,
    atr_ratio, corr_score,
    horizon='1d', gate='',
    model_version='v1', calibration_date=None, sample_size=0,
    data_source='unknown', proxy_used=False
):
    if not supabase:
        return
    data = {
        "asset": asset,
        "price": price,
        "bull_prob": bull_prob,
        "confidence": confidence,
        "composite": composite,
        "tech_score": tech,
        "macro_score": macro,
        "sent_score": sent,
        "news_score": news,
        "regime": regime,
        "regime_probs": regime_probs,
        "atr_ratio": atr_ratio,
        "corr_score": corr_score,
        "horizon": horizon,
        "gate": gate,
        "model_version": model_version,
        "calibration_date": calibration_date or datetime.utcnow().isoformat(),
        "sample_size": sample_size,
        "data_source": data_source,
        "proxy_used": proxy_used,
        "timestamp": datetime.utcnow().isoformat(),
        "outcome_evaluated": False
    }
    try:
        supabase.table("predictions").insert(data).execute()
    except Exception as e:
        logger.error(f"Supabase persistence error encountered during audit logging: {e}")
