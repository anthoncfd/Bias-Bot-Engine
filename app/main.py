import os
import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn

# Import the configured bot application instance from your service layer
from app.services.telegram_bot import application

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("macro_engine.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles non-blocking background execution loops for the Telegram engine.
    """
    logger.info("Initializing Macro Bias Engine Core Components...")
    
    # Verify token exists before firing up loops
    if not os.getenv("TELEGRAM_TOKEN"):
        logger.error("CRITICAL: TELEGRAM_TOKEN environment variable is missing on Render!")
    else:
        try:
            logger.info("Starting Telegram Bot application context...")
            await application.initialize()
            await application.start()
            
            # Fire off the polling loop inside a non-blocking asyncio task thread
            asyncio.create_task(application.updater.start_polling())
            logger.info("Telegram engine successfully attached and polling active.")
        except Exception as e:
            logger.error(f"Failed to start Telegram polling thread layer: {e}")
            
    yield
    
    logger.info("Shutting down Macro Bias Engine systems...")
    if os.getenv("TELEGRAM_TOKEN"):
        try:
            await application.updater.stop()
            await application.stop()
            await application.shutdown()
            logger.info("Telegram listener gracefully disconnected.")
        except Exception as e:
            logger.error(f"Error cleanly stopping Telegram runner: {e}")

# Initialize FastAPI Framework Routing
app = FastAPI(
    title="Macro Bias Engine API",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/")
async def root_health_check():
    """Keeps Render port-scanner happy so deployments never time out."""
    return {
        "status": "healthy",
        "engine": "Macro Bias Engine Bot Router",
        "timestamp": "Operational"
    }

if __name__ == "__main__":
    port_env = os.environ.get("PORT", "8000")
    try:
        bind_port = int(port_env)
    except ValueError:
        bind_port = 8000

    logger.info(f"Launching production server wrapper on port: {bind_port}")
    uvicorn.run("app.main:app", host="0.0.0.0", port=bind_port, workers=1)
