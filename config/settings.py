import os
from dotenv import load_dotenv

load_dotenv()

# Upbit API Keys
ACCESS_KEY = os.getenv("UPBIT_ACCESS_KEY")
SECRET_KEY = os.getenv("UPBIT_SECRET_KEY")

# Trading Mode
MOCK_TRADING = os.getenv("MOCK_TRADING", "True").lower() == "true"
TRADING_MODE_LABEL = "모의거래" if MOCK_TRADING else "실거래"

# Trading Parameters
TARGET_COIN = "KRW-BTC"  # Default, can be overridden
TICKER_INTERVAL = "minute60"  # 1 hour
RSI_PERIOD = 14
RSI_OVERSOLD = 30  # Default, optimization will override
RSI_OVERBOUGHT = 70

MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# Strategy Risk Management
STOP_LOSS_PCT = 3.0  # 3.0%
TAKE_PROFIT_PCT = 35.0  # 35.0%
MAX_HOLD_DAYS = 5

# Trading Amount
INITIAL_CAPITAL = 1000000  # 1 Million KRW
TRADE_FEE_RATE = 0.0005  # 0.05% Upbit Fee
SLIPPAGE_RATE = 0.0005 # 0.05% Estimated Slippage (Conservative)

# Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

TELEGRAM_PREFIX = f"[Upbit Coin Trading Bot][{TRADING_MODE_LABEL}][{TARGET_COIN}]"
