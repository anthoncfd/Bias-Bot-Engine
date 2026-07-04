import os
import logging
import random
import time
import numpy as np
import pandas as pd
import requests
import feedparser
from datetime import datetime, timezone
from app.models import MacroData

logger = logging.getLogger(__name__)

# ------------------------------------------------------------
# Yahoo V8 API – direct, no yfinance
# ------------------------------------------------------------
def fetch_yahoo_v8(symbol: str, days: int = 60) -> pd.DataFrame:
    """
    Fetch OHLC data from Yahoo's V8 chart API.
    Returns DataFrame with 'Close' (and optionally Open, High, Low, Volume).
    """
    if symbol.endswith("=X"):
        ticker = symbol.upper()
    else:
        ticker = f"{symbol.upper()}=X"

    end_time = int(time.time())
    start_time = end_time - (days * 24 * 60 * 60)

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
            logger.error(f"Yahoo V8 API returned {response.status_code} for {ticker}")
            return pd.DataFrame()

        data = response.json()
        result = data.get("chart", {}).get("result", [])
        if not result:
            return pd.DataFrame()

        timestamps = result[0].get("timestamp", [])
        quote = result[0].get("indicators", {}).get("quote", [{}])[0]
        closes = quote.get("close", [])
        opens = quote.get("open", [])
        highs = quote.get("high", [])
        lows = quote.get("low", [])
        volumes = quote.get("volume", [])

        if not timestamps or not closes:
            return pd.DataFrame()

        df = pd.DataFrame({
            "Close": closes,
            "Open": opens,
            "High": highs,
            "Low": lows,
            "Volume": volumes
        }, index=pd.to_datetime(timestamps, unit="s"))

        df = df.dropna()
        return df

    except Exception as e:
        logger.error(f"Yahoo V8 fetch error for {ticker}: {e}")
        return pd.DataFrame()

