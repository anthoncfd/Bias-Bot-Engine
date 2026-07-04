from app.models import AggregatedScores, MacroData, SentimentData

class ExplanationEngine:
    @staticmethod
    def generate(asset: str, price: float, scores: AggregatedScores,
                 prob: float, conf: float, regime: str,
                 macro: MacroData, sent: SentimentData, correlation: float = 0.0,
                 tech_indicators=None, news_items=None, source_reliabilities=None,
                 proxy_used=False, macro_timestamp=None, news_timestamp=None, sent_timestamp=None,
                 model_version='unknown', sample_size=0,
                 macro_extra=None) -> str:

        direction = "BULLISH" if scores.composite > 0.05 else "BEARISH" if scores.composite < -0.05 else "NEUTRAL"
        asset_label = asset.upper()
        
        # Determine symbol padding based on type (FX vs standard asset handles)
        is_fx = any(x in asset_label for x in ["EUR", "USD", "JPY", "GBP", "AUD", "CAD", "CHF"])
        unit_prefix = "" if is_fx else "$"

        audit = ""
        if tech_indicators:
            audit += f"• Technical Matrix: {scores.tech_score:+.2f}\n"
            audit += f"  - SMA20 Vector: {unit_prefix}{tech_indicators.sma20:.4f if is_fx else '.2f'}\n"
            audit += f"  - Volatility-Adjusted Z-Score: {tech_indicators.z_score:+.2f}\n"
            audit += f"  - High-Velocity Momentum: {tech_indicators.momentum:+.2f}%\n"
        if scores.macro_score != 0:
            audit += f"• Macro Engine: {scores.macro_score:+.2f}\n"
            audit += f"  - DXY Index Close: {macro.dxy:.2f}\n"
            audit += f"  - Yield Curve US10Y: {macro.us10y:.2f}%\n"
            audit += f"  - Structural Inflation Rate: {macro.cpi_yoy:.1f}%\n"
        if scores.sent_score != 0:
            audit += f"• Sentiment Index: {scores.sent_score:+.2f}\n"
            audit += f"  - VIX Baseline: {sent.vix:.1f}\n"
            audit += f"  - Fear & Greed Parse Value: {sent.fear_greed:.0f}\n"
        if scores.news_score != 0 and news_items:
            audit += f"• Natural Language Core: {scores.news_score:+.2f}\n"
            for item in news_items[:2]:
                audit += f"  - [{item.source.upper()}] {item.headline[:45]}... (Dir: {item.direction})\n"

        timestamps = ""
        if macro_timestamp:
            timestamps += f"• Macro Data: {macro_timestamp.strftime('%H:%M UTC')}\n"
        if proxy_used:
            timestamps += "⚠️ *Structural warning: Active network data proxy operational.*\n"

        reliability_text = "Source Confidence Weightings:\n"
        if source_reliabilities:
            for src, rel in source_reliabilities.items():
                reliability_text += f"  • {src}: {rel*100:.0f}%\n"

        macro_extra_text = ""
        if macro_extra:
            raw_conf = macro_extra.get('confidence', 50.0)
            conf_val = float(raw_conf) if raw_conf is not None else 50.0
            macro_extra_text += (
                f"\n💡 *Macro Bias Summary:* `{macro_extra.get('bias', 'N/A')}`\n"
                f"🎯 *Macro Confidence level:* `{conf_val:.1f}%`\n"
                f"🔄 *Macro Market Regime:* `{macro_extra.get('regime', 'N/A')}`\n\n"
                f"📰 *High-Impact Macro Wire:*\n{macro_extra.get('news', 'No high-impact macro headlines reported.')}\n\n"
                f"🧠 _**RISK INSIGHT:**_\n"
                f"_{macro_extra.get('quote', '')}_\n"
            )

        return (
            f"📊 *{asset_label} Institutional Analysis Engine V4.3*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"💵 *Spot Price:* {unit_prefix}{price:.4f if is_fx else '.2f'}\n"
            f"📈 *Directional Alpha Bias:* {direction}\n"
            f"🎯 *Bullish Convergence Prob:* {prob:.1f}%\n"
            f"🔒 *Calibrated Statistical Confidence:* {conf:.0f}%\n"
            f"🌊 *Active Market Regime:* {regime}\n"
            f"📊 *Intermarket Correlation Vector:* {correlation:+.2f}\n"
            f"🧠 *Engine Node:* {model_version} ({sample_size} arrays)\n\n"
            f"📉 *Factor Weight Score Decomposition:*\n"
            f"• Technical Factor: {scores.tech_score:+.2f}\n"
            f"• Macroeconomic Factor: {scores.macro_score:+.2f}\n"
            f"• Sentiment Matrix: {scores.sent_score:+.2f}\n"
            f"• LLM Sentiment Vector: {scores.news_score:+.2f}\n"
            f"• Composite Processing Score: {scores.composite:+.2f}\n\n"
            f"🔍 *System Factor Audit Trail:*\n{audit}\n"
            f"⏱️ *Data Layer Integrity Verification:*\n{timestamps}\n"
            f"{reliability_text}"
            f"{macro_extra_text}\n"
            f"⚡ *Data Nodes:* Yahoo Finance / FRED / Gemini API\n"
            f"🛡️ *Engineered for High-Conviction Execution*"
        )
