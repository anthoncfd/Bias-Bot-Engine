import os
import sys
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config import settings
from app.logger import logger
from app.bot.bot import run_polling
from app.services.market_data import MarketDataService

async def warm_historical_cache_layer():
    """Loops through all fiat and index trackers on bootup to populate historical profiles safely."""
    try:
        # Give the system 5 seconds to let the main bot application boot up safely first
        await asyncio.sleep(5)
        logger.info("📡 Starting background cache warming and validation layer...")
        service = MarketDataService()
        
        # 🎯 CRITICAL FIX: Synchronized precisely with market_data.py symbols matrix
        sync_symbols = [
            "EURUSD", "GBPUSD", "GBPJPY", "USDCAD", 
            "USDCHF", "AUDUSD", "EURJPY", "EURGBP", 
            "YM=F", "NKD=F", "NQ=F", "BTCUSD", "ETHUSD", "BNBUSD"
        ]
        
        for symbol in sync_symbols:
            await service.sync_asset_historical_cache(symbol)
            # Structural pause to avoid free-tier API rate limit adjustments
            await asyncio.sleep(8)
        logger.info("✅ All market intelligence historical asset matrix indexes are fully synchronized.")
        
    except Exception as err:
        logger.error(f"Cache warming loop encountered an initialization exception: {err}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles continuous deployment bootstrap configurations safely."""
    logger.info(f"Bootstrapping foundational operations for {settings.app_name}... Version: {settings.app_version}")
    
    # 1. Check if this is a manual test inside GitHub Actions
    if os.getenv("GITHUB_ACTIONS") == "true":
        # For CI validation steps, we run the cache sync sequentially and terminate
        await warm_historical_cache_layer()
        logger.info("✅ GitHub Actions environment validation complete. Terminating with exit code 0.")
        sys.exit(0)
        
    # 2. Production Render Run Track: Spin up the warming sequence as an un-blocking independent task
    asyncio.create_task(warm_historical_cache_layer())
    
    # 3. Mount and kick-off the continuous Telegram polling application instantly
    bot_task = asyncio.create_task(run_polling())
    
    yield
    
    logger.info("Signaling background worker threads for graceful task cancellation cascades...")
    bot_task.cancel()
    try:
        await bot_task
    except asyncio.CancelledError:
        logger.info("Background telemetry monitoring loops successfully broken and detached.")

app = FastAPI(
    title=settings.app_name, 
    version=settings.app_version, 
    debug=settings.debug, 
    lifespan=lifespan
)

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
