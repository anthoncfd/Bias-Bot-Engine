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
    
    # We do not sync crypto because it reads dynamically off live public frameworks natively
    sync_symbols = [
        "EUR/USD", "GBP/USD", "GBP/JPY", "USD/CAD", 
        "USD/CHF", "AUD/USD", "EUR/JPY", "EUR/GBP", 
        "NI225", "DJI", "IXIC"
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
    
    # Fire up background caching routines safely alongside core async loops
    asyncio.create_task(warm_historical_cache_layer())
    bot_task = asyncio.create_task(run_polling())
    
    yield
    
    logger.info("Signaling background worker threads for graceful task cancellation cascades...")
    bot_task.cancel()
    try:
        await bot_task
    except asyncio.CancelledError:
        logger.info("Background telemetry monitoring loops successfully broken and detached.")

app = FastAPI(title=settings.app_name, version=settings.app_version, debug=settings.debug, lifespan=lifespan)

@app.get("/health", tags=["System Infrastructure"])
async def system_health_check():
    return {"status": "operational", "engine_mode": "Production"}
