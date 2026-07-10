import os
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from app.bot.handlers import handle_market_query, start_handler
from app.logger import logger

def create_bot() -> Application:
    """Configures persistent state instances and binds message routing paths
    using a framework-compliant unified catch-all logic flow map.
    """
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        logger.critical("❌ Missing critical configuration: TELEGRAM_TOKEN environment variable is unset.")
        raise ValueError("TELEGRAM_TOKEN environment variable must be specified.")

    app = Application.builder().token(token).build()
    
    # ━━━━ 🏛️ FRAMEWORK-COMPLIANT MULTI-ENTRY ROUTER MATRIX ━━━━
    
    # Handler 1: Explicitly trap the primary onboarding command sequence first
    app.add_handler(CommandHandler("start", start_handler))
    
    # Handler 2: Catch ALL other slash commands dynamically using a framework Command Filter
    # This replaces the broken regex CommandHandler completely and routes safely without TypeError risk
    app.add_handler(MessageHandler(filters.COMMAND, handle_market_query))
    
    # Handler 3: Route text inputs that omit slashes cleanly into the same validation loop
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_market_query))
    
    logger.info("🤖 Telegram systematic routing handlers bound to execution context successfully.")
    return app
