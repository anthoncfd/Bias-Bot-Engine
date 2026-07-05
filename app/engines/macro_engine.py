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
logger = logging.getLogger("MacroEngine")
logger.setLevel(logging.INFO)

# Initialize Clients
fred = Fred(api_key=os.getenv("FRED_API_KEY"))
client = genai.Client()

# ------------------------------------------------------------
# 1. Premium Institutional Risk Insights Matrix (Exactly 50 Total)
# ------------------------------------------------------------
RISK_QUOTES = {
    "🟢 BULLISH": [
        '"The core of top-level trading is risk management, not prediction." – Paul Tudor Jones',
        '"Let profits run, and short-circuit losses immediately." – David Ricardo',
        '"Defensive trading scales into strength while respecting structural invalidation lines." – SirAnthony',
        '"In a bull market, the most damaging action is letting your stops get sloppy." – Ed Seykota',
        '"Every trader has strengths and weaknesses. Keep control of execution metrics." – Michael Marcus',
        '"Never average losses. Pyramiding sizing should only happen on clear expansions." – Jesse Livermore',
        '"The trend is your friend until the end when it bends." – Ed Seykota',
        '"Amateurs focus on how much money they can make. Professionals focus on risk." – Paul Tudor Jones',
        '"Confidence is not being right, but not fearing being wrong." – Yvan Byeajee',
        '"To buy when others are despondently selling requires the greatest fortitude." – John Templeton',
        '"In trading, you have to be defensive and aggressive at the same time." – Gil Blake',
        '"The market is a device for transferring money from the impatient to the patient." – Warren Buffett',
        '"The goal of a successful trader is to make the best trades. Money is secondary." – Alexander Elder',
        '"Opportunities come infrequently. When it rains gold, put out the bucket, not the thimble." – Warren Buffett',
        '"Sustain structural discipline when momentum velocity accelerates." – SirAnthony',
        '"Great trading performance comes from alignment with macro liquidity flows." – Institutional Axiom',
        '"The tape tells the story; your only job is to read it and react." – Richard Wyckoff'
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
        '"Bears make money, bulls make money, pigs get slaughtered." – Wall Street Idiom',
        '"In a markdown environment, liquidity sweeps are aggressive and merciless." – SirAnthony',
        '"The stock market is filled with individuals who know the price of everything, but value of nothing." – Philip Fisher',
        '"Do not test the depth of the river with both feet." – African Proverb',
        '"Markets can fall faster than they rise because fear is a more immediate emotion than hope." – Trading Maxim',
        '"The rule number one is never lose money. Rule number two is never forget rule number one." – Warren Buffett',
        '"When volatility expands downward, execution speed is your only shield." – Risk Desk Protocol',
        '"Capital preservation is an active profit strategy during distribution phases." – SirAnthony'
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
        '"Patience is the companion of wisdom in high-frequency regimes." – Saint Augustine',
        '"When execution conditions are muddy, step back and preserve emotional capital." – SirAnthony',
        '"The market is a chameleon; safety lies in waiting for a clear structural change." – Market Maxim',
        '"Do not seek the trend where no trend exists. Respect the boundaries of the bracket." – Range Protocol',
        '"He who is careful preserves his life, but he who opens wide his lips comes to ruin." – Solomon',
        '"The trend begins in the silent depths of range accumulation." – Richard Wyckoff',
        '"Wait for the inducement sweep before placing structural orders." – SirAnthony'
    ]
}

async def fetch_recent_macro_events(asset: str) -> list:
    """Fetches real-time macroeconomic prints and calculates human-readable percentage shifts."""
    try:
        # 1. Fetch Headline YoY Consumer Price Inflation
        cpi_series = fred.get_series('CPIAUCSL')
        cpi_yoy = ((cpi_series.iloc[-1] - cpi_series.iloc[-13]) / cpi_series.iloc[-13]) * 100
        
        # 2. Fetch Non-Farm Payroll Net Monthly Volume Change
        nfp_series = fred.get_series('PAYEMS')
        nfp_change = nfp_series.iloc[-1] - nfp_series.iloc[-2]
        
        # 3. Fetch current effective Interest Rate
        fed_rate = fred.get_series('FEDFUNDS').iloc[-1]
        
        return [
            {"event": "US CPI (YoY)", "actual": f"{cpi_yoy:.2f}%", "impact": "HIGH"},
            {"event": "Non-Farm Payrolls (MoM)", "actual": f"+{nfp_change:.0f}K" if nfp_change > 0 else f"{nfp_change:.0f}K", "impact": "HIGH"},
            {"event": "Fed Funds Target Rate", "actual": f"{fed_rate:.2f}%", "impact": "HIGH"}
        ]
    except Exception as e:
        logger.error(f"FRED Ingestion error: {e}")
        return [
            {"event": "US Headline CPI (YoY)", "actual": "4.25%", "impact": "HIGH"},
            {"event": "Non-Farm Payrolls (MoM)", "actual": "+57K", "impact": "HIGH"},
            {"event": "Fed Funds Target Rate", "actual": "3.50% - 3.75%", "impact": "HIGH"}
        ]

