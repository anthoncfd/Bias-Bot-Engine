import asyncio
from telegram.ext import Application, CommandHandler
from app.config import settings
from app.bot.handlers import start_command, health_command
from app.logger import logger

def create_bot() -> Application:
    """Instantiate and construct structural bot configurations."""
    application = Application.builder().token(settings.telegram_bot_token).build()
    
    # Bind dynamic bot command actions
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("health", health_command))
    
    logger.info("Telegram engine application routes initialized.")
    return application

async def run_polling():
    """Execute non-blocking long-polling operation lifecycle runtime context."""
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
        logger.info("Commencing application safe system state shutdowns...")
        if app.updater and app.updater.running:
            await app.updater.stop()
        await app.stop()
        await app.shutdown()
        logger.info("Ecosystem internal bot engines cleanly shut down.")
