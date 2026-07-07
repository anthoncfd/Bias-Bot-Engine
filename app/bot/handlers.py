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
        "The Market Intelligence Engine is alive and ready.\n\n"
        "**Available Target Triggers:**\n"
        "💱 **Forex Pairs:**\n"
        "  /eurusd, /gbpusd, /gbpjpy, /usdcad, /usdchf, /audusd, /eurjpy, /eurgbp\n\n"
        "📈 **Stock Indices:**\n"
        "  /jp225, /us30, /us100\n\n"
        "🪙 **Cryptocurrencies:**\n"
        "  /btcusd, /ethusd, /bnbusd\n\n"
        "⚙️ **System Maintenance:** /health"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def health_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🟢 **System Core Status: Healthy**\nAll operational runtime loops functional.", parse_mode="Markdown")

# Target Forex Pairs Route Handling Setup
async def eurusd_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): await process_and_send_report(update, "EUR/USD", "EURUSD")
async def gbpusd_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): await process_and_send_report(update, "GBP/USD", "GBPUSD")
async def gbpjpy_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): await process_and_send_report(update, "GBP/JPY", "GBPJPY")
async def usdcad_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): await process_and_send_report(update, "USD/CAD", "USDCAD")
async def usdchf_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): await process_and_send_report(update, "USD/CHF", "USDCHF")
async def audusd_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): await process_and_send_report(update, "AUD/USD", "AUDUSD")
async def eurjpy_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): await process_and_send_report(update, "EUR/JPY", "EURJPY")
async def eurgbp_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): await process_and_send_report(update, "EUR/GBP", "EURGBP")

# Target Indices Route Handling Setup
async def jp225_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):  await process_and_send_report(update, "NI225", "Nikkei 225 (JP225)")
async def us30_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):   await process_and_send_report(update, "DJI", "Dow Jones 30 (US30)")
async def us100_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):  await process_and_send_report(update, "IXIC", "Nasdaq 100 (US100)")

# Target Crypto Route Handling Setup
async def btcusd_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):  await process_and_send_report(update, "BTC/USD", "BTCUSD")
async def ethusd_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):  await process_and_send_report(update, "ETH/USD", "ETHUSD")
async def bnbusd_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):  await process_and_send_report(update, "BNB/USD", "BNBUSD")
