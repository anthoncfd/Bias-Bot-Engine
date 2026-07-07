import asyncio
from telegram.ext import Application, CommandHandler
from app.config import settings
from app.bot import handlers
from app.logger import logger

def create_bot() -> Application:
    """Enterprise configuration factory that builds the python-telegram-bot application state
    and binds matching controller routers precisely.
    """
    # Initialize the core PTB framework engine using the configured Telegram bot token
    application = Application.builder().token(settings.telegram_bot_token).build()
    
    # ⚙️ GLOBAL UTILITY COMMAND ROUTES
    application.add_handler(CommandHandler("start", handlers.start_handler))
    
    # 💱 FOREX TELEMETRY HANDLER ROUTES
    application.add_handler(CommandHandler("eurusd", handlers.eurusd_handler))
    application.add_handler(CommandHandler("gbpusd", handlers.gbpusd_handler))
    application.add_handler(CommandHandler("gbpjpy", handlers.gbpjpy_handler))
    application.add_handler(CommandHandler("usdcad", handlers.usdcad_handler))
    application.add_handler(CommandHandler("usdchf", handlers.usdchf_handler))
    application.add_handler(CommandHandler("audusd", handlers.audusd_handler))
    application.add_handler(CommandHandler("eurjpy", handlers.eurjpy_handler))
    application.add_handler(CommandHandler("eurgbp", handlers.eurgbp_handler))
    
    # 📈 FUTURES & CFD STOCK INDEX HANDLER ROUTES
    application.add_handler(CommandHandler("us30", handlers.us30_handler))
    application.add_handler(CommandHandler("nas100", handlers.nas100_handler))
    application.add_handler(CommandHandler("jp225", handlers.jp225_handler))
    
    # 🪙 CRYPTOCURRENCY MULTI-VECTORS SPOT HANDLER ROUTES
    application.add_handler(CommandHandler("btcusd", handlers.btcusd_handler))
    application.add_handler(CommandHandler("ethusd", handlers.ethusd_handler))
    application.add_handler(CommandHandler("bnbusd", handlers.bnbusd_handler))
    
    logger.info("🤖 Telegram systematic routing handlers bound to execution context successfully.")
    return application

if __name__ == "__main__":
    # NATIVE ISOLATED BACKEND RUNNER RUN TRACK:
    # This block allows you to manually run the bot as a pure, standalone console script 
    # if you ever decide to isolate it completely away from the FastAPI web framework.
    bot_instance = create_bot()
    logger.info("🚀 Launching standalone background long-polling engine layer...")
    
    # drop_pending_updates=True guarantees that the bot instantly drops the backlog
    # of messages sent while it was offline, preventing an endless queue flooding loop.
    bot_instance.run_polling(drop_pending_updates=True)
