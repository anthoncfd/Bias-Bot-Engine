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
        
        # 🔐 RESILIENT ATTRIBUTE FALLBACK: Safely extracts configuration properties without crash trace risk
        api_key = getattr(settings, "gemini_api_key", None) or os.getenv("GEMINI_API_KEY") or getattr(settings, "supabase_key", "")
        
        self.gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"

    @staticmethod
    def calculate_composite_matrix(tech: float, macro: float, sent: float, news: float) -> Dict[str, Any]:
        """Runs your mathematical calculations before AI is involved to prevent model hallucinations."""
        composite = (tech * 0.40) + (macro * 0.30) + (sent * 0.15) + (news * 0.15)
        
        normalized_comp = (composite + 100.0) / 2.0
        prob_up = max(0.0, min(100.0, normalized_comp))
        prob_down = 100.0 - prob_up
        
        confidence = abs(composite)
        
        bias = "STRONG_BULLISH" if composite > 40.0 else "STRONG_BEARISH" if composite < -40.0 else "BULLISH" if composite > 15.0 else "BEARISH" if composite < -15.0 else "NEUTRAL"
        
        return {
            "composite_score": composite, "prob_up": prob_up, "prob_down": prob_down,
            "confidence_level": confidence, "market_bias": bias
        }

    async def generate_institutional_briefing(self, symbol: str, matrix: dict, tech_score: float) -> str:
        """Passes the finalized mathematical output to Gemini to generate a professional executive briefing."""
        prompt = (
            f"You are a Senior Macro Portfolio Manager. Review these computed matrix metrics for the financial asset {symbol}:\n"
            f"- Multi-Factor Composite Score: {matrix['composite_score']:.2f}%\n"
            f"- Technical Vector Weight: {tech_score:.2f}%\n"
            f"- Evaluated Bullish Directional Probability: {matrix['prob_up']:.1f}%\n"
            f"- Calculated Core Bias State: {matrix['market_bias']}\n\n"
            f"Generate a professional, high-density 3-sentence summary analyzing this systemic macro alignment. "
            f"Keep your tone analytical and concise, and begin directly with the data analysis."
        )
        try:
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            res = await self.client.post(self.gemini_url, json=payload, timeout=12.0)
            if res.status_code == 200:
                return res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as err:
            logger.error(f"Gemini executive generation failure: {err}")
        return "System matrix metrics are active, but the generative commentary layer timed out. Please evaluate raw metrics percentages above."
