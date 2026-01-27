import argparse
import pandas as pd
from utils.data_loader import load_data
from backtester.backtest_engine import BacktestEngine
from strategy.signal import SignalGenerator
from config.logging_config import setup_logging, get_logger
from config.settings import (
    TARGET_COIN, RSI_OVERSOLD, 
    STOP_LOSS_PCT, TAKE_PROFIT_PCT, MAX_HOLD_DAYS
)

setup_logging()
logger = get_logger("Backtester")

def fetch_data(market, days):
    logger.info(f"Loading {days} days of data for {market}...")
    df = load_data(market, days)
    if df is None or df.empty:
        logger.error("No data loaded. Did you run 'python collect_data.py'?")
        return None
    logger.info(f"Loaded {len(df)} rows.")
    return df

def run_backtest(args):
    df = fetch_data(args.market, args.days)
    if df is None:
        return

    logger.info(f"Running Backtest: RSI<{args.rsi}")
    
    signal_gen = SignalGenerator(rsi_oversold=args.rsi)
    engine = BacktestEngine(
        df, 
        signal_generator=signal_gen
    )
    
    result = engine.run()
    
    print("\n" + "="*40)
    print(f" BACKTEST RESULTS ({args.market})")
    print("="*40)
    print(f"Period: {args.days} days")
    print(f"Initial Balance: {result['initial_balance']:,.0f} KRW")
    print(f"Final Balance:   {result['final_balance']:,.0f} KRW")
    print(f"Return:          {result['return_pct']:.2f}%")
    print(f"Total Trades:    {result['total_trades']}")
    print("-" * 40)
    
    engine.save_results(filename=f"backtest_details_{args.market}.csv")

def main():
    parser = argparse.ArgumentParser(description="Run a single backtest simulation.")
    
    parser.add_argument("--market", type=str, default=TARGET_COIN, help=f"Market (default: {TARGET_COIN})")
    parser.add_argument("--days", type=int, default=365, help="Days to backtest (default: 365)")
    
    parser.add_argument("--rsi", type=float, default=RSI_OVERSOLD, help=f"RSI Oversold Threshold (default: {RSI_OVERSOLD})")
    # Removed SL/TP/MaxHold args as they are now hardcoded in Strategy V2 settings or derived from ATR
    
    args = parser.parse_args()
    run_backtest(args)

if __name__ == "__main__":
    main()
