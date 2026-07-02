import os
from dotenv import load_dotenv
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
FRED_API_KEY = os.getenv("FRED_API_KEY")

# Gemini API Integration (Free Tier)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# GoldAPI.io key – required for XAUUSD and XAGUSD
GOLDAPI_KEY = os.getenv("GOLDAPI_KEY")

# Yahoo Finance symbols map
ASSET_MAP = {
    "xauusd": "XAUUSD=X",
    "xagusd": "XAGUSD=X",
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
