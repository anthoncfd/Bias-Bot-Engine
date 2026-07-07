import asyncio
from telegram.ext import Application, CommandHandler
from app.config import settings
from app.bot import handlers
from app.logger import logger

def create_bot() -> Application:
    application = Application.builder().token(settings.telegram_bot_token).build()
    
    # Corrected handler function pointers to match handlers.py syntax definitions exactly
    application.add_handler(CommandHandler("start", handlers.start_handler))
    
    # Forex Commands Mounts
    application.add_handler(CommandHandler("eurusd", handlers.eurusd_handler))
    application.add_handler(CommandHandler("gbpusd", handlers.gbpusd_handler))
    application.add_handler(CommandHandler("gbpjpy", handlers.gbpjpy_handler))
    
    # Indices Commands Mounts
    application.add_handler(CommandHandler("jp225", handlers.jp225_handler))
    application.add_handler(CommandHandler("us30", handlers.us30_handler))
    
    # Crypto Commands Mounts
    application.add_handler(CommandHandler("btcusd", handlers.btcusd_handler))
    application.add_handler(CommandHandler("ethusd", handlers.ethusd_handler))
    application.add_handler(CommandHandler("bnbusd", handlers.bnbusd_handler))
    
    logger.info("Telegram engine application routes initialized successfully.")
    return application

async def run_polling():
    app = create_bot()
    logger.info("Initializing background bot operational threads...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        logger.info("Bot execution context received system thread cancellation.")
    finally:
        if app.updater and app.updater.running:
            await app.updater.stop()
        await app.stop()
        await app.shutdown()
        logger.info("Ecosystem internal bot engines cleanly shut down.")
