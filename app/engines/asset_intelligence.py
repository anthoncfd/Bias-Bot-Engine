from app.engines.dynamic_weights import DynamicWeightEngine
from app.models import AggregatedScores

class AssetIntelligenceEngine:
    def __init__(self):
        self.weight_engine = DynamicWeightEngine()

    def combine(self, asset: str, tech: float, macro: float, sent: float, news: float, regime: str) -> AggregatedScores:
        weights = self.weight_engine.get_weights(asset, regime)
        composite = (
            tech * weights.get("tech", 0.25) +
            macro * weights.get("macro", 0.25) +
            sent * weights.get("sent", 0.25) +
            news * weights.get("news", 0.25)
        )
        return AggregatedScores(
            tech_score=tech,
            macro_score=macro,
            sent_score=sent,
            news_score=news,
            composite=float(composite)
        )
