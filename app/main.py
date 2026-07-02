import logging
from fastapi import FastAPI
from app.api.routes import router, bot_app
from app.config import WEBHOOK_URL, TELEGRAM_TOKEN
import uvicorn

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Market Intelligence Bot V4.2")
app.include_router(router)

@app.on_event("startup")
async def startup():
    if WEBHOOK_URL and TELEGRAM_TOKEN:
        try:
            await bot_app.initialize()
            await bot_app.bot.set_webhook(f"{WEBHOOK_URL}/webhook")
            await bot_app.start()
            logger.info("Telegram Webhook set successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Telegram Webhook on startup: {e}")

@app.on_event("shutdown")
async def shutdown():
    try:
        await bot_app.stop()
        await bot_app.shutdown()
        logger.info("Telegram application cleanly shut down.")
    except Exception as e:
        logger.error(f"Error during shutdown sequence: {e}")

@app.get("/")
async def root():
    return {"status": "Market Intelligence Engine V4.2 - Institutional Grade Active"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)
