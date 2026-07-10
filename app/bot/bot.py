import os
import re
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from app.bot.handlers import handle_market_query, start_handler
from app.logger import logger

def create_bot() -> Application:
    """Configures persistent state instances and binds message routing paths
    using a unified institutional catch-all handler configuration matrix.
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.critical("❌ Missing critical configuration: TELEGRAM_BOT_TOKEN environment variable is unset.")
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable must be specified.")

    app = Application.builder().token(token).build()
    
    # ━━━━ 🏛️ UNIFIED MULTI-ENTRY ROUTER MATRIX ━━━━
    # Route onboarding commands to the dedicated startup message handler
    app.add_handler(CommandHandler("start", start_handler))
    
    # Catch any remaining slash commands dynamically via unified regex pattern configurations
    app.add_handler(CommandHandler(re.compile(r'.*'), handle_market_query))
    
    # Route text inputs that omit slashes cleanly into the same validation loop
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_market_query))
    
    logger.info("🤖 Telegram systematic routing handlers bound to execution context successfully.")
    return app
