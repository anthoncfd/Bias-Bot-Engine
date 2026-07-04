import os
import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn

# Bind the configured bot application instance from your service layer
from app.services.telegram_bot import application

# Setup structural log output configurations
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("macro_engine.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles seamless background execution loops for the Telegram engine
    without choking the primary FastAPI web routing layer.
    """
    logger.info("Initializing Macro Bias Engine Core Components...")
    
    if not os.getenv("TELEGRAM_TOKEN"):
        logger.error("CRITICAL ERROR: TELEGRAM_TOKEN environment variable is missing on Render configuration tabs!")
    else:
        try:
            logger.info("Starting Telegram Bot application context...")
            await application.initialize()
            await application.start()
            
            # Spin off polling inside a non-blocking background asyncio task thread
            asyncio.create_task(application.updater.start_polling())
            logger.info("Telegram engine successfully attached and polling active.")
        except Exception as e:
            logger.error(f"Failed to start Telegram polling layer: {e}")
            
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
    """
    Crucial endpoint for Render's deployment engine.
    Returns 200 OK instantly to pass the platform's HTTP connection scan.
    """
    return {
        "status": "healthy",
        "engine": "Macro Bias Engine Bot Router",
        "timestamp": "Operational"
    }

if __name__ == "__main__":
    # Pull dynamic port structural value assigned by Render environment
    # Fallback natively to 8000 for local workspace testing profiles
    port_env = os.environ.get("PORT", "8000")
    try:
        bind_port = int(port_env)
    except ValueError:
        logger.warning(f"Invalid PORT environment assignment string: '{port_env}'. Defaulting to 8000.")
        bind_port = 8000

    logger.info(f"Launching production server wrapper on host 0.0.0.0 binding to port: {bind_port}")
    uvicorn.run("app.main:app", host="0.0.0.0", port=bind_port, workers=1)
