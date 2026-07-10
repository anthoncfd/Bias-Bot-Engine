import httpx
import os
from typing import Dict, Any
from app.logger import logger
from app.config import settings

class MarketIntelligenceEngine:
    """The central decision-making engine. Combines all sub-scores mathematically 
    before calling Gemini to generate an institutional-grade explanation report.
    """
    
    def __init__(self, http_client: httpx.AsyncClient):
        self.client = http_client
        self.api_key = os.getenv("GEMINI_API_KEY") or getattr(settings, "supabase_key", "") or getattr(settings, "market_api_key", "")
        self.gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"

    @staticmethod
    def calculate_composite_matrix(tech_score_pct: float, macro: float, sent: float, news: float, 
                                      net_change: float, asset_class: str, is_noise: bool) -> Dict[str, Any]:
        """Runs your mathematical calculations before AI is involved to prevent model hallucinations."""
        # Weighted matrix distribution layer: Tech (40%), Macro (30%), Sentiment (15%), News (15%)
        composite = (tech_score_pct * 0.40) + (macro * 0.30) + (sent * 0.15) + (news * 0.15)
        
        normalized_comp = (composite + 100.0) / 2.0
        prob_up = max(0.0, min(100.0, normalized_comp))
        prob_down = 100.0 - prob_up
        
        confidence = abs(composite)
        barrier = 15.0 if asset_class == "FOREX" else 30.0

        # ━━━━ 🏛️ CLASSIC VOLATILITY-NORMALIZED BIAS ROUTER ━━━━
        if tech_score_pct > barrier:
            if is_noise:
                bias_state = "BULLISH_CONSOLIDATION"
                display_text = "🟢 STRUCTURAL BULLISH (INTRADAY CONSOLIDATION)"
                icon = "📈"
            elif net_change > 0:
                bias_state = "STRONGLY_BULLISH"
                display_text = "🟢 STRONGLY BULLISH BIAS"
                icon = "🚀"
            else:
                bias_state = "BULLISH_RETRACEMENT"
                display_text = "🟡 BULLISH RETRACEMENT (DIP BUYING ZONE)"
                icon = "⚡"
                
        elif tech_score_pct < -barrier:
            if is_noise:
                bias_state = "BEARISH_CONSOLIDATION"
                display_text = "🔴 STRUCTURAL BEARISH (INTRADAY CONSOLIDATION)"
                icon = "📉"
            elif net_change < 0:
                bias_state = "STRONGLY_BEARISH"
                display_text = "🔴 STRONGLY BEARISH BIAS"
                icon = "💥"
            else:
                bias_state = "BEARISH_RECOVERY"
                display_text = "🟡 BEARISH RECOVERY (RALLY SELLING ZONE)"
                icon = "⚡"
        else:
            bias_state = "NEUTRAL"
            display_text = "⚪ NEUTRAL MEAN REVERSION BLOCK"
            icon = "⚖️"
        
        return {
            "composite_score": composite,
            "prob_up": prob_up,
            "prob_down": prob_down,
            "confidence_level": confidence,
            "market_bias": bias_state,
            "bias_display": display_text,
            "bias_icon": icon
        }

    async def generate_institutional_briefing(self, symbol: str, matrix: dict, tech_score: float) -> str:
        """Passes the finalized mathematical output to Gemini to generate a professional executive briefing."""
        prompt = (
            f"You are a Senior Macro Portfolio Manager. Review these computed matrix metrics for the financial asset {symbol}:\n"
            f"- Multi-Factor Composite Score: {matrix['composite_score']:.2f}%\n"
            f"- Technical Vector Weight: {tech_score:.2f}%\n"
            f"- Evaluated Bullish Directional Probability: {matrix['prob_up']:.1f}%\n"
            f"- Calculated Core Bias State: {matrix['bias_display']}\n\n"
            f"Generate a professional, high-density 3-sentence summary analyzing this systemic macro alignment. "
            f"Keep your tone analytical and concise, and begin directly with the data analysis."
        )
        try:
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            res = await self.client.post(self.gemini_url, json=payload, timeout=12.0)
            if res.status_code == 200:
                return res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            else:
                logger.error(f"⚠️ Gemini API briefing rejection: Status {res.status_code}")
        except Exception as err:
            logger.error(f"Gemini executive generation unexpected failure: {err}")
            
        return "System matrix metrics are active, but the generative commentary layer timed out. Please evaluate raw metrics percentages above."
