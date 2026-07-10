import re
from typing import Dict, Any
from telegram import Update
from telegram.ext import ContextTypes
from app.logger import logger
from app.services.market_data import MarketDataService

# 🏛️ CENTRAL SYSTEM ASSET REGISTRY
SUPPORTED_ASSETS: Dict[str, str] = {
    "EURUSD": "EUR/USD",
    "GBPUSD": "GBP/USD",
    "GBPJPY": "GBP/JPY",
    "USDCAD": "USD/CAD",
    "USDCHF": "USD/CHF",
    "AUDUSD": "AUD/USD",
    "EURJPY": "EUR/JPY",
    "EURGBP": "EUR/GBP",
    "YM=F": "US30 (Dow Jones)",
    "NQ=F": "NAS100 (Nasdaq)",
    "NKD=F": "JP225 (Nikkei)",
    "BTCUSD": "BTCUSD",
    "ETHUSD": "ETHUSD",
    "BNBUSD": "BNBUSD"
}

# 🧠 INTERACTIVE NICKNAME ALIAS DICTIONARY
ASSET_ALIASES: Dict[str, str] = {
    "BITCOIN": "BTCUSD",
    "BTC": "BTCUSD",
    "ETHEREUM": "ETHUSD",
    "ETH": "ETHUSD",
    "BNB": "BNBUSD",
    "NASDAQ": "NQ=F",
    "NAS100": "NQ=F",
    "NAS": "NQ=F",
    "NIKKEI": "NKD=F",
    "JP225": "NKD=F",
    "DOW": "YM=F",
    "DOWJONES": "YM=F",
    "US30": "YM=F"
}

def normalize_user_input(raw_text: str) -> str:
    """Cleans up raw text inputs, strips punctuation, normalizes symbols,
    and cross-references aliases to return a verified system token string.
    """
    if not raw_text:
        return ""
    clean_text = raw_text.replace("/", "").strip().upper()
    clean_text = clean_text.split()[0] if clean_text else ""
    if clean_text in ASSET_ALIASES:
        return ASSET_ALIASES[clean_text]
    return clean_text

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generates the main onboarding structural command directory for the interface."""
    welcome_msg = (
        "🏛️ **MACRO BIAS PRO ENGINE ONLINE**\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "Welcome to your institutional systematic data engine. "
        "Query the assets below to pull live deviations alongside 2,000-path "
        "vectorized Geometric Brownian Motion session estimates.\n\n"
        "💱 **Forex Assets**\n"
        " └ eurusd, gbpusd, gbpjpy\n"
        " └ usdcad, usdchf, audusd\n"
        " └ eurjpy, eurgbp\n\n"
        "📈 **Indices Assets**\n"
        " └ us30 - Dow Jones Mini Futures\n"
        " └ nas100 - Nasdaq 100 E-mini\n"
        " └ jp225 - Nikkei 225 Mirror\n\n"
        "🪙 **Crypto Assets**\n"
        " └ btcusd, ethusd, bnbusd\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "💡 _Tip: You can use slashes or type in plain text! Simply sending 'btc' or 'eurusd' works perfectly._"
    )
    await update.message.reply_text(text=welcome_msg, parse_mode="Markdown")

async def handle_market_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Unified dynamic controller that processes commands and plain text inputs,
    running validation checks before passing queries to the math engine.
    """
    if not update.message or not update.message.text:
        return

    raw_message = update.message.text
    
    # Bypass asset analytics processing if user invokes the onboarding root handler
    if raw_message.strip().startswith("/start"):
        await start_handler(update, context)
        return

    user = update.effective_user
    chat_id = update.effective_chat.id

    logger.info(f"👤 User {user.id if user else 'Unknown'} dispatched text vector: '{raw_message}'")

    try:
        target_symbol = normalize_user_input(raw_message)
        
        # 🛡️ VALIDATION BOUNDARY GUARD
        if target_symbol not in SUPPORTED_ASSETS:
            logger.warning(f"⚠️ Validation Fault: Normalized token '{target_symbol}' matches no registered track rows.")
            help_msg = (
                "🔍 **Unsupported Ticker Vector**\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "The engine could not resolve your input. Please request a supported asset from our registry:\n\n"
                "💱 **Forex Pairs:**\n"
                "• `eurusd` | `gbpusd` | `gbpjpy`\n"
                "• `usdcad` | `usdchf` | `audusd`\n\n"
                "📊 **Macro Indexes & Futures:**\n"
                "• `nas100` (Nasdaq) | `jp225` (Nikkei) | `us30` (Dow Jones)\n\n"
                "🪙 **Digital Assets:**\n"
                "• `btc` (Bitcoin) | `eth` (Ethereum) | `bnb` (BNB Coin)\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "💡 _Tip: Slashes are completely optional!_"
            )
            await update.message.reply_text(text=help_msg, parse_mode="Markdown")
            return

        display_name = SUPPORTED_ASSETS[target_symbol]
        
        # Send interactive typing feedback to user interface
        await update.message.reply_chat_action(action="typing")
        
        status_node = await update.message.reply_text(
            text=f"📥 **Ingesting Time-Series Grid for {display_name}...**", 
            parse_mode="Markdown"
        )
        
        market_service = MarketDataService()
        report_markup = await market_service.get_asset_report(target_symbol, display_name)
        
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=status_node.message_id,
            text=report_markup,
            parse_mode="Markdown"
        )
        logger.info(f"✅ Telemetry compilation successfully transmitted for {target_symbol} to Chat ID: {chat_id}")

    except Exception as fatal_err:
        logger.critical(f"Unhandled exception caught inside message routing pipeline: {fatal_err}", exc_info=True)
        fallback_error = "❌ **Infrastructure Timeout:** The processing node encountered an error. Please try again in a moment."
        await update.message.reply_text(text=fallback_error, parse_mode="Markdown")
