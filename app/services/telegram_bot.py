import os
import logging
import traceback
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# Initialize premium structural execution logger
logger = logging.getLogger(__name__)

# ------------------------------------------------------------
# Premium Layout Generation Factory (HTML-Safe Conversion)
# ------------------------------------------------------------
def build_html_report_panel(asset: str, data: dict) -> str:
    """
    Compiles the signature Macro Bias Report layout using strict HTML tags.
    Gracefully scales layout formatting between stock indexes and precise currency matrices.
    """
    # Secure clean parameter extractions with fallback safe-fails
    bias = data.get("bias", "⚪ NEUTRAL")
    confidence = data.get("confidence", 50.0)
    regime = data.get("regime", "Compression Range (Liquidity Building)")
    live_price = data.get("live_price", 0.0)
    prev_close = data.get("prev_close", 0.0)
    sma_20 = data.get("sma_20", 0.0)
    momentum = data.get("momentum", data.get("z_score", 0.0))
    news = data.get("news", "• No critical structural updates found in the last 4 hours.")
    
    # Grab the dynamic direction-specific quote mapped by the backend macro engine
    quote = data.get("quote", '"Cash is an active position. If you don\'t have an edge, don\'t play." – Market Proverb')

    # Pull the 5-sentence context analysis computed via gemini-1.5-flash
    inference = data.get("macro_inference", data.get("inference", None))
    if not inference:
        inference = (
            f"The asset class {asset.upper()} exhibits significant consolidation within established structural boundaries. "
            "Market volatility metrics reflect an accumulation phase ahead of shifting macroeconomic timelines. "
            "Order flow is clustered around major volume profile nodes while high-impact data stabilizes. "
            "Patience remains paramount as risk matrices calibrate to incoming directional flow adjustments. "
            "Awarding clean invalidation triggers will confirm structural breakout intentions."
        )

    # Internal formatting helper to dynamically adjust precision scalars based on asset class pricing scales
    def format_price(val) -> str:
        try:
            float_val = float(val)
            if float_val == 0.0:
                return "0.00"
            return f"{float_val:,.4f}" if float_val < 10.0 else f"{float_val:,.2f}"
        except (ValueError, TypeError):
            return str(val)

    # Dynamic scalar representation of the current calculations pipeline
    conf_str = f"{confidence:.1f}%" if isinstance(confidence, (int, float)) else str(confidence)

    # Format momentum z-scores with formal polarity tracking sign indicators (+/-)
    try:
        mom_str = f"{float(momentum):+.2f}"
    except (ValueError, TypeError):
        mom_str = str(momentum)

    # TARGET CORPORATE PRESENTATION LAYOUT VECTOR
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
        f"🧠 <b>MACRO INFERENCE SUMMARY</b>\n"
        f"<i>{inference}</i>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏛️ <i><b>RISK INSIGHT:</b></i>\n"
        f"<i>{quote}</i>\n"
    )
    return html

# ------------------------------------------------------------
# Command & Message Event Route Handlers
# ------------------------------------------------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Welcomes operators and prints out standard usage parameters."""
    welcome_text = (
        "<b>SirAnthony Bias Engine Active</b> 🚀\n\n"
        "Send me any asset token symbol directly to instantly generate your institutional macro report panel.\n"
        "<i>Examples: EURUSD, GBPUSD, BTCUSD, US30, SPX, JP225</i>"
    )
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.HTML)

async def handle_bias_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Intercepts message text updates, processes underlying asset calculus matrices, and dispatches the HTML panel."""
    asset_input = update.message.text.strip().upper()
    
    if not asset_input:
        return

    # Instantly trigger live notification overlay keeping the workspace responsive
    status_message = await update.message.reply_text(
        f"⚡ Processing micro-structure momentum matrix profiles for <b>{asset_input}</b>...",
        parse_mode=ParseMode.HTML
    )

    try:
        # 🛡️ LAZY LOCAL IMPORT: Prevents initialization looping during container boot sequences
        from app.engines.macro_engine import calculate_asset_bias

        # Await dictionary mapping response from the backend computation layer
        metrics_dict = await calculate_asset_bias(asset_input)
        
        if not metrics_dict:
            raise ValueError(f"Macro Calculus Engine returned a dry payload structure dictionary for target symbol {asset_input}.")

        # Pass payload coordinates directly to the template parser module
        report_html = build_html_report_panel(asset_input, metrics_dict)
        
        # Ship final rendered typography down the Telegram network pipes
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=report_html,
            parse_mode=ParseMode.HTML
        )
        
        # Clean processing message status out of the timeline ledger
        await status_message.delete()

    except Exception as e:
        # Dump advanced diagnostics telemetry cleanly straight to server pipeline logs
        print("\n=== !!! ADVANCED PANEL GENERATION CRASH STACKTRACE !!! ===")
        print(traceback.format_exc())
        print("===========================================================\n")
        
        logger.error(f"Advanced report composition workflow failed on token target asset '{asset_input}': {e}", exc_info=True)
        
        # Graceful UI crash notification fallback
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

# Instantiate engine application runtime context layers
application = Application.builder().token(token).build()

# Direct incoming event traffic updates to designated logic targets
application.add_handler(CommandHandler("start", start_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_bias_request))
