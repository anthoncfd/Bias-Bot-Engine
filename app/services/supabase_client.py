import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("macro_engine.services.supabase")

# Initialize client using service role or public anonymous tokens
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Optional[Client] = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

if not supabase:
    logger.error("Supabase initialization skipped. Environment keys missing.")


def log_prediction(
    asset: str, price: float, bull_prob: float, confidence: float, composite: float,
    tech: float, macro: float, sent: float, news: float, regime: str, regime_probs: dict,
    atr_ratio: float, corr_score: float,
    horizon: str = '1d', gate: str = '',
    model_version: str = 'v1', calibration_date: Optional[str] = None, sample_size: int = 0,
    data_source: str = 'unknown', proxy_used: bool = False
) -> None:
    """
    Saves a newly generated real-time quantitative asset bias prediction to the database.
    Called directly by the Telegram bot handling route wrapper.
    """
    if not supabase:
        logger.warning("Supabase engine inactive. Bypassing execution log event stream.")
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
        logger.error(f"Supabase persistence error encountered during audit logging for {asset}: {e}")


# --- BACKEND ML & OPTIMIZATION ACCESS ENGINE LAYER ---

def get_unevaluated_predictions(horizon: str = "1d") -> List[Dict[str, Any]]:
    """Fetches historical predictions requiring outcome evaluation."""
    if not supabase:
        return []
    try:
        response = supabase.table("predictions")\
            .select("*")\
            .eq("outcome_evaluated", False)\
            .eq("horizon", horizon)\
            .execute()
        return response.data or []
    except Exception as e:
        logger.error(f"Error reading pending evaluations from schema: {e}")
        return []


def update_prediction_outcome(prediction_id: int, outcome_data: Dict[str, Any]) -> None:
    """Saves historical evaluation states back to the ledger."""
    if not supabase:
        return
    try:
        supabase.table("predictions")\
            .update({**outcome_data, "outcome_evaluated": True, "evaluated_at": datetime.utcnow().isoformat()})\
            .eq("id", prediction_id)\
            .execute()
    except Exception as e:
        logger.error(f"Failed to update tracking verification for row ID {prediction_id}: {e}")


def upsert_model_calibration(asset: str, horizon: str, model_data: Dict[str, Any]) -> None:
    """Persists model structural components from automated GitHub Actions walk-forward runs."""
    if not supabase:
        return
    try:
        payload = {
            "asset": asset,
            "horizon": horizon,
            "model_data": model_data
        }
        supabase.table("calibration_models").upsert(payload, on_conflict="asset,horizon").execute()
    except Exception as e:
        logger.error(f"Failed to save ML model weights for {asset}: {e}")


def get_regime_weights(asset: str, regime: str) -> Optional[Dict[str, Any]]:
    """Loads optimized factor alpha allocations matching current macro structures."""
    if not supabase:
        return None
    try:
        response = supabase.table("weight_config")\
            .select("weights")\
            .eq("asset", asset)\
            .eq("regime", regime)\
            .execute()
        return response.data[0]["weights"] if response.data else None
    except Exception as e:
        logger.error(f"Error loading dynamic weight layouts for {asset} under {regime}: {e}")
        return None
