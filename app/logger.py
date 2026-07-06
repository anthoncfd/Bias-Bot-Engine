import sys
from loguru import logger
from app.config import settings

# Clear default standard loguru handler configuration
logger.remove()

# Add structured terminal/console configuration
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
    level=settings.log_level,
    colorize=True
)

# Add production daily rotating file logger configuration
logger.add(
    settings.log_file,
    rotation="1 day",
    retention="7 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name} - {message}",
    level=settings.log_level,
    compression="zip"
)

__all__ = ["logger"]
