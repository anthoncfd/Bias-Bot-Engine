import os
import random
import logging
import asyncio
import time
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
# 1. Premium Institutional Risk Insights Matrix
# ------------------------------------------------------------
RISK_QUOTES = {
    "🟢 BULLISH": [
        '"The core of top-level trading is risk management, not prediction." – Paul Tudor Jones',
        '"Let profits run, and short-circuit losses immediately." – David Ricardo',
        '"Defensive trading scales into strength while respecting structural invalidation lines." – SirAnthony',
        '"Markets can remain irrational longer than you can remain solvent." – John Maynard Keynes',
        '"In a bull market, the most damaging action is letting your stops get sloppy." – Ed Seykota',
    ],
    "🔴 BEARISH": [
        '"It takes 20 years to build a reputation and 5 minutes to ruin it." – Warren Buffett',
        '"Don\'t focus on making money; focus on protecting what you have." – Paul Tudor Jones',
        '"During distributions, capital preservation outranks catching the exact absolute bottom." – SirAnthony',
        '"Expect the unexpected in the markets. Live to fight another day." – Richard Dennis',
        '"Cut your losses quickly. The first loss is always the cheapest loss." – Currency Proverb',
    ],
    "⚪ NEUTRAL": [
        '"If you don\'t have an edge, don\'t play. Cash is an active position." – Market Proverb',
        '"In ranges, liquidity pools are swept on both sides before structural expansion." – SirAnthony',
        '"The desire to constant trade is a major pitfall for retail consistency." – Jesse Livermore',
        '"Sit still. Money is made by sitting, not trading." – Jesse Livermore',
        '"Range compression is where smart money accumulates; patience pays dividends here." – Wyckoff Principle',
    ]
}

# ------------------------------------------------------------
# 2. Unified Asset Ticker Mapping (from config)
# ------------------------------------------------------------
# We'll import from config, but also provide a fallback dict
try:
    from app.config import ASSET_MAP
except ImportError:
    # Fallback mapping if config not accessible
    ASSET_MAP = {
        "eurusd": "EURUSD=X",
        "gbpusd": "GBPUSD=X",
        "audusd": "AUDUSD=X",
        "gbpjpy": "GBPJPY=X",
        "eurjpy": "EURJPY=X",
        "usdchf": "USDCHF=X",
        "usdcad": "USDCAD=X",
        "cadchf": "CADCHF=X",
        "us30": "^DJI",
        "jp225": "^N225",
        "btcusd": "BTC-USD",
        "ethusd": "ETH-USD",
        "bnbusd": "BNB-USD"
    }

# ------------------------------------------------------------
# 3. Robust yfinance fetcher with retries
# ------------------------------------------------------------
async def fetch_yf_data(ticker: str, period="3mo", retries=3) -> pd.DataFrame:
    """
    Fetch OHLC data from Yahoo Finance with retry logic.
    Returns empty DataFrame if all attempts fail.
    """
    for attempt in range(retries):
        try:
            df = await asyncio.to_thread(
                yf.download,
                ticker,
                period=period,
                interval="1d",
                progress=False,
                timeout=10
            )
            if not df.empty:
                return df
            logger.warning(f"Attempt {attempt+1} for {ticker} returned empty, retrying...")
            await asyncio.sleep(2 ** attempt)  # exponential backoff
        except Exception as e:
            logger.warning(f"Attempt {attempt+1} for {ticker} failed: {e}")
            await asyncio.sleep(2 ** attempt)
    return pd.DataFrame()

# ------------------------------------------------------------
# 4. FRED Macro Data Ingestion
# ------------------------------------------------------------
async def fetch_recent_macro_events(asset: str) -> list:
    try:
        cpi = fred.get_series('CPIAUCSL').iloc[-1]
        nfp = fred.get_series('PAYEMS').iloc[-1]
        fed_rate = fred.get_series('FEDFUNDS').iloc[-1]
        return [
            {"event": "Core CPI Index", "actual": f"{cpi:.2f}", "impact": "HIGH"},
            {"event": "Non-Farm Payrolls (K)", "actual": f"{nfp:.0f}", "impact": "HIGH"},
            {"event": "Fed Funds Rate", "actual": f"{fed_rate:.2f}%", "impact": "HIGH"}
        ]
    except Exception as e:
        logger.error(f"FRED API failed: {e}")
        return [{"event": "Macro Data Feed", "actual": "Latency Error", "impact": "N/A"}]

# ------------------------------------------------------------
# 5. Gemini AI Synthesis
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
            config=types.GenerateContentConfig(temperature=0.3, max_output_tokens=800)
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"Gemini failed: {e}")
        return "Market data is currently being processed by the institutional strategy engine."

