import os
import logging
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update
from dotenv import load_dotenv

from app.engines.macro_engine import calculate_asset_bias

load_dotenv()
logger = logging.getLogger("macro_engine.bot")

TOKEN = os.getenv("TELEGRAM_TOKEN")

async def process_and_send_bias(update: Update, context: ContextTypes.DEFAULT_TYPE, asset: str):
    status_message = await update.message.reply_text(
        f"🔄 Ingesting market streams for {asset}... Running calculations..."
    )
    
    try:
        data = await calculate_asset_bias(asset)
        
        # Completely swapped watermark signature layer for high-end context trading quotes
        final_report = (
            f"📊 **{asset} MACRO BIAS REPORT**\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💡 **CORE BIAS:** `{data['bias']}`\n"
            f"🎯 **CONFIDENCE LEVEL:** `{data['confidence']}`\n"
            f"🔄 **MARKET REGIME:** `{data['regime']}`\n\n"
            f"📈 **PRICE LOG DATA**\n"
            f"• **Live Spot Price:** `{data['live_price']}`\n"
            f"• **Previous Close:** `{data['prev_close']}`\n"
            f"• **Rolling 20 SMA:** `{data['sma_20']}`\n"
            f"• **Momentum (Z-Score):** `{data['momentum']}`\n\n"
            f"📰 **HIGH-IMPACT MACRO WIRE**\n"
            f"{data['news']}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🧠 _**RISK INSIGHT:**_\n"
            f"_{data['quote']}_\n"
        )
        
        await status_message.edit_text(final_report, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Interface build crash: {e}")
        await status_message.edit_text("❌ Critical error generating advanced report output panels.")

async def handle_eurusd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await process_and_send_bias(update, context, "EURUSD")

async def handle_eurjpy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await process_and_send_bias(update, context, "EURJPY")

application = Application.builder().token(TOKEN).build()
application.add_handler(CommandHandler("eurusd", handle_eurusd))
application.add_handler(CommandHandler("eurjpy", handle_eurjpy))
