import requests
from config.settings import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_PREFIX
from config.logging_config import get_logger

logger = get_logger("TelegramNotifier")

def send_message(message):
    """
    Send message to Telegram
    """
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram token or Chat ID not configured. Skipping notification.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': f"{TELEGRAM_PREFIX}\n{message}"
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to send telegram message: {e}")
