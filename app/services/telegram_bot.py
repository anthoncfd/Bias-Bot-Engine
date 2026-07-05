import os
import logging
import traceback
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from app.engines.macro_engine import calculate_asset_bias

logger = logging.getLogger(__name__)

def build_html_report_panel(asset: str, data: dict) -> str:
    bias = data.get("bias", "⚪ NEUTRAL")
    confidence = data.get("confidence", 50.0)
    regime = data.get("regime", "Compression Range")
    live_price = data.get("live_price", 0.0)
    prev_close = data.get("prev_close", 0.0)
    sma_20 = data.get("sma_20", 0.0)
    momentum = data.get("momentum", 0.0)
    news = data.get("news", "")
    quote = data.get("quote", "")
    inference = data.get("macro_inference", "No inference available.")

    fmt = lambda v: f"{float(v):,.4f}" if float(v) < 10.0 else f"{float(v):,.2f}"

    return (
        f"📊 <b>{asset.upper()} MACRO BIAS REPORT</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💡 <b>CORE BIAS:</b> <code>{bias}</code>\n"
        f"🎯 <b>CONFIDENCE LEVEL:</b> <code>{confidence:.1f}%</code>\n"
        f"🔄 <b>MARKET REGIME:</b> <code>{regime}</code>\n\n"
        f"📈 <b>PRICE LOG DATA</b>\n"
        f"• <b>Last Price Point:</b> <code>{fmt(live_price)}</code>\n"
        f"• <b>Prior Trading Close:</b> <code>{fmt(prev_close)}</code>\n"
        f"• <b>Rolling 20 SMA:</b> <code>{fmt(sma_20)}</code>\n"
        f"• <b>Momentum (Z-Score):</b> <code>{momentum:+.2f}</code>\n\n"
        f"📰 <b>HIGH-IMPACT MACRO WIRE</b>\n"
        f"{news}\n\n"
        f"🧠 <b>MACRO STRATEGY INFERENCE</b>\n"
        f"<i>{inference}</i>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏛️ <i><b>RISK INSIGHT:</b></i>\n"
        f"<i>{quote}</i>\n"
    )

async def handle_bias_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    asset_input = update.message.text.strip().replace("/", "").upper()
    status_message = await update.message.reply_text("⚡ Analyzing macro structure...", parse_mode=ParseMode.HTML)

    try:
        metrics_dict = await calculate_asset_bias(asset_input)
        
        if not metrics_dict:
            await status_message.edit_text(
                f"❌ <b>Engine Empty Return:</b>\n"
                f"The calculus pipeline returned an empty payload for token target: <code>{asset_input}</code>.",
                parse_mode=ParseMode.HTML
            )
            return

        report_html = build_html_report_panel(asset_input, metrics_dict)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=report_html,
            parse_mode=ParseMode.HTML
        )
        await status_message.delete()
        
    except Exception as e:
        logger.error(f"Exception encountered for {asset_input}: {traceback.format_exc()}")
        try:
            await status_message.edit_text(f"❌ <b>Pipeline Exception Error:</b>\n<code>{str(e)}</code>", parse_mode=ParseMode.HTML)
        except Exception:
            pass

token = os.getenv("TELEGRAM_TOKEN")
application = Application.builder().token(token).build()
application.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text("SirAnthony Engine Active 🚀")))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_bias_request))
