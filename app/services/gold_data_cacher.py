import requests
from datetime import datetime, timedelta
import time
import logging
from supabase import create_client, Client
from app.config import SUPABASE_URL, SUPABASE_KEY, GOLDAPI_KEY

logger = logging.getLogger(__name__)

TABLE = "precious_metals_daily"
MAX_RETRIES = 3
METALS = ["XAU", "XAG"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

def fetch_metal_for_date(metal: str, date_str: str, retries=0):
    if not GOLDAPI_KEY:
        return None
    try:
        url = f"https://www.goldapi.io/api/{metal}/USD/{date_str}"
        headers = {"x-access-token": GOLDAPI_KEY}
        resp = requests.get(url, headers=headers, timeout=15)
        
        if resp.status_code == 200:
            data = resp.json()
            return {
                "date": date_str,
                "metal": metal,
                "price": data.get("price"),
                "open_price": data.get("open_price"),
                "high_price": data.get("high_price"),
                "low_price": data.get("low_price"),
                "prev_close": data.get("prev_close_price"),
                "timestamp": data.get("timestamp")
            }
        elif resp.status_code == 429:
            time.sleep(60)
            if retries < MAX_RETRIES:
                return fetch_metal_for_date(metal, date_str, retries + 1)
        else:
            logger.error(f"Upstream provider error code {resp.status_code} mapped for {metal} targeting timestamp {date_str}")
    except Exception as e:
        logger.exception(f"Unhandled metadata mapping layer exception for token parameter {metal} on {date_str}: {e}")
    return None

def get_existing_dates():
    if not supabase:
        return set()
    try:
        response = supabase.table(TABLE).select("date, metal").execute()
        return {(row["date"], row["metal"]) for row in response.data}
    except Exception as e:
        logger.error(f"Could not pull data availability matrix from caching table: {e}")
        return set()

def backfill_missing_days(days=30):
    if not supabase:
        return
    logger.info("Initializing historical backfill parameters for physical asset caches...")
    existing = get_existing_dates()
    end = datetime.now()
    missing = []
    
    for i in range(days):
        date_str = (end - timedelta(days=i)).strftime("%Y-%m-%d")
        for metal in METALS:
            if (date_str, metal) not in existing:
                missing.append((metal, date_str))
    
    if not missing:
        logger.info("Structural physical data cache verification matches execution requirements.")
        return
    
    for metal, date_str in sorted(missing, key=lambda x: x[1]):
        record = fetch_metal_for_date(metal, date_str)
        if record:
            try:
                supabase.table(TABLE).upsert(record).execute()
                time.sleep(1.5)
            except Exception as e:
                logger.error(f"Persistence operation interrupted on cache storage operation: {e}")

def update_today():
    if not supabase:
        return
    today = datetime.now().strftime("%Y-%m-%d")
    existing = get_existing_dates()
    
    for metal in METALS:
        if (today, metal) in existing:
            continue
        record = fetch_metal_for_date(metal, today)
        if record:
            try:
                supabase.table(TABLE).upsert(record).execute()
                logger.info(f"Refreshed real-time data cache vector for {metal} matching window {today}")
            except Exception as e:
                logger.error(f"Real-time metadata persistence error encountered: {e}")

def get_historical_from_cache(metal: str, days: int = 60):
    if not supabase:
        return None
    try:
        response = supabase.table(TABLE)\
            .select("*")\
            .eq("metal", metal.upper())\
            .order("date", desc=True)\
            .limit(days)\
            .execute()
        data = response.data
        if not data:
            return None
        import pandas as pd
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        df = df.rename(columns={
            'date': 'Date',
            'open_price': 'Open',
            'high_price': 'High',
            'low_price': 'Low',
            'price': 'Close',
            'prev_close': 'PreviousClose'
        })
        df = df[['Date', 'Open', 'High', 'Low', 'Close', 'PreviousClose']].dropna()
        df.set_index('Date', inplace=True)
        return df
    except Exception as e:
        logger.error(f"Fallback initiated. Error resolving cache structures for {metal}: {e}")
        return None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    backfill_missing_days(days=30)
    update_today()
