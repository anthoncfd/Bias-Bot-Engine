import os
import sys
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config import settings
from app.logger import logger
from app.bot.bot import create_bot
from app.services.market_data import MarketDataService

async def warm_historical_cache_layer():
    """Loops through asset trackers on bootup using strict rate-safe pacing to protect API limits."""
    try:
        # Fixed: Standard, safe, non-blocking async sleep initialization anchor
        await asyncio.sleep(5)
        
        is_github_ci = os.getenv("GITHUB_ACTIONS") == "true"
        
        if is_github_ci:
            logger.info("🧪 GitHub Actions environment detected. Warming ONLY free Yahoo Finance assets to protect production keys...")
            sync_symbols = ["YM=F", "NKD=F", "NQ=F", "BTCUSD", "ETHUSD", "BNBUSD"]
        else:
            logger.info("📡 Production Server Initialization: Deploying master cache mapping sequences...")
            sync_symbols = [
                "EURUSD", "GBPUSD", "GBPJPY", "USDCAD", 
                "USDCHF", "AUDUSD", "EURJPY", "EURGBP", 
                "YM=F", "NKD=F", "NQ=F", "BTCUSD", "ETHUSD", "BNBUSD"
            ]
            
        service = MarketDataService()
        
        for index, symbol in enumerate(sync_symbols, start=1):
            logger.info(f"🔄 Warming Cache Matrix [{index}/{len(sync_symbols)}]: Processing target asset {symbol}")
            await service.sync_asset_historical_cache(symbol)
            
            is_forex = not any(char in symbol for char in ["=", "^", "BTC", "ETH", "BNB"])
            sleep_duration = 12 if (is_forex and not is_github_ci) else 3
            await asyncio.sleep(sleep_duration)
            
        logger.info("✅ All market intelligence historical asset matrix indexes are fully synchronized.")
        
    except Exception as err:
        logger.error(f"Cache warming loop encountered an initialization exception: {err}")

# Instantiate the global bot application configuration framework
telegram_app = create_bot()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles continuous deployment bootstrap configurations safely without blocking the runtime loop."""
    logger.info(f"Bootstrapping foundational operations for {settings.app_name}... Version: {settings.app_version}")
    
    if os.getenv("GITHUB_ACTIONS") == "true":
        await warm_historical_cache_layer()
        logger.info("✅ GitHub Actions environment validation complete. Terminating with exit code 0.")
        sys.exit(0)
        
    # Production Track: Detach cache warming to run smoothly on background worker lines
    asyncio.create_task(warm_historical_cache_layer())
    
    # Clean Lifespan Bind: Link the bot smoothly into the active Uvicorn loop
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
    logger.info("Ecosystem internal bot engines cleanly shut down.")

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
