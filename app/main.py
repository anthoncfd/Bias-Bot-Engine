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
    logger.info("Starting background cache warming and validation layer...")
    service = MarketDataService()
    
    # Swapped indices to Yahoo Finance native tickers (prefixed with ^)
    sync_symbols = [
        "EUR/USD", "GBP/USD", "GBP/JPY", "USD/CAD", 
        "USD/CHF", "AUD/USD", "EUR/JPY", "EUR/GBP", 
        "^N225", "^DJI", "^IXIC"
    ]
    
    for symbol in sync_symbols:
        await service.sync_asset_historical_cache(symbol)
        # 8-second structural pause completely avoids free-tier 429 API rate limit exhaustion
        await asyncio.sleep(8)
    logger.info("All market intelligence historical asset matrix indexes are fully synchronized.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles continuous deployment bootstrap configurations safely."""
    logger.info(f"Bootstrapping foundational operations for {settings.app_name}... Version: {settings.app_version}")
    
    # 1. Always run the validation and cache warming sequence first
    await warm_historical_cache_layer()
    
    # 2. Check if this is a manual test inside GitHub Actions
    if os.getenv("GITHUB_ACTIONS") == "true":
        logger.info("✅ GitHub Actions environment validation complete. Terminating with exit code 0.")
        sys.exit(0)
        
    # 3. Otherwise, proceed with normal 24/7 hosting on Render
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
