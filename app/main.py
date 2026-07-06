import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.routes import router as api_router
from app.config import settings
from app.logger import logger
from app.bot.bot import run_polling

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Event Hook: Setup server background processes
    logger.info(f"Bootstrapping foundational operations for {settings.app_name}...")
    bot_task = asyncio.create_task(run_polling())
    
    yield
    
    # Event Hook: Tear down background application contexts
    logger.info("Gracefully severing system infrastructure states...")
    bot_task.cancel()
    try:
        await bot_task
    except asyncio.CancelledError:
        logger.info("System server core verified successful runtime termination stack.")

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan
)

# Route Mounting Configurations
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.app_name} v{settings.app_version}",
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
