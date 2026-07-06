from telegram import Update
from telegram.ext import ContextTypes
from app.logger import logger

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the interactive /start command."""
    user = update.effective_user
    username_segment = f" ({user.username})" if user.username else ""
    logger.info(f"User {user.id}{username_segment} issued /start.")
    
    await update.message.reply_text(
        f"🚀 *System Online*\n\n"
        f"Welcome {user.first_name}!\n"
        f"The Market Intelligence Engine is alive and ready.\n"
        f"More features coming soon…",
        parse_mode="Markdown"
    )

async def health_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the interactive /health verification update ping."""
    logger.info(f"User {update.effective_user.id} requested system status check.")
    await update.message.reply_text("✅ System is healthy and running.")
