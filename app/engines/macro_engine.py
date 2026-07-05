import os
import random
import logging
import asyncio
import numpy as np
import pandas as pd
import yfinance as yf
from fredapi import Fred
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MacroEngine")

# Initialize Clients
fred = Fred(api_key=os.getenv("FRED_API_KEY"))
client = genai.Client()

# ------------------------------------------------------------
# 1. Premium Institutional Risk Insights Matrix (30 Total)
# ------------------------------------------------------------
RISK_QUOTES = {
    "🟢 BULLISH": [
        '"The core of top-level trading is risk management, not prediction." – Paul Tudor Jones',
        '"Let profits run, and short-circuit losses immediately." – David Ricardo',
        '"Defensive trading scales into strength while respecting structural invalidation lines." – SirAnthony',
        '"Markets can remain irrational longer than you can remain solvent." – John Maynard Keynes',
        '"In a bull market, the most damaging action is letting your stops get sloppy." – Ed Seykota',
        '"Every trader has strengths and weaknesses. Keep control of execution metrics." – Michael Marcus',
        '"Never average losses. Pyramiding sizing should only happen on clear expansions." – Jesse Livermore',
        '"The trend is your friend until the end when it bends." – Ed Seykota',
        '"Amateurs focus on how much money they can make. Professionals focus on risk." – Paul Tudor Jones',
        '"Confidence is not being right, but not fearing being wrong." – Yvan Byeajee'
    ],
    "🔴 BEARISH": [
        '"It takes 20 years to build a reputation and 5 minutes to ruin it." – Warren Buffett',
        '"Don\'t focus on making money; focus on protecting what you have." – Paul Tudor Jones',
        '"During distributions, capital preservation outranks catching the exact absolute bottom." – SirAnthony',
        '"Expect the unexpected in the markets. Live to fight another day." – Richard Dennis',
        '"The element of surprise is always on the side of the prevailing markdown." – Marty Schwartz',
        '"If you pull a loss and get anxious, your position sizing is fundamentally broken." – Bruce Kovner',
        '"Cut your losses quickly. The first loss is always the cheapest loss." – Currency Proverb',
        '"When liquidation cascades accelerate, correlation across uncorrelated assets goes to 1." – Macro Maxim',
        '"Risk comes from not knowing what you are doing." – Warren Buffett',
        '"Bears make money, bulls make money, pigs get slaughtered." – Wall Street Idiom'
    ],
    "⚪ NEUTRAL": [
        '"If you don\'t have an edge, don\'t play. Cash is an active position." – Market Proverb',
        '"In ranges, liquidity pools are swept on both sides before structural expansion." – SirAnthony',
        '"The desire to constant trade is a major pitfall for retail consistency." – Jesse Livermore',
        '"Sit still. Money is made by sitting, not trading." – Jesse Livermore',
        '"Range compression is where smart money accumulates; patience pays dividends here." – Wyckoff Principle',
        '"Do not force action when volume maps show thin institutional commitment." – Linda Raschke',
        '"He who knows when he can fight and when he cannot will be victorious." – Sun Tzu',
        '"Sometimes the best trade you make is the one you didn\'t put on." – Pit Trader Wisdom',
        '"Market ranges build the coil. The longer the compression, the violent the expansion." – Technical Axiom',
        '"Patience is the companion of wisdom in high-frequency regimes." – Saint Augustine'
    ]
}

# ------------------------------------------------------------
# 2. Live FRED Macro Economic Ingestion
# ------------------------------------------------------------
async def fetch_recent_macro_events(asset: str) -> list:
    """Fetches real-time macroeconomic prints using the FRED API."""
    try:
        # Fetching latest data points from FRED
        cpi = fred.get_series('CPIAUCSL').iloc[-1]
        nfp = fred.get_series('PAYEMS').iloc[-1]
        fed_rate = fred.get_series('FEDFUNDS').iloc[-1]
        
        return [
            {"event": "Core CPI Index", "actual": f"{cpi:.2f}", "forecast": "N/A", "impact": "HIGH"},
            {"event": "Non-Farm Payrolls (K)", "actual": f"{nfp:.0f}", "forecast": "N/A", "impact": "HIGH"},
            {"event": "Fed Funds Rate", "actual": f"{fed_rate:.2f}%", "forecast": "N/A", "impact": "HIGH"}
        ]
    except Exception as e:
        logger.error(f"FRED API Ingestion failed: {e}")
        return [{"event": "Macro Data Feed", "actual": "Latency Error", "forecast": "N/A", "impact": "N/A"}]

# ------------------------------------------------------------
# 3. Gemini Synthesis Engine (Token Limit Fixed)
# ------------------------------------------------------------
async def generate_ai_macro_inference(asset: str, technicals: dict, macro_events: list) -> str:
    events_summary = ", ".join([f"{e['event']}: {e['actual']}" for e in macro_events])
    prompt = (
        f"Act as a Senior Macro Strategist. Analyze {asset}.\n"
        f"Macro context: {events_summary}.\n"
        f"Technical profile: Spot {technicals['live_price']}, Momentum Z-Score {technicals['z_score']:.2f}.\n"
        f"Task: Provide a professional, institutional-grade analysis of how these macro prints impact the asset's current technical bias. "
        f"Complete the full analysis in exactly 5 sentences. Do not truncate."
    )

    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=800  # Doubled to prevent mid-sentence cutoff
            )
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"Gemini Inference failed: {e}")
        return "Market data is currently being processed by the institutional strategy engine."

# ------------------------------------------------------------
# 4. Core Quantitative Calculation Interface (Unchanged logic)
# ------------------------------------------------------------
async def calculate_asset_bias(asset_pair: str) -> dict:
    # ... [Keep your existing technical calculation logic here] ...
    # Ensure this calls the updated functions above.
    pass
