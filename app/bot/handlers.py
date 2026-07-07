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
    await process_and_send_report(update, "EUR/USD", "EURUSD")

async def gbpusd_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes real-time deviations and Monte Carlo drift vectors for GBP/USD."""
    await process_and_send_report(update, "GBP/USD", "GBPUSD")

async def gbpjpy_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes real-time deviations and Monte Carlo drift vectors for GBP/JPY."""
    await process_and_send_report(update, "GBP/JPY", "GBPJPY")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📈 STOCK INDEX FUTURES ROUTING HANDLERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def us30_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes real-time deviations and Monte Carlo drift vectors for Dow Jones Mini Futures."""
    # Matches mini futures 'YM=F' to align perfectly with retail CFD values (OANDA/Forex.com)
    await process_and_send_report(update, "YM=F", "US30 (Dow Jones)")

async def jp225_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes real-time deviations and Monte Carlo drift vectors for Nikkei 225 USD Futures."""
    # Matches highly liquid CME Nikkei futures 'NKD=F' to align with broker data streams
    await process_and_send_report(update, "NKD=F", "JP225 (Nikkei)")

async def nas100_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes real-time deviations and Monte Carlo drift vectors for Nasdaq 100 Futures."""
    # Maps directly to the high-volume E-mini Nasdaq 100 futures tracking anchor
    await process_and_send_report(update, "NQ=F", "NAS100 (Nasdaq)")

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
        " └ /eurusd - Euro vs US Dollar\n"
        " └ /gbpusd - British Pound vs US Dollar\n"
        " └ /gbpjpy - British Pound vs Japanese Yen\n\n"
        "📈 **Indices Command Matrix**\n"
        " └ /us30 - Dow Jones Industrial Mini Futures\n"
        " └ /nas100 - Nasdaq 100 E-mini Futures\n"
        " └ /jp225 - Nikkei 225 Futures Mirror\n\n"
        "🪙 **Crypto Command Matrix**\n"
        " └ /btcusd - Bitcoin Spot Index\n"
        " └ /ethusd - Ethereum Spot Index\n"
        " └ /bnbusd - Binance Coin Spot Index\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "💡 *Systems status: Operating with active Supabase local database caching layer.*"
    )
    await update.message.reply_text(text=welcome_msg, parse_mode="Markdown")
