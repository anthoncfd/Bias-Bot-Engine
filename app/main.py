import os
import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn
from app.services.telegram_bot import application

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up engine core...")
    await application.initialize()
    await application.start()
    asyncio.create_task(application.updater.start_polling())
    yield
    logger.info("Shutting down engine core...")
    await application.updater.stop()
    await application.stop()
    await application.shutdown()

app = FastAPI(title="Macro Engine", lifespan=lifespan)

@app.get("/")
async def root():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), workers=1)
