import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config import settings
from app.logger import logger
from app.bot.bot import run_polling

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages foundational bootstrap contexts and clean background task destruction flags."""
    logger.info(f"Bootstrapping foundational operations for {settings.app_name}... Version: {settings.app_version}")
    
    # Initialize background long-polling worker contexts for the bot engine thread pool
    bot_task = asyncio.create_task(run_polling())
    
    yield
    
    logger.info("Signaling background worker threads for graceful task cancellation cascades...")
    bot_task.cancel()
    try:
        await bot_task
    except asyncio.CancelledError:
        logger.info("Background telemetry monitoring loops successfully broken and detached.")
    
    logger.info("Ecosystem internal applications completely finalized.")

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan
)

@app.get("/health", tags=["System Operational Infrastructure"])
async def system_health_check():
    return {
        "status": "operational",
        "app_name": settings.app_name,
        "version": settings.app_version,
        "engine_mode": "Production" if not settings.debug else "Development"
    }
