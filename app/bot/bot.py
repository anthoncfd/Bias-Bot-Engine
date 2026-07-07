import asyncio
from telegram.ext import Application, CommandHandler
from app.config import settings
from app.bot import handlers
from app.logger import logger

def create_bot() -> Application:
    application = Application.builder().token(settings.telegram_bot_token).build()
    
    application.add_handler(CommandHandler("start", handlers.start_command))
    application.add_handler(CommandHandler("health", handlers.health_command))
    
    # Forex Commands Mounts
    application.add_handler(CommandHandler("eurusd", handlers.eurusd_handler))
    application.add_handler(CommandHandler("gbpusd", handlers.gbpusd_handler))
    application.add_handler(CommandHandler("gbpjpy", handlers.gbpjpy_handler))
    application.add_handler(CommandHandler("usdcad", handlers.usdcad_handler))
    application.add_handler(CommandHandler("usdchf", handlers.usdchf_handler))
    application.add_handler(CommandHandler("audusd", handlers.audusd_handler))
    application.add_handler(CommandHandler("eurjpy", handlers.eurjpy_handler))
    application.add_handler(CommandHandler("eurgbp", handlers.eurgbp_handler))
    
    # Indices Commands Mounts
    application.add_handler(CommandHandler("jp225", handlers.jp225_handler))
    application.add_handler(CommandHandler("us30", handlers.us30_handler))
    application.add_handler(CommandHandler("us100", handlers.us100_handler))
    
    # Crypto Commands Mounts
    application.add_handler(CommandHandler("btcusd", handlers.btcusd_handler))
    application.add_handler(CommandHandler("ethusd", handlers.ethusd_handler))
    application.add_handler(CommandHandler("bnbusd", handlers.bnbusd_handler))
    
    logger.info("Telegram engine application routes initialized.")
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
