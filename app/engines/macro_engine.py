import os
import logging
import random
import time
import numpy as np
import pandas as pd
import requests
import feedparser
from bs4 import BeautifulSoup

logger = logging.getLogger("macro_engine.core")

def fetch_yahoo_chart_data(asset: str) -> pd.DataFrame:
    """
    Directly targets Yahoo's core V8 chart REST API using automated browser 
    spoofing to bypass the standard library crumb/cookie blockers on Render.
    """
    # Format symbol correctly for FX pairings (e.g., EURUSD=X)
    ticker = f"{asset}=X" if not asset.endswith("=X") else asset
    
    # Calculate timestamps for 60 days of historical data lookback
    end_time = int(time.time())
    start_time = end_time - (60 * 24 * 60 * 60)
    
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    params = {
        "period1": start_time,
        "period2": end_time,
        "interval": "1d",
        "includePrePost": "false",
        "events": "div,splits"
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://finance.yahoo.com",
        "Referer": "https://finance.yahoo.com/",
        "Connection": "keep-alive"
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code != 200:
            logger.error(f"Yahoo API rejected request with HTTP status: {response.status_code}")
            return pd.DataFrame()
            
        data = response.json()
        result = data.get("chart", {}).get("result", [])
        
        if not result:
            logger.error("Yahoo API returned an empty result block matrix.")
            return pd.DataFrame()
            
        # Parse timestamp indices and closing data vectors from raw JSON payload
        timestamps = result[0].get("timestamp", [])
        indicators = result[0].get("indicators", {}).get("quote", [{}])[0]
        closes = indicators.get("close", [])
        
        if not timestamps or not closes:
            return pd.DataFrame()
            
        # Build clean dataframe matching analytical structures
        df = pd.DataFrame({"Close": closes}, index=pd.to_datetime(timestamps, unit="s"))
        # Drop entries missing data points
        df = df.dropna()
        return df
        
    except Exception as e:
        logger.error(f"Failed direct scrap matrix execution from Yahoo Core: {e}")
        return pd.DataFrame()

def get_regime_quote(bias_state: str) -> str:
    """
    Returns a highly relevant trading quote matching the psychological 
    and execution state of the current market regime.
    """
    quotes = {
        "STRONG BULLISH": [
            "\"The trend is your friend until the end when it bends.\" – Ed Seykota",
            "\"Never test the depth of the river with both feet.\" – Warren Buffett",
            "\"Defend your profits fiercely when the macro tide is in your favor.\""
        ],
        "STRONG BEARISH": [
            "\"In a bear market, the game is to lose as little as possible so you're still there at the turn.\" – Paul Tudor Jones",
            "\"Markets fall faster than they rise because fear is a stronger emotion than hope.\"",
            "\"Don't catch falling knives. Wait for structural confirmation.\""
        ],
        "CAUTIOUSLY BULLISH": [
            "\"The core of top-level trading is risk management, not prediction.\" – Paul Tudor Jones",
            "\"Unlikely setups breed catastrophic losses. Wait for the market to prove its hands.\"",
            "\"Range expansions often trap late-stage retail buyers. Stay objective.\""
        ],
        "NEUTRAL": [
            "\"The desire to constant action is one of the greatest hazards on Wall Street.\" – Jesse Livermore",
            "\"If you don't have an edge, don't play. Cash is an active position.\"",
            "\"Compression always precedes expansion. Conserve capital for the breakout.\""
        ]
    }
    
    clean_key = bias_state.replace("🟢 ", "").replace("🔴 ", "").replace("🟡 ", "").replace("⚪ ", "").strip()
    selected_pool = quotes.get(clean_key, quotes["NEUTRAL"])
    return random.choice(selected_pool)

def fetch_macro_news(asset: str) -> str:
    """
    Scrapes the latest macroeconomic headlines related to the asset
    using RSS financial feeds to build a real-time risk profile.
    """
    try:
        feed_url = "https://www.reutersagency.com/feed/?best-topics=economy"
        response = requests.get(feed_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        feed = feedparser.parse(response.content)
        
        keywords = ["fed", "ecb", "inflation", "rate", "usd", "eur", "jpy", "macro"]
        if "EUR" in asset:
            keywords.extend(["euro", "europe", "lagarde"])
        if "JPY" in asset:
            keywords.extend(["yen", "japan", "boj"])
            
        headlines = []
        for entry in feed.entries:
            title_lower = entry.title.lower()
            if any(kw in title_lower for kw in keywords):
                headlines.append(f"• {entry.title}")
                if len(headlines) >= 2:
                    break
                    
        if headlines:
            return "\n".join(headlines)
        return "• No high-impact macro developments reported in the last 4 hours."
    except Exception as e:
        logger.error(f"Error parsing news wire for {asset}: {e}")
        return "• Macro news feed temporarily unavailable."

async def calculate_asset_bias(asset: str) -> dict:
    """
    Advanced calculation layer. Computes spot prices, historical SMAs, 
    Z-score momentum, mathematical confidence levels, and aggregates macro headlines.
    """
    try:
        logger.info(f"Executing advanced analytical matrix pipeline for: {asset}")
        
        # Pull processed dataframe from the direct chart endpoint
        df = fetch_yahoo_chart_data(asset)
        
        if df.empty or len(df) < 22:
            raise ValueError(f"Insufficient historical data depth fetched from core charts for {asset}")

        df['Close'] = df['Close'].astype(float)
        
        live_price = df['Close'].iloc[-1]
        prev_close = df['Close'].iloc[-2]
        
        df['log_return'] = np.log(df['Close'] / df['Close'].shift(1))
        df['sma_20'] = df['Close'].rolling(window=20).mean()
        df['rolling_mean_ret'] = df['log_return'].rolling(window=20).mean()
        df['rolling_std_ret'] = df['log_return'].rolling(window=20).std().replace(0, np.nan)
        
        df['z_score'] = (df['log_return'] - df['rolling_mean_ret']) / df['rolling_std_ret']
        current_z = df['z_score'].fillna(0).iloc[-1]
        current_sma = df['sma_20'].iloc[-1]
        
        z_abs = abs(current_z)
        confidence_raw = 50.0 + (z_abs * 22.5)  
        confidence_level = min(max(confidence_raw, 50.0), 99.1)
        
        is_above_sma = live_price > current_sma
        
        if is_above_sma and current_z > 0.5:
            bias_state = "🟢 STRONG BULLISH"
            regime_state = "Expansion Trend (Aggressive Buying)"
        elif not is_above_sma and current_z < -0.5:
            bias_state = "🔴 STRONG BEARISH"
            regime_state = "Distribution Shift (Heavy Liquidations)"
        elif is_above_sma and current_z <= 0.5:
            bias_state = "🟡 CAUTIOUSLY BULLISH"
            regime_state = "Mean Reversion / Trend Exhaustion"
        else:
            bias_state = "⚪ NEUTRAL"
            regime_state = "Compression Range (Liquidity Building)"

        macro_news_feed = fetch_macro_news(asset)
        trading_quote = get_regime_quote(bias_state)

        return {
            "live_price": f"{live_price:.5f}",
            "prev_close": f"{prev_close:.5f}",
            "sma_20": f"{current_sma:.5f}",
            "bias": bias_state,
            "momentum": f"{'+' if current_z >= 0 else ''}{current_z:.2f}",
            "confidence": f"{confidence_level:.1f}%",
            "regime": regime_state,
            "news": macro_news_feed,
            "quote": trading_quote
        }
        
    except Exception as e:
        logger.error(f"Execution matrix failed: {e}")
        return {
            "live_price": "0.0000", "prev_close": "0.0000", "sma_20": "0.0000",
            "bias": "ERROR", "momentum": "0.00", "confidence": "0.0%",
            "regime": "Fault Loop Intercepted", "news": "• Error scraping live wires.",
            "quote": "\"In trading, the market tells you what to do, not vice versa.\""
        }
