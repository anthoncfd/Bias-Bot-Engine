import json
from app.services.supabase_client import supabase

class DynamicWeightEngine:
    def __init__(self):
        with open('app/config/weights.json') as f:
            self.default_weights = json.load(f)

    def get_weights(self, asset: str, regime: str) -> dict:
        if supabase:
            try:
                result = supabase.table('weight_config').select('weights').eq('asset', asset).eq('regime', regime).execute()
                if result.data:
                    return result.data[0]['weights']
            except Exception:
                pass
        asset_config = self.default_weights.get(asset, {})
        if regime in asset_config:
            return asset_config[regime]
        return self.default_weights.get('default', {'tech': 0.25, 'macro': 0.25, 'sent': 0.25, 'news': 0.25})

    def update_weights(self, asset: str, regime: str, weights: dict):
        if supabase:
            try:
                supabase.table('weight_config').upsert({'asset': asset, 'regime': regime, 'weights': weights}).execute()
            except Exception:
                pass
