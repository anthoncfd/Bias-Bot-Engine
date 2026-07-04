import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn

# Setup logging pattern
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("macro_engine.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown events cleanly.
    Put any background tasks or database connection pools here.
    """
    logger.info("Initializing Macro Bias Engine Core Components...")
    
    # Example: If you use python-telegram-bot application long-polling:
    # from app.bot.telegram_client import bot_application
    # await bot_application.initialize()
    # await bot_application.start()
    # logger.info("Telegram interface online.")
    
    yield
    
    logger.info("Shutting down Macro Bias Engine systems...")
    # Example clean shutdown:
    # await bot_application.stop()
    # await bot_application.shutdown()

# Initialize FastAPI App
app = FastAPI(
    title="Macro Bias Engine API",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/")
async def root_health_check():
    """
    Crucial endpoint for Render's deployment engine.
    Returns 200 OK instantly to pass the platform's HTTP connection scan.
    """
    return {
        "status": "healthy",
        "engine": "Macro Bias Engine",
        "timezone": "UTC"
    }

@app.get("/api/v1/health")
async def api_health():
    return {"status": "operational"}

if __name__ == "__main__":
    # Pull dynamic port structural value assigned by Render environment
    # Fallback natively to 8000 for local workspace testing profiles
    port_env = os.environ.get("PORT", "8000")
    
    try:
        bind_port = int(port_env)
    except ValueError:
        logger.warning(f"Invalid PORT environment assignment string: '{port_env}'. Defaulting to 8000.")
        bind_port = 8000

    logger.info(f"Launching ASGI application layer on host 0.0.0.0 binding to port: {bind_port}")
    
    uvicorn.run(
        "app.main:app", 
        host="0.0.0.0", 
        port=bind_port,
        workers=1
    )
