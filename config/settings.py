import os
from dotenv import load_dotenv

load_dotenv()

# Upbit API Keys
ACCESS_KEY = os.getenv("UPBIT_ACCESS_KEY")
SECRET_KEY = os.getenv("UPBIT_SECRET_KEY")

# Trading Mode
MOCK_TRADING = True
TRADING_MODE_LABEL = "모의거래" if MOCK_TRADING else "실거래"

# Trading Parameters
TARGET_COIN = "KRW-BTC"  # Default, can be overridden
TICKER_INTERVAL = "minute60"  # 1 hour
RSI_PERIOD = 14
RSI_OVERSOLD = 44  # Default, optimization will override
RSI_OVERBOUGHT = 70

# Optimization Config
RSI_OPT_MIN = 20
RSI_OPT_MAX = 56
RSI_OPT_STEP = 2

MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# Strategy Risk Management
STOP_LOSS_PCT = 1.0  # 3.0%
TAKE_PROFIT_PCT = 10.0  # 35.0%
MIN_PROFIT_PCT = 4.0 # Minimum profit to secure at Max Hold
MAX_HOLD_DAYS = 10

# Trading Amount
INITIAL_CAPITAL = 1000000  # 1 Million KRW
TRADE_FEE_RATE = 0.0005  # 0.05% Upbit Fee
SLIPPAGE_RATE = 0.0005 # 0.05% Estimated Slippage (Conservative)

# Trend Strategy & Risk Management
ATR_PERIOD = 14
ATR_K = 1.5
RISK_PER_TRADE_PCT = 1.0  # Risk 1.0% of Total Capital per trade

EMA_FAST = 9
EMA_SLOW = 20

BB_PERIOD = 20
BB_STD = 2.0
BB_WIDTH_THRESHOLD = 0.1 # Example threshold for volatility check if needed

ATR_VOLATILITY_THRESHOLD = 1.5 # ATR Filter: ATR(t) / ATR(t-5) > 1.5

MAX_CONSECUTIVE_LOSSES = 2
COOLDOWN_CANDLES = 5

# Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

TELEGRAM_PREFIX = f"[Upbit Coin Trading Bot][{TRADING_MODE_LABEL}][{TARGET_COIN}]"
