import os
import logging
import traceback
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from app.engines.macro_engine import calculate_asset_bias

# Initialize logger
logger = logging.getLogger(__name__)

# ------------------------------------------------------------
# Layout Generation Factory
# ------------------------------------------------------------
def build_html_report_panel(asset: str, data: dict) -> str:
    bias = data.get("bias", "⚪ NEUTRAL")
    confidence = data.get("confidence", 50.0)
    regime = data.get("regime", "Compression Range")
    live_price = data.get("live_price", 0.0)
    prev_close = data.get("prev_close", 0.0)
    sma_20 = data.get("sma_20", 0.0)
    momentum = data.get("momentum", data.get("z_score", 0.0))
    news = data.get("news", "• No critical structural updates found.")
    quote = data.get("quote", '"Cash is an active position."')
    inference = data.get("macro_inference", data.get("inference", "No inference available."))

    def format_price(val) -> str:
        try:
            float_val = float(val)
            return f"{float_val:,.4f}" if float_val < 10.0 else f"{float_val:,.2f}"
        except (ValueError, TypeError):
            return str(val)

    conf_str = f"{confidence:.1f}%" if isinstance(confidence, (int, float)) else str(confidence)
    mom_str = f"{float(momentum):+.2f}" if isinstance(momentum, (int, float)) else str(momentum)

    return (
        f"📊 <b>{asset.upper()} MACRO BIAS REPORT</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💡 <b>CORE BIAS:</b> <code>{bias}</code>\n"
        f"🎯 <b>CONFIDENCE LEVEL:</b> <code>{conf_str}</code>\n"
        f"🔄 <b>MARKET REGIME:</b> <code>{regime}</code>\n\n"
        f"📈 <b>PRICE LOG DATA</b>\n"
        f"• <b>Live Spot Price:</b> <code>{format_price(live_price)}</code>\n"
        f"• <b>Previous Close:</b> <code>{format_price(prev_close)}</code>\n"
        f"• <b>Rolling 20 SMA:</b> <code>{format_price(sma_20)}</code>\n"
        f"• <b>Momentum (Z-Score):</b> <code>{mom_str}</code>\n\n"
        f"📰 <b>HIGH-IMPACT MACRO WIRE</b>\n"
        f"{news}\n\n"
        f"🧠 <b>MACRO INFERENCE SUMMARY</b>\n"
        f"<i>{inference}</i>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏛️ <i><b>RISK INSIGHT:</b></i>\n"
        f"<i>{quote}</i>\n"
    )

# ------------------------------------------------------------
# Handlers
# ------------------------------------------------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("SirAnthony Bias Engine Active 🚀")

async def handle_bias_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    asset_input = update.message.text.strip().replace("/", "").upper()
    if not asset_input:
        return

    status_message = await update.message.reply_text("⚡ Analyzing macro structure...", parse_mode=ParseMode.HTML)

    try:
        # Await data computation from the backend engine
        metrics_dict = await calculate_asset_bias(asset_input)
        
        # Check if the engine completely returned an empty payload or None
        if not metrics_dict:
            await status_message.edit_text(
                f"❌ <b>Engine Empty Return:</b>\n"
                f"The calculus pipeline returned an empty payload for token target: <code>{asset_input}</code>. "
                f"Verify if the asset ticker is properly mapped in your historical data tables or APIs.",
                parse_mode=ParseMode.HTML
            )
            return

        # Render layout
        report_html = build_html_report_panel(asset_input, metrics_dict)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=report_html,
            parse_mode=ParseMode.HTML
        )
        await status_message.delete()
        
    except Exception as e:
        # Extract full trace metrics to surface exactly where it broke
        error_details = traceback.format_exc()
        logger.error(f"Macro processing exception on {asset_input}:\n{error_details}")
        
        # Directly notify the operator within the chat box window for faster debugging
        await status_message.edit_text(
            f"❌ <b>Calculus Pipeline Exception:</b>\n"
            f"<code>{str(e)}</code>", 
            parse_mode=ParseMode.HTML
        )

# ------------------------------------------------------------
# GLOBAL APPLICATION INITIALIZATION
# ------------------------------------------------------------
token = os.getenv("TELEGRAM_TOKEN")
if not token:
    raise ValueError("TELEGRAM_TOKEN not found in environment.")

application = Application.builder().token(token).build()
application.add_handler(CommandHandler("start", start_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_bias_request))