# ------------------------------------------------------------
# 6. Core Quantitative Calculation (Fixed)
# ------------------------------------------------------------
async def calculate_asset_bias(asset_pair: str) -> dict:
    """
    Computes technicals, fetches macro data, and generates a full report.
    NEVER returns an empty dict – always returns a dict with at least a 'bias' key.
    """
    # Clean asset name
    raw_input = asset_pair.strip().upper().replace("/", "")
    logger.info(f"Initiating pipeline for: {raw_input}")

    # ---- Get correct Yahoo ticker from ASSET_MAP ----
    yf_ticker = ASSET_MAP.get(raw_input.lower())
    if not yf_ticker:
        # Fallback: try to infer (forex or crypto)
        if "USD" in raw_input:
            if raw_input.startswith(("BTC", "ETH", "BNB")):
                base = raw_input.replace("USD", "")
                yf_ticker = f"{base}-USD"
            else:
                yf_ticker = f"{raw_input}=X"
        else:
            yf_ticker = raw_input  # e.g., "^DJI" if directly provided
        logger.warning(f"Asset {raw_input} not in ASSET_MAP, using inferred ticker: {yf_ticker}")

    logger.info(f"Using Yahoo ticker: {yf_ticker}")

    # ---- Fetch data ----
    df = await fetch_yf_data(yf_ticker, period="3mo")

    # If still empty, try alternative fallback tickers
    if df.empty:
        # For crypto, try USDT pair as a last resort
        if raw_input.startswith(("BTC", "ETH", "BNB")):
            alt_ticker = raw_input + "USDT"
            logger.warning(f"Retrying with {alt_ticker}")
            df = await fetch_yf_data(alt_ticker, period="3mo")
        # For indices, fallback to Yahoo's default symbol
        elif raw_input.startswith(("US30", "JP225")):
            alt_map = {"US30": "^DJI", "JP225": "^N225"}
            if raw_input in alt_map:
                df = await fetch_yf_data(alt_map[raw_input], period="3mo")

    # ---- If still no data, return a dict with error info ----
    if df.empty or len(df) < 20:
        logger.error(f"❌ No data for {raw_input} (ticker: {yf_ticker})")
        return {
            "bias": "⚪ NEUTRAL",
            "confidence": 0.0,
            "regime": "Data Unavailable",
            "live_price": 0.0,
            "prev_close": 0.0,
            "sma_20": 0.0,
            "momentum": 0.0,
            "news": "• No price data found. Check ticker mapping or network.",
            "quote": "\"The market is always right.\"",
            "macro_inference": "Unable to compute inference due to missing data."
        }

    # ---- Calculate technicals ----
    df['Close'] = df['Close'].astype(float)
    live_price = float(df['Close'].iloc[-1])
    prev_close = float(df['Close'].iloc[-2]) if len(df) > 1 else live_price

    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    sma_20 = float(df['SMA_20'].iloc[-1]) if not pd.isna(df['SMA_20'].iloc[-1]) else live_price

    rolling_std = df['Close'].rolling(window=20).std().iloc[-1]
    z_score = (live_price - sma_20) / rolling_std if rolling_std and rolling_std > 0 else 0.0

    # ---- Determine bias ----
    if z_score > 1.0:
        bias = "🟢 BULLISH"
        regime = "Trend Expansion (Premium)"
        confidence = min(50.0 + (z_score * 15), 95.0)
    elif z_score < -1.0:
        bias = "🔴 BEARISH"
        regime = "Trend Expansion (Discount)"
        confidence = min(50.0 + (abs(z_score) * 15), 95.0)
    else:
        bias = "⚪ NEUTRAL"
        regime = "Compression Range (Mean Reverting)"
        confidence = 50.0 + abs(z_score * 10)

    technicals = {
        "live_price": live_price,
        "prev_close": prev_close,
        "sma_20": sma_20,
        "z_score": z_score
    }

    # ---- Fetch macro and AI ----
    macro_events = await fetch_recent_macro_events(raw_input)
    ai_inference = await generate_ai_macro_inference(raw_input, technicals, macro_events)
    selected_quote = random.choice(RISK_QUOTES.get(bias, RISK_QUOTES["⚪ NEUTRAL"]))

    # Format news
    news_lines = [f"• <b>{e['event']}:</b> <code>{e['actual']}</code> (Impact: {e['impact']})" for e in macro_events]
    formatted_news = "\n".join(news_lines)

    # ---- Build final payload (always returns a dict) ----
    return {
        "bias": bias,
        "confidence": confidence,
        "regime": regime,
        "live_price": live_price,
        "prev_close": prev_close,
        "sma_20": sma_20,
        "momentum": z_score,
        "news": formatted_news,
        "quote": selected_quote,
        "macro_inference": ai_inference
    }
