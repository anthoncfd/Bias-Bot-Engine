from app.services.supabase_client import supabase
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import pandas_market_calendars as mcal

class PredictionEvaluationEngine:
    @staticmethod
    def update_outcomes(horizon_days=1):
        if not supabase:
            return
        try:
            result = supabase.table('predictions').select('*').eq('outcome_evaluated', False).eq('horizon', f'{horizon_days}d').execute()
            for pred in result.data:
                asset = pred['asset']
                pred_time = pd.to_datetime(pred['timestamp'])
                nyse = mcal.get_calendar('NYSE')
                end_search = pred_time + timedelta(days=horizon_days * 4)
                trading_days = nyse.schedule(start_date=pred_time, end_date=end_search)
                
                if len(trading_days) < horizon_days:
                    target_date = pred_time + timedelta(days=horizon_days)
                else:
                    target_date = trading_days.iloc[horizon_days - 1]['market_close']
                    
                from app.services.price_service import PriceService
                ps = PriceService()
                hist = ps.get_historical_data(asset, days=horizon_days + 10)
                hist.index = pd.to_datetime(hist.index)
                
                valid_closes = hist[hist.index <= target_date]
                if valid_closes.empty:
                    continue
                target_close = valid_closes['Close'].iloc[-1]
                
                ret = (target_close - pred['price']) / pred['price'] * 100
                correct = (ret > 0) == (pred['bull_prob'] > 50)
                
                supabase.table('predictions').update({
                    'outcome_return': float(ret),
                    'outcome_correct': bool(correct),
                    'outcome_evaluated': True,
                    'evaluated_at': datetime.utcnow().isoformat()
                }).eq('id', pred['id']).execute()
        except Exception as e:
            print(f"Error calculating verification matrices across ledger indexes: {e}")

    @staticmethod
    def walk_forward_train(asset: str, horizon='1d'):
        from app.engines.calibration import train_model, save_model
        model, scaler, n, cv_score = train_model(asset, horizon)
        if model is not None:
            save_model(asset, horizon, model, scaler, n, cv_score)
        return model, scaler, n, cv_score
