import os
import datetime
import numpy as np
import pandas as pd
import yfinance as yf
import requests
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# --- ENVIRONMENT VARIABLES ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GOLDAPI_KEY = os.getenv("GOLDAPI_KEY")  # Fixed variable name mapping

LOOKBACK_DAYS = 180
MIN_REQUIRED_ROWS = 1  # Allows execution on initial DB creation

FOREX_CRYPTO_ASSETS = {
    "btcusd": "BTC-USD",
    "eurusd": "EURUSD=X",
    "gbpusd": "GBPUSD=X"
}

def get_supabase_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("❌ System Environment Error: SUPABASE_URL or SUPABASE_KEY is missing!")
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def sync_spot_gold_and_get_history(supabase: Client) -> pd.DataFrame:
    today_str = datetime.date.today().strftime('%Y-%m-%d')
    
    if not GOLDAPI_KEY:
        print("⚠️ Warning: GOLDAPI_KEY variable is missing. Skipping API request, reading cache directly.")
    else:
        print("📡 Querying Gold API for current Spot Gold price...")
        url = "https://www.goldapi.io/api/XAU/USD"
        headers = {
            "x-access-token": str(GOLDAPI_KEY).strip(), 
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 403:
                print("❌ Gold API rejected key authentication (403 Forbidden). Verify your token on goldapi.io.")
            response.raise_for_status()
            data = response.json()
            
            current_spot_price = float(data.get("price"))
            print(f"✅ Fetched Spot Gold: ${current_spot_price}")
            
            # Persist price entry into Supabase history cache
            supabase.table("gold_history").upsert({
                "date": today_str,
                "close_price": current_spot_price
            }).execute()
            
        except Exception as e:
            print(f"⚠️ Gold API request failed: {e}. Falling back to existing DB history.")

    # Retrieve local history cache for processing indicators
    print("📥 Retrieving historical data cache from Supabase...")
    try:
        response = supabase.table("gold_history")\
            .select("date, close_price")\
            .order("date", desc=False)\
            .limit(LOOKBACK_DAYS)\
            .execute()
        
        records = response.data
        if not records:
            print("❌ No historical gold data found in the Supabase table.")
            return pd.DataFrame()
            
        df = pd.DataFrame(records)
        df['date'] = pd.to_datetime(df['date'])
        df = df.rename(columns={'close_price': 'Close'}).set_index('date')
        return df
    except Exception as e:
        print(f"❌ Error fetching history from Supabase: {e}")
        return pd.DataFrame()

def calculate_bias_metrics(df: pd.DataFrame) -> pd.DataFrame:
    # Safely flatten multi-level column indexes if yfinance returns them
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # Ensure data series contains numeric data points 
    df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
    df = df.dropna(subset=['Close'])

    if len(df) < 20:
        # Fallback tracking if history data pool is still scaling up
        df['sma_20'] = df['Close']
        df['z_score'] = 0.0
    else:
        df['sma_20'] = df['Close'].rolling(window=20).mean()
        df['momentum'] = np.log(df['Close'] / df['Close'].shift(1))
        rolling_mean = df['momentum'].rolling(window=20).mean()
        rolling_std = df['momentum'].rolling(window=20).std()
        df['z_score'] = (df['momentum'] - rolling_mean) / rolling_std.replace(0, np.nan)
    
    df['directional_bias'] = 0
    df.loc[(df['Close'] > df['sma_20']), 'directional_bias'] = 1
    df.loc[(df['Close'] < df['sma_20']), 'directional_bias'] = -1
    return df

def run_macro_engine():
    print(f"🚀 Starting Engine Run: {datetime.date.today()}")
    supabase = get_supabase_client()
    
    # Configure global requests session scraping header values to clear Yahoo anti-bot walls
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    
    # --- 1. SPOT GOLD ---
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
        print(f"❌ Calibration skipped for XAUUSD (Insufficient rows: {len(xau_df)})")

    # --- 2. FOREX & CRYPTO ---
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=LOOKBACK_DAYS)
    
    for asset_name, ticker in FOREX_CRYPTO_ASSETS.items():
        print(f"\n--- Processing Asset: {asset_name.upper()} ---")
        try:
            # Pass custom session structure down directly to avoid Expecting Value 403 blocks
            raw_df = yf.download(ticker, start=start_date, end=end_date, session=session, progress=False)
            
            if raw_df.empty:
                print(f"❌ No price data returned for {asset_name} via yfinance.")
                continue
                
            processed_df = calculate_bias_metrics(raw_df)
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
            print(f"✨ Upserted {asset_name} to database successfully.")
        except Exception as e:
            print(f"❌ Critical failure handling standard asset {asset_name}: {e}")

if __name__ == "__main__":
    run_macro_engine()
