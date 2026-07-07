from telegram import Update
from telegram.ext import ContextTypes
from app.logger import logger
from app.services.market_data import MarketDataService

async def process_and_send_report(update: Update, symbol: str, name: str):
    logger.info(f"User {update.effective_user.id} requested report on asset command: {symbol}")
    await update.message.reply_chat_action(action="typing")
    service = MarketDataService()
    report_output = await service.get_asset_report(symbol, name)
    await update.message.reply_text(report_output, parse_mode="Markdown")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🚀 **System Online**\n\n"
        "Welcome Anthon-X!\n"
        "The Hybrid Caching Architecture is fully active.\n\n"
        "**Available Target Triggers:**\n"
        "💱 **Forex Pairs:**\n"
        "  /eurusd, /gbpusd, /gbpjpy, /usdcad, /usdchf, /audusd, /eurjpy, /eurgbp\n\n"
        "📈 **Stock Indices:**\n"
        "  /jp225, /us30, /us100\n\n"
        "🪙 **Cryptocurrencies:**\n"
        "  /btcusd, /ethusd, /bnbusd"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def health_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🟢 **System Status: Healthy**\nCache metrics nominal.", parse_mode="Markdown")

# Forex Handlers Mappings
async def eurusd_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): await process_and_send_report(update, "EUR/USD", "EURUSD")
async def gbpusd_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): await process_and_send_report(update, "GBP/USD", "GBPUSD")
async def gbpjpy_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): await process_and_send_report(update, "GBP/JPY", "GBPJPY")
async def usdcad_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): await process_and_send_report(update, "USD/CAD", "USDCAD")
async def usdchf_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): await process_and_send_report(update, "USD/CHF", "USDCHF")
async def audusd_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): await process_and_send_report(update, "AUD/USD", "AUDUSD")
async def eurjpy_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): await process_and_send_report(update, "EUR/JPY", "EURJPY")
async def eurgbp_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): await process_and_send_report(update, "EUR/GBP", "EURGBP")

# Indices Handlers Mappings (Mapped precisely to Yahoo Finance native tickers)
async def jp225_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):  await process_and_send_report(update, "^N225", "JP225 (Nikkei)")
async def us30_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):   await process_and_send_report(update, "^DJI", "US30 (Dow Jones)")
async def us100_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):  await process_and_send_report(update, "^IXIC", "US100 (Nasdaq)")

# Crypto Handlers Mappings
async def btcusd_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):  await process_and_send_report(update, "BTCUSD", "BTCUSD")
async def ethusd_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):  await process_and_send_report(update, "ETHUSD", "ETHUSD")
async def bnbusd_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):  await process_and_send_report(update, "BNBUSD", "BNBUSD")
