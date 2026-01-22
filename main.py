import time
import datetime
import schedule
from config.logging_config import setup_logging, get_logger
from config.settings import TARGET_COIN, RSI_OVERSOLD, MOCK_TRADING
from data_fetcher.upbit_api import UpbitAPI
from data_fetcher.mock_upbit_api import MockUpbitAPI
from strategy.signal import SignalGenerator
from trade.trader import Trader
from utils.telegram_notifier import send_message

setup_logging()
logger = get_logger("Main")

def run_trading_logic(trader, api, signal_gen):
    try:
        logger.info("Running trading logic...")
        
        # 1. Fetch Data
        # We need enough data for indicators (RSI 14 + MACD 26 + extra for smoothing)
        # 200 candles is sufficient.
        df = api.get_ohlcv(market=TARGET_COIN, interval="minute60", days=10) # 10 days ~= 240 hours
        
        if df.empty:
            logger.error("Failed to fetch data.")
            return

        # 2. Calculate Signals
        df = signal_gen.process(df)
        last_row = df.iloc[-1]
        
        current_price = last_row['close']
        
        # Log status
        logger.info(f"Price: {current_price}, RSI: {last_row['rsi']:.2f}, MACD: {last_row['macd']:.2f}")

        # 3. Monitor Existing Position (StopLoss/TakeProfit)
        # This checks if we need to sell due to risk management
        if trader.get_market_state():
            trader.monitor_position(current_price)
        
        # 4. Check Buy Signal
        # Only buy if not in position (and position wasn't just closed above)
        if not trader.get_market_state():
            if signal_gen.check_buy_signal(last_row):
                logger.info("Buy Signal Detected!")
                send_message(f"🚀 Buy Signal Detected!\nRSI: {last_row['rsi']:.2f}\nMACD: {last_row['macd']:.2f}")
                trader.buy_market()
            else:
                logger.info("No Buy Signal.")

    except Exception as e:
        logger.error(f"Error in trading logic: {e}", exc_info=True)
        send_message(f"⚠️ Error in Bot: {e}")

def main():
    logger.info(f"Starting Coin Trading Bot... Mode: {'MOCK' if MOCK_TRADING else 'REAL'}")
    send_message(f"🤖 Coin Trading Bot Started ({'MOCK' if MOCK_TRADING else 'REAL'})")

    if MOCK_TRADING:
        api = MockUpbitAPI()
    else:
        api = UpbitAPI()
    # Note: RSI_OVERSOLD should be updated based on Optimization results!
    # Ideally, load from a dynamic config or arguments. Defaulting to settings.py value.
    signal_gen = SignalGenerator(rsi_oversold=RSI_OVERSOLD) # 30 default
    trader = Trader()

    # Schedule: Run every 1 hour
    # We want to run at the start of the hour ideally. 
    # schedule.every().hour.at(":01").do(...)
    schedule.every().hour.at(":01").do(run_trading_logic, trader, api, signal_gen)
    
    # Also run immediately on startup to check status
    run_trading_logic(trader, api, signal_gen)

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()
