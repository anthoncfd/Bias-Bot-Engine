import httpx
from telegram import Update
from telegram.ext import ContextTypes
from app.logger import logger
from app.services.market_data import MarketDataService

# Initialize our enterprise data broker layer
market_service = MarketDataService()

async def process_and_send_report(update: Update, symbol: str, display_name: str):
    """Core controller runner that handles the execution lifecycle of asset report queries."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    logger.info(f"👤 User {user_id} triggered macro query execution for vector: {display_name} [{symbol}]")
    
    # Send non-blocking typing indicator to user interface
    await update.message.reply_chat_action(action="typing")
    
    try:
        # Route query straight to our hybrid ingestion and math engine assembly
        report_output = await market_service.get_asset_report(symbol, display_name)
        
        # Dispatch final synchronized statistical layout back to the Telegram channel
        await update.message.reply_text(
            text=report_output,
            parse_mode="Markdown"
        )
        logger.info(f"✅ Telemetry compilation successfully transmitted for {display_name} to Chat ID: {chat_id}")
        
    except Exception as err:
        logger.error(f"❌ Controller layer failure executing report compilation for {symbol}: {err}", exc_info=True)
        await update.message.reply_text(
            text=f"❌ **System Execution Fault:** Infrastructure failed to process token matrix tracking for `{display_name}`."
        )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 💱 FOREX ASSET ROUTING HANDLERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def eurusd_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes real-time deviations and Monte Carlo drift vectors for EUR/USD."""
    await process_and_send_report(update, "EURUSD", "EURUSD")

async def gbpusd_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes real-time deviations and Monte Carlo drift vectors for GBP/USD."""
    await process_and_send_report(update, "GBPUSD", "GBPUSD")

async def gbpjpy_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes real-time deviations and Monte Carlo drift vectors for British Pound vs JPY."""
    await process_and_send_report(update, "GBPJPY", "GBPJPY")

async def usdcad_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes real-time deviations and Monte Carlo drift vectors for US Dollar vs Canadian Dollar."""
    await process_and_send_report(update, "USDCAD", "USDCAD")

async def usdchf_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes real-time deviations and Monte Carlo drift vectors for US Dollar vs Swiss Franc."""
    await process_and_send_report(update, "USDCHF", "USDCHF")

async def audusd_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes real-time deviations and Monte Carlo drift vectors for Australian Dollar vs US Dollar."""
    await process_and_send_report(update, "AUDUSD", "AUDUSD")

async def eurjpy_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes real-time deviations and Monte Carlo drift vectors for Euro vs Japanese Yen."""
    await process_and_send_report(update, "EURJPY", "EURJPY")

async def eurgbp_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes real-time deviations and Monte Carlo drift vectors for Euro vs British Pound."""
    await process_and_send_report(update, "EURGBP", "EURGBP")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📈 STOCK INDEX FUTURES ROUTING HANDLERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def us30_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes real-time deviations and Monte Carlo drift vectors for Dow Jones Mini Futures."""
    await process_and_send_report(update, "YM=F", "US30 (Dow Jones)")

async def nas100_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes real-time deviations and Monte Carlo drift vectors for Nasdaq 100 E-mini Futures."""
    await process_and_send_report(update, "NQ=F", "NAS100 (Nasdaq)")

async def jp225_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes real-time deviations and Monte Carlo drift vectors for Nikkei 225 Futures Mirror."""
    await process_and_send_report(update, "NKD=F", "JP225 (Nikkei)")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🪙 CRYPTOCURRENCY SPOT ROUTING HANDLERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def btcusd_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes real-time deviations and Monte Carlo drift vectors for Bitcoin Spot."""
    await process_and_send_report(update, "BTCUSD", "BTCUSD")

async def ethusd_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes real-time deviations and Monte Carlo drift vectors for Ethereum Spot."""
    await process_and_send_report(update, "ETHUSD", "ETHUSD")

async def bnbusd_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes real-time deviations and Monte Carlo drift vectors for Binance Coin Spot."""
    await process_and_send_report(update, "BNBUSD", "BNBUSD")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ⚙️ GLOBAL UTILITY COMMAND HANDLERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generates the main onboarding structural command directory for the interface."""
    welcome_msg = (
        "🏛️ **MACRO BIAS PRO ENGINE ONLINE**\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "Welcome to your institutional systematic data engine. "
        "Query the commands below to pull live deviations alongside 2,000-path "
        "vectorized Geometric Brownian Motion session estimates.\n\n"
        "💱 **Forex Command Matrix**\n"
        " └ /eurusd, /gbpusd, /gbpjpy\n"
        " └ /usdcad, /usdchf, /audusd\n"
        " └ /eurjpy, /eurgbp\n\n"
        "📈 **Indices Command Matrix**\n"
        " └ /us30 - Dow Jones Mini Futures\n"
        " └ /nas100 - Nasdaq 100 E-mini\n"
        " └ /jp225 - Nikkei 225 Mirror\n\n"
        "🪙 **Crypto Command Matrix**\n"
        " └ /btcusd, /ethusd, /bnbusd\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "💡 *Systems status: Operating with active Supabase local database caching layer.*"
    )
    await update.message.reply_text(text=welcome_msg, parse_mode="Markdown")
