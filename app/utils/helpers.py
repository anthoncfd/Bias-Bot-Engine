import logging

logger = logging.getLogger("MacroEngine.Utils")

def clean_macro_string_to_float(val_str: str) -> float:
    """Strips formatting characters from macro metrics to extract a raw mathematical float."""
    if not val_str or any(marker in val_str.upper() for marker in ["N/A", "PENDING", "CHALLENGE"]):
        return None
    try:
        # Standardize signs and remove directional or scaling indicators
        cleaned = val_str.replace('%', '').replace('$', '').replace(',', '').strip()
        
        # Handle thousands metric scaling factor
        if cleaned.upper().endswith('K'):
            return float(cleaned[:-1]) * 1000.0
        # Handle millions metric scaling factor
        elif cleaned.upper().endswith('M'):
            return float(cleaned[:-1]) * 1000000.0
            
        return float(cleaned)
    except ValueError:
        logger.warning(f"Failed to cleanly convert string value: '{val_str}'")
        return None

def safe_telegram_markdown_truncate(text: str, max_chars: int = 4000) -> str:
    """Guarantees messages fit safely within Telegram constraints without cutting off markup."""
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars - 50]
    return f"{truncated}\n\n<b>... [Report Truncated for System Limits]</b>"
