import os
from dotenv import load_dotenv

load_dotenv()

# Fixed to use your exact environment variable setup
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
FRED_API_KEY = os.getenv("FRED_API_KEY")

# AI / Alternative Data Integrations
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GOLDAPI_KEY = os.getenv("GOLDAPI_KEY")

# Supported Core Asset Universe Matrix
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
