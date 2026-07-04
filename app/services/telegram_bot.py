import os
import logging
import traceback
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# Global logger initialization
logger = logging.getLogger(__name__)

# ------------------------------------------------------------
# Premium Layout Generation Factory (HTML-Safe Conversion)
# ------------------------------------------------------------
def build_html_report_panel(asset: str, data: dict) -> str:
    """
    Compiles your exact signature Macro Bias Report layout using safe HTML tags.
    Preserves old-money typography and layout while preventing Telegram parse errors.
    """
    # Safely retrieve values with fallback defaults
    bias = data.get("bias", "⚪ NEUTRAL")
    confidence = data.get("confidence", 50.0)
    regime = data.get("regime", "Compression Range (Liquidity Building)")
    live_price = data.get("live_price", 0.0)
    prev_close = data.get("prev_close", 0.0)
    sma_20 = data.get("sma_20", 0.0)
    
    # Structural check to handle both 'momentum' and 'z_score' key nomenclatures
    momentum = data.get("momentum", data.get("z_score", 0.0))
    news = data.get("news", "• No high-impact macro developments reported in the last 4 hours.")
    quote = data.get("quote", '"Cash is an active position. If you don\'t have an edge, don\'t play."')

    # Helper function to dynamically scale decimal places based on asset class pricing scale
    def format_price(val) -> str:
        try:
            float_val = float(val)
            if float_val == 0.0:
                return "0.00"
            return f"{float_val:,.4f}" if float_val < 10.0 else f"{float_val:,.2f}"
        except (ValueError, TypeError):
            return str(val)

    # Clean confidence value representation
    conf_str = f"{confidence:.1f}%" if isinstance(confidence, (int, float)) else str(confidence)

    # Format momentum score cleanly with static sign indicators (+/-)
    try:
        mom_str = f"{float(momentum):+.2f}"
    except (ValueError, TypeError):
        mom_str = str(momentum)

    # YOUR EXACT SIGNATURE LAYOUT PANEL — HARDENED VIA HTML PARSING TIERS:
    html = (
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
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🧠 <i><b>RISK INSIGHT:</b></i>\n"
        f"<i>{quote}</i>\n"
    )
    return html

# ------------------------------------------------------------
# Command & Message Event Route Handlers
# ------------------------------------------------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Greets users and outlines asset processing steps."""
    welcome_text = (
        "<b>SirAnthony Bias Engine Active</b> 🚀\n\n"
        "Send me any asset token symbol directly to instantly generate your institutional macro report panel.\n"
        "<i>Examples: EURUSD, GBPUSD, BTCUSD, US30, SPX</i>"
    )
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.HTML)

async def handle_bias_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Processes incoming ticker text, evaluates macro metrics, and transmits output panels."""
    asset_input = update.message.text.strip().upper()
    
    if not asset_input:
        return

    # Keep user informed with a live calculation state status block
    status_message = await update.message.reply_text(
        f"⚡ Processing micro-structure momentum matrix profiles for <b>{asset_input}</b>...",
        parse_mode=ParseMode.HTML
    )

    try:
        # 🛡️ LAZY LOCAL IMPORT: Breaks circular import path on app boot sequence
        from app.engines.macro_engine import calculate_asset_bias

        # Request quantitative dictionary slice from underlying macro calculus engine
        metrics_dict = await calculate_asset_bias(asset_input)
        
        if not metrics_dict:
            raise ValueError(f"Macro Engine calculated returning dry null payload dictionary for target asset {asset_input}.")

        # Safely render your custom corporate template layout block
        report_html = build_html_report_panel(asset_input, metrics_dict)
        
        # Dispatch final design layout panel directly down the API pipe
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=report_html,
            parse_mode=ParseMode.HTML
        )
        
        # Remove lingering processing notification from the timeline chat log
        await status_message.delete()

    except Exception as e:
        # Clear print block outputs structural execution stack trace telemetry straight to Render logs
        print("\n=== !!! ADVANCED PANEL GENERATION CRASH STACKTRACE !!! ===")
        print(traceback.format_exc())
        print("===========================================================\n")
        
        logger.error(f"Advanced report composition workflow failed on token target asset '{asset_input}': {e}", exc_info=True)
        
        # Fallback design presentation vector 
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"❌ <b>Critical error generating advanced report output panels.</b>\n"
                 f"<i>The underlying structure analysis pipeline threw an internal formatting validation fault. Check application logging.</i>",
            parse_mode=ParseMode.HTML
        )

# ------------------------------------------------------------
# Global Application Core Initializer 
# ------------------------------------------------------------
token = os.getenv("TELEGRAM_TOKEN")
if not token:
    logger.critical("TELEGRAM_TOKEN configuration parameter missing entirely within environment variable configs.")
    raise ValueError("Missing TELEGRAM_TOKEN environment assignment config settings values.")

# Build global instance infrastructure state layers mapping
application = Application.builder().token(token).build()

# Wire logic execution handlers to application core routing
application.add_handler(CommandHandler("start", start_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_bias_request))
