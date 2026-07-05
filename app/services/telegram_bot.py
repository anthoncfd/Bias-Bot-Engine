import os
import logging
import traceback
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from app.engines.macro_engine import calculate_asset_bias

# Initialize premium structural execution logger
logger = logging.getLogger(__name__)

# ------------------------------------------------------------
# Premium Layout Generation Factory (Full Version)
# ------------------------------------------------------------
def build_html_report_panel(asset: str, data: dict) -> str:
    """Compiles the signature Macro Bias Report layout."""
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
# Event Handlers
# ------------------------------------------------------------
async def handle_bias_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    asset_input = update.message.text.strip().replace("/", "").upper()
    if not asset_input:
        return

    status_message = await update.message.reply_text("⚡ Processing matrix...", parse_mode=ParseMode.HTML)

    try:
        metrics_dict = await calculate_asset_bias(asset_input)
        if not metrics_dict:
            await status_message.edit_text("❌ Calculus engine returned no data.")
            return

        report_html = build_html_report_panel(asset_input, metrics_dict)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=report_html,
            parse_mode=ParseMode.HTML
        )
        await status_message.delete()
    except Exception as e:
        logger.error(f"Crash on {asset_input}: {e}", exc_info=True)
        await status_message.edit_text(f"❌ <b>System Error:</b>\n<i>{str(e)[:100]}</i>", parse_mode=ParseMode.HTML)
