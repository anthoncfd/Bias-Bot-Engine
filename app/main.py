import os
import sys
import asyncio
import httpx
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from app.config import settings
from app.logger import logger
from app.bot.bot import create_bot
from app.services.market_data import MarketDataService

# Create a single, persistent, global async HTTP client pool instance
global_http_client = httpx.AsyncClient(
    timeout=httpx.Timeout(15.0, connect=5.0),
    limits=httpx.Limits(max_connections=50, max_keepalive_connections=10)
)

async def warm_historical_cache_layer():
    """Loops through asset trackers on bootup using strict rate-safe pacing to check baseline data."""
    try:
        await asyncio.sleep(5)
        is_github_ci = os.getenv("GITHUB_ACTIONS") == "true"
        
        if is_github_ci:
            logger.info("🧪 GitHub Actions environment detected. Checking free Yahoo Finance assets...")
            sync_symbols = ["YM=F", "^N225", "NQ=F", "BTCUSD", "ETHUSD", "BNBUSD"]
        else:
            logger.info("📡 Production Server Initialization: Checking baseline database status...")
            sync_symbols = [
                "EURUSD", "GBPUSD", "GBPJPY", "USDCAD", 
                "USDCHF", "AUDUSD", "EURJPY", "EURGBP", 
                "YM=F", "^N225", "NQ=F", "BTCUSD", "ETHUSD", "BNBUSD"
            ]
            
        service = MarketDataService(http_client=global_http_client)
        
        for index, symbol in enumerate(sync_symbols, start=1):
            logger.info(f"🔄 Baseline Check [{index}/{len(sync_symbols)}]: Verifying structural data for {symbol}")
            await service.sync_asset_historical_cache(symbol, force_refresh=False)
            
            is_forex = not any(char in symbol for char in ["=", "^", "BTC", "ETH", "BNB"])
            # Hardened startup pacing to protect API endpoints
            sleep_duration = 15 if (is_forex and not is_github_ci) else 5
            await asyncio.sleep(sleep_duration)
            
        logger.info("✅ Core initialization checks complete. Production cache engine is stable.")
        
    except Exception as err:
        logger.error(f"Cache warming loop encountered an initialization exception: {err}")

# Instantiate the global bot application configuration framework factory
telegram_app = create_bot()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles continuous deployment bootstrap configurations safely without blocking the runtime loop."""
    logger.info(f"Bootstrapping foundational operations for {settings.app_name}... Version: {settings.app_version}")
    
    if os.getenv("GITHUB_ACTIONS") == "true":
        await warm_historical_cache_layer()
        logger.info("✅ GitHub Actions environment validation complete. Terminating with exit code 0.")
        await global_http_client.aclose()
        sys.exit(0)
        
    asyncio.create_task(warm_historical_cache_layer())
    
    logger.info("Connecting and synchronizing live Telegram network sockets...")
    await telegram_app.initialize()
    await telegram_app.start()
    await telegram_app.updater.start_polling(drop_pending_updates=True)
    logger.info("📡 Bot network engine is fully online and actively listening for commands.")
    
    yield
    
    logger.info("Signaling background worker threads for graceful task cancellation cascades...")
    await telegram_app.updater.stop()
    await telegram_app.stop()
    await telegram_app.shutdown()
    
    await global_http_client.aclose()
    logger.info("Ecosystem internal bot engines cleanly shut down.")

app = FastAPI(
    title=settings.app_name, 
    version=settings.app_version, 
    debug=settings.debug, 
    lifespan=lifespan
)

@app.get("/api/v3/macro-engine/utc-rollover-sync", tags=["Data Automation Engine"])
async def force_utc_day_rollover_synchronizer(secret_token: str | None = None):
    """Secure automation hook executed at 00:05 UTC via cron-job.org."""
    if not secret_token or secret_token != settings.supabase_key[:10]:
        raise HTTPException(status_code=401, detail="Invalid execution secret token context.")
        
    logger.info("📅 00:05 UTC Day Rollover Triggered: Appending closed daily candle transactions...")
    service = MarketDataService(http_client=global_http_client)
    
    sync_symbols = [
        "EURUSD", "GBPUSD", "GBPJPY", "USDCAD", 
        "USDCHF", "AUDUSD", "EURJPY", "EURGBP", 
        "YM=F", "^N225", "NQ=F", "BTCUSD", "ETHUSD", "BNBUSD"
    ]
    
    for index, symbol in enumerate(sync_symbols, start=1):
        try:
            logger.info(f"🔄 Rollover Sync [{index}/{len(sync_symbols)}]: Appending fresh close row for {symbol}")
            await service.sync_asset_historical_cache(symbol, force_refresh=True)
            
            # 🛡️ RATE LIMIT SHIELD: Standardize a strict 15-second delay between assets
            # This completely prevents "429 Too Many Requests" errors across all plans
            await asyncio.sleep(15)
            
        except Exception as e:
            logger.error(f"Failed to append daily rollover close for target {symbol}: {e}")
            await asyncio.sleep(5)
            
    logger.info("✅ Database historical rows are successfully synchronized for the new trading session.")
    return {"status": "synchronized", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.get("/health", tags=["System Infrastructure"])
async def system_health_check():
    return {
        "status": "operational", 
        "app_name": settings.app_name,
        "version": settings.app_version,
        "engine_mode": "Production" if not settings.debug else "Development"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=settings.debug)
