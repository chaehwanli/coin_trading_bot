import argparse
import os
import pandas as pd
from data_fetcher.upbit_api import UpbitAPI
from config.logging_config import setup_logging, get_logger

setup_logging()
logger = get_logger("DataCollector")

DEFAULT_COINS = ["KRW-BTC", "KRW-ETH", "KRW-XRP", "KRW-SOL", "KRW-DOGE", "KRW-ADA"]

def collect_data(days, coins):
    api = UpbitAPI()
    data_dir = "data"
    
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        
    for market in coins:
        logger.info(f"Collecting data for {market} ({days} days)...")
        try:
            df = api.get_ohlcv(market=market, interval="minute60", days=days)
            if not df.empty:
                file_path = os.path.join(data_dir, f"{market}.csv")
                df.to_csv(file_path, index=False)
                logger.info(f"Saved {len(df)} rows to {file_path}")
            else:
                logger.warning(f"No data found for {market}")
        except Exception as e:
            logger.error(f"Failed to collect {market}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Collect market data from Upbit")
    parser.add_argument("--days", type=int, default=365, help="Days of history to fetch")
    parser.add_argument("--coins", type=str, help="Comma-separated list of markets (e.g. KRW-BTC,KRW-ETH)")
    
    args = parser.parse_args()
    
    if args.coins:
        coins = [c.strip() for c in args.coins.split(",")]
    else:
        coins = DEFAULT_COINS
        
    collect_data(args.days, coins)

if __name__ == "__main__":
    main()
