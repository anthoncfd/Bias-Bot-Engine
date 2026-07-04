import os
import logging
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update
from dotenv import load_dotenv

# Import your quantitative calculation framework 
from app.engines.macro_engine import calculate_asset_bias

load_dotenv()
logger = logging.getLogger("macro_engine.bot")

# Extract env token string
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_TOKEN environment variable not detected in execution workspace.")

async def process_and_send_bias(update: Update, context: ContextTypes.DEFAULT_TYPE, asset: str):
    """
    Executes core calculations dynamically and updates the initial 'Processing...'
    text block instantly with the complete macro overview.
    """
    # 1. Dispatch structural status message to the user channel
    status_message = await update.message.reply_text(
        f"🔄 Processing quantitative biases for {asset}... Please wait."
    )
    
    try:
        logger.info(f"Invoking bias matrix calculation loops for asset footprint: {asset}")
        
        # 2. Compute live matrix data using your processing module engine
        bias_results = await calculate_asset_bias(asset)
        
        # 3. Compile layout payload configurations based on output interface models
        if isinstance(bias_results, dict):
            final_report = (
                f"📊 **{asset} Macro Bias Report**\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"• **Directional Bias:** {bias_results.get('bias', 'NEUTRAL')}\n"
                f"• **Momentum Core:** {bias_results.get('momentum', '0.00')}\n"
                f"• **Macro Weight Score:** {bias_results.get('macro_score', '0.00')}\n"
                f"• **Market Regime:** {bias_results.get('regime', 'Consolidation')}\n\n"
                f"_*Watermarked @anthonycfd_"
            )
        else:
            final_report = f"{bias_results}\n\n_*Watermarked @anthonycfd_"

        # 4. Overwrite the pending message directly with the completed matrix metrics
        await status_message.edit_text(final_report, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Engine calculation layout crash for pair {asset}: {e}")
        await status_message.edit_text(
            f"❌ **Engine Error:** Could not compute quant metrics for {asset}.\n"
            f"Review live execution trace logs on Render deployment pipelines."
        )

# Asset router endpoints
async def handle_eurusd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await process_and_send_bias(update, context, "EURUSD")

async def handle_eurjpy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await process_and_send_bias(update, context, "EURJPY")

# Construct Python Telegram Bot Application Instance Container (v21+ Patterns)
application = Application.builder().token(TOKEN).build()

# Attach structural triggers to operational handler methods
application.add_handler(CommandHandler("eurusd", handle_eurusd))
application.add_handler(CommandHandler("eurjpy", handle_eurjpy))
