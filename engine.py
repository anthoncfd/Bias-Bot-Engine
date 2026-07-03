import os
import datetime
import numpy as np
import pandas as pd
import yfinance as yf
import requests
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GOLD_API_KEY = os.getenv("GOLD_API_KEY")

LOOKBACK_DAYS = 180
MIN_REQUIRED_ROWS = 30

FOREX_CRYPTO_ASSETS = {
    "btcusd": "BTC-USD",
    "eurusd": "EURUSD=X",
    "gbpusd": "GBPUSD=X"
}

def get_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def sync_spot_gold_and_get_history(supabase: Client) -> pd.DataFrame:
    """
    Consumes exactly 1 GoldAPI credit to fetch today's price, stores it,
    and retrieves history from Supabase to prevent quota exhaustion.
    """
    today_str = datetime.date.today().strftime('%Y-%m-%d')
    
    # 1. Fetch Today's Live Spot Price (1 Request consumed)
    print("📡 Querying Gold API for current Spot Gold price...")
    url = "https://www.goldapi.io/api/XAU/USD"
    headers = {"x-access-token": GOLD_API_KEY, "Content-Type": "application/json"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        current_spot_price = float(data.get("price"))
        print(f"✅ Fetched Spot Gold: ${current_spot_price}")
        
        # 2. Save today's price to your own database
        supabase.table("gold_history").upsert({
            "date": today_str,
            "close_price": current_spot_price
        }).execute()
        
    except Exception as e:
        print(f"⚠️ Gold API request failed or limited: {e}. Falling back to existing DB history.")

    # 3. Read history from your DB to calculate indicators for free
    print("📥 Retrieving historical data cache from Supabase...")
    try:
        response = supabase.table("gold_history")\
            .select("date, close_price")\
            .order("date", desc=False)\
            .limit(LOOKBACK_DAYS)\
            .execute()
        
        records = response.data
        if not records:
            return pd.DataFrame()
            
        df = pd.DataFrame(records)
        df['date'] = pd.to_datetime(df['date'])
        df = df.rename(columns={'close_price': 'Close'}).set_index('date')
        return df
    except Exception as e:
        print(f"❌ Error fetching history from Supabase: {e}")
        return pd.DataFrame()

def calculate_bias_metrics(df: pd.DataFrame) -> pd.DataFrame:
    df['sma_20'] = df['Close'].rolling(window=20).mean()
    df['momentum'] = np.log(df['Close'] / df['Close'].shift(1))
    
    rolling_mean = df['momentum'].rolling(window=20).mean()
    rolling_std = df['momentum'].rolling(window=20).std()
    df['z_score'] = (df['momentum'] - rolling_mean) / rolling_std.replace(0, np.nan)
    
    df['directional_bias'] = 0
    df.loc[(df['Close'] > df['sma_20']) & (df['z_score'] > 0), 'directional_bias'] = 1
    df.loc[(df['Close'] < df['sma_20']) & (df['z_score'] < 0), 'directional_bias'] = -1
    return df

def run_macro_engine():
    print(f"🚀 Starting Engine Run: {datetime.date.today()}")
    supabase = get_supabase_client()
    
    # --- 1. SPOT GOLD (HYBRID FETCH & CACHE) ---
    print("\n--- Processing Asset: XAUUSD (Spot Gold) ---")
    xau_df = sync_spot_gold_and_get_history(supabase)
    
    if not xau_df.empty and len(xau_df) >= MIN_REQUIRED_ROWS:
        processed_xau = calculate_bias_metrics(xau_df)
        latest_row = processed_xau.iloc[-1]
        
        payload = {
            "asset": "xauusd",
            "date": processed_xau.index[-1].strftime('%Y-%m-%d'),
            "close_price": float(latest_row['Close']),
            "sma_20": float(latest_row['sma_20']) if not pd.isna(latest_row['sma_20']) else None,
            "z_score": float(latest_row['z_score']) if not pd.isna(latest_row['z_score']) else None,
            "bias": int(latest_row['directional_bias'])
        }
        supabase.table("macro_biases").upsert(payload).execute()
        print(f"✨ Spot Gold Calculated & Logged. Bias: {int(latest_row['directional_bias'])}")
    else:
        print(f"❌ Calibration skipped for XAUUSD (Need history build-up. Current rows: {len(xau_df)})")

    # --- 2. FOREX & CRYPTO ---
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=LOOKBACK_DAYS)
    
    for asset_name, ticker in FOREX_CRYPTO_ASSETS.items():
        print(f"\n--- Processing Asset: {asset_name.upper()} ---")
        raw_df = yf.download(ticker, start=start_date, end=end_date, progress=False)
        
        if raw_df.empty:
            continue
            
        if isinstance(raw_df.columns, pd.MultiIndex):
            raw_df.columns = raw_df.columns.get_level_values(0)
            
        processed_df = calculate_bias_metrics(raw_df.dropna(subset=['Close']))
        latest_row = processed_df.iloc[-1]
        
        payload = {
            "asset": asset_name,
            "date": processed_df.index[-1].strftime('%Y-%m-%d'),
            "close_price": float(latest_row['Close']),
            "sma_20": float(latest_row['sma_20']) if not pd.isna(latest_row['sma_20']) else None,
            "z_score": float(latest_row['z_score']) if not pd.isna(latest_row['z_score']) else None,
            "bias": int(latest_row['directional_bias'])
        }
        supabase.table("macro_biases").upsert(payload).execute()
        print(f"✨ Upserted {asset_name} to database.")

if __name__ == "__main__":
    run_macro_engine()