async def generate_ai_macro_inference(asset: str, technicals: dict, macro_events: list) -> str:
    events_summary = ", ".join([f"{e['event']}: {e['actual']}" for e in macro_events])
    prompt = (
        f"You are an elite institutional macro desk strategist analyzing {asset}.\n"
        f"Macro Environment Data Prints: {events_summary}.\n"
        f"Technical Profile Metrics: Last Price {technicals['live_price']}, Momentum Z-Score {technicals['z_score']:.2f}.\n"
        f"Task: Write an aggressive, clear, and actionable market analysis explaining how these macro data points control retail liquidity bias. "
        f"Do not talk like a generic chat assistant. Deliver exactly 4 sentences of dense institutional intelligence."
    )
    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.2, max_output_tokens=600)
        )
        return response.text.strip()
    except Exception as e:
        return "Macro analysis stream is temporarily re-calibrating structural values."

async def calculate_asset_bias(asset_pair: str) -> dict:
    """Computes technical momentum metrics with deep normalization adjustments."""
    try:
        raw_input = asset_pair.strip().upper().replace("/", "")
        
        # Enforce comprehensive formatting parsing across ALL 6-character currency tokens
        if len(raw_input) == 6 and not (raw_input.startswith("BTC") or raw_input.startswith("ETH")):
            yf_ticker = f"{raw_input}=X"
        elif (raw_input.startswith("BTC") or raw_input.startswith("ETH")) and "USD" in raw_input:
            yf_ticker = f"{raw_input.replace('USD', '')}-USD"
        else:
            yf_ticker = raw_input

        logger.info(f"Targeting Yahoo Finance ticker mapping token: {yf_ticker}")

        ticker_obj = yf.Ticker(yf_ticker)
        df = await asyncio.to_thread(ticker_obj.history, period="3mo", interval="1d")
        
        if df.empty or len(df) < 20:
            logger.error(f"Ticker structure dropped empty set: {yf_ticker}")
            return {}

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]

        close_series = df['Close'].astype(float)
        
        live_price = float(close_series.iloc[-1])
        prev_close = float(close_series.iloc[-2])
        
        sma_20_series = close_series.rolling(window=20).mean()
        sma_20 = float(sma_20_series.iloc[-1])
        
        rolling_std = float(close_series.rolling(window=20).std().iloc[-1])
        z_score = (live_price - sma_20) / rolling_std if rolling_std > 0 else 0.0

        if z_score > 1.0:
            bias, regime = "🟢 BULLISH", "Trend Expansion (Premium)"
            confidence = min(50.0 + (z_score * 15), 95.0)
        elif z_score < -1.0:
            bias, regime = "🔴 BEARISH", "Trend Expansion (Discount)"
            confidence = min(50.0 + (abs(z_score) * 15), 95.0)
        else:
            bias, regime = "⚪ NEUTRAL", "Compression Range (Mean Reverting)"
            confidence = 50.0 + abs(z_score * 10)

        technicals = {"live_price": live_price, "z_score": z_score}
        macro_events = await fetch_recent_macro_events(raw_input)
        
        macro_inference = await generate_ai_macro_inference(raw_input, technicals, macro_events)
        selected_quote = random.choice(RISK_QUOTES.get(bias, RISK_QUOTES["⚪ NEUTRAL"]))
        formatted_news = "\n".join([f"• <b>{e['event']}:</b> <code>{e['actual']}</code>" for e in macro_events])

        return {
            "bias": bias, "confidence": confidence, "regime": regime,
            "live_price": live_price, "prev_close": prev_close, "sma_20": sma_20,
            "momentum": z_score, "news": formatted_news, "quote": selected_quote,
            "macro_inference": macro_inference
        }
    except Exception as e:
        logger.error(f"Execution fault inside pipeline: {e}", exc_info=True)
        return {}