# ------------------------------------------------------------
# Macro News (Reuters RSS)
# ------------------------------------------------------------
def fetch_macro_news(asset: str) -> str:
    try:
        feed_url = "https://www.reutersagency.com/feed/?best-topics=economy"
        response = requests.get(feed_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        feed = feedparser.parse(response.content)

        keywords = ["fed", "ecb", "inflation", "rate", "usd", "eur", "jpy", "macro"]
        asset_upper = asset.upper()
        if "EUR" in asset_upper: keywords.extend(["euro", "europe", "lagarde"])
        if "JPY" in asset_upper: keywords.extend(["yen", "japan", "boj"])
        if "GBP" in asset_upper: keywords.extend(["pound", "boe", "uk"])
        if "AUD" in asset_upper: keywords.extend(["aussie", "rba"])

        headlines = []
        for entry in feed.entries[:10]:
            title_lower = entry.title.lower()
            if any(kw in title_lower for kw in keywords):
                headlines.append(f"• {entry.title}")
                if len(headlines) >= 2:
                    break

        if headlines:
            return "\n".join(headlines)
        return "• No high-impact macro developments reported in the last 4 hours."
    except Exception as e:
        logger.error(f"News fetch error: {e}")
        return "• Macro news feed temporarily unavailable."

# ------------------------------------------------------------
# Regime Quote
# ------------------------------------------------------------
def get_regime_quote(bias_state: str) -> str:
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

# ------------------------------------------------------------
# Main MacroEngine – now uses V8 API, no yfinance/fredapi
# ------------------------------------------------------------
class MacroEngine:
    def __init__(self):
        self._extra = {}

    def fetch(self) -> tuple[MacroData, dict, dict]:
        """
        Returns:
          - MacroData: DXY, US10Y, US2Y, fed_funds, cpi_yoy, payrolls, pmi (all from V8)
          - timestamps: dict with when each was fetched
          - extra: dict with 'bias', 'confidence', 'regime', 'news', 'quote'
        """
        dxy_df = fetch_yahoo_v8("DX-Y.NYB", days=5)
        us10y_df = fetch_yahoo_v8("^TNX", days=5)
        us2y_df = fetch_yahoo_v8("^FVX", days=5)

        dxy = float(dxy_df['Close'].iloc[-1]) if not dxy_df.empty else 102.0
        us10y = float(us10y_df['Close'].iloc[-1]) if not us10y_df.empty else 4.2
        us2y = float(us2y_df['Close'].iloc[-1]) if not us2y_df.empty else 4.5

        # Placeholder values – can be replaced with FRED later
        fed_funds = 5.25
        cpi_yoy = 3.0
        payrolls = 180.0
        pmi = 49.5

        macro = MacroData(
            dxy=dxy, us10y=us10y, us2y=us2y,
            fed_funds=fed_funds, cpi_yoy=cpi_yoy,
            payrolls=payrolls, pmi=pmi
        )

        now = datetime.now(timezone.utc)
        timestamps = {'dxy': now, 'us10y': now, 'fred_fed': now, 'fred_cpi': now}
        return macro, timestamps, {}

    def score(self, macro: MacroData, asset: str, surprises: dict = None) -> float:
        """
        Compute a numeric macro score (-1..1) based on the asset.
        Also computes bias, news, quote and stores them in self._extra.
        """
        df = fetch_yahoo_v8(asset, days=60)
        if df.empty or len(df) < 22:
            score = 0.0
            score += (101.5 - macro.dxy) / 4.0 * 0.3
            score += (4.0 - macro.us10y) / 1.5 * 0.2
            score += (2.5 - macro.cpi_yoy) / 1.5 * 0.2
            score += (4.25 - macro.fed_funds) / 1.5 * 0.2
            score += (macro.pmi - 50.0) / 7.0 * 0.1
            self._extra = {
                "bias": "⚪ NEUTRAL",
                "regime": "Fault Loop Intercepted (Fallback Framework)",
                "confidence": 50.0,
                "news": "• Advanced scraping frames dropped to fallback channels.",
                "quote": "\"In trading, the market tells you what to do, not vice versa.\"",
                "live_price": 0.0, "sma_20": 0.0, "z_score": 0.0, "prev_close": 0.0
            }
            return float(np.clip(score, -1, 1))

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

        is_above_sma = live_price > current_sma

        if is_above_sma and current_z > 0.5:
            bias_state = "🟢 STRONG BULLISH"
            regime_state = "Expansion Trend (Aggressive Buying)"
            macro_bias_score = 0.8
        elif not is_above_sma and current_z < -0.5:
            bias_state = "🔴 STRONG BEARISH"
            regime_state = "Distribution Shift (Heavy Liquidations)"
            macro_bias_score = -0.8
        elif is_above_sma and current_z <= 0.5:
            bias_state = "🟡 CAUTIOUSLY BULLISH"
            regime_state = "Mean Reversion / Trend Exhaustion"
            macro_bias_score = 0.3
        else:
            bias_state = "⚪ NEUTRAL"
            regime_state = "Compression Range (Liquidity Building)"
            macro_bias_score = 0.0

        z_abs = abs(current_z)
        confidence_raw = 50.0 + (z_abs * 22.5)
        confidence_level = min(max(confidence_raw, 50.0), 99.1)

        macro_news = fetch_macro_news(asset)
        trading_quote = get_regime_quote(bias_state)

        self._extra = {
            "bias": bias_state, "regime": regime_state, "confidence": confidence_level,
            "news": macro_news, "quote": trading_quote, "live_price": live_price,
            "sma_20": current_sma, "z_score": current_z, "prev_close": prev_close
        }

        dxy_score = (101.5 - macro.dxy) / 4.0
        us10y_score = (4.0 - macro.us10y) / 1.5
        cpi_score = (2.5 - macro.cpi_yoy) / 1.5
        fed_score = (4.25 - macro.fed_funds) / 1.5
        pmi_score = (macro.pmi - 50.0) / 7.0

        traditional = 0.3 * dxy_score + 0.2 * us10y_score + 0.2 * cpi_score + 0.2 * fed_score + 0.1 * pmi_score
        blended = 0.6 * traditional + 0.4 * macro_bias_score
        return float(np.clip(blended, -1, 1))

    def get_extra(self):
        """Return the extra info computed during the last score() call."""
        return getattr(self, '_extra', {})

# ------------------------------------------------------------
# Backward-Compatibility Bridge for Legacy Services
# ------------------------------------------------------------
async def calculate_asset_bias(asset: str) -> dict:
    """
    Acts as a routing bridge for legacy instances (like app/services/telegram_bot.py)
    that look to import calculate_asset_bias as a module-level function.
    """
    engine = MacroEngine()
    # Mock fallback baseline macro container
    mock_macro = MacroData(
        dxy=102.0, us10y=4.2, us2y=4.5, 
        fed_funds=5.25, cpi_yoy=3.0, payrolls=180.0, pmi=49.5
    )
    # Run historical evaluations and populate extra maps
    engine.score(mock_macro, asset)
    return engine.get_extra()
