import argparse
import pandas as pd
import itertools
from data_fetcher.upbit_api import UpbitAPI
from backtester.backtest_engine import BacktestEngine
from strategy.signal import SignalGenerator
from config.logging_config import get_logger
from config.settings import TARGET_COIN, RSI_OVERSOLD, STOP_LOSS_PCT, TAKE_PROFIT_PCT, MAX_HOLD_DAYS

logger = get_logger("Optimizer")

def fetch_data(market, days):
    api = UpbitAPI()
    df = api.get_ohlcv(market=market, interval="minute60", days=days)
    if df.empty:
        logger.error("No data fetched for optimization.")
        return None
    logger.info(f"Data fetched: {len(df)} rows")
    return df

def optimize_rsi(df):
    results = []
    logger.info("Starting RSI Optimization (Range: 20-50)...")
    
    for rsi_val in range(20, 51, 2):
        signal_gen = SignalGenerator(rsi_oversold=rsi_val)
        # Use default Risk Params
        engine = BacktestEngine(df.copy(), signal_generator=signal_gen)
        
        result = engine.run()
        
        results.append({
            'rsi_oversold': rsi_val,
            'return_pct': result['return_pct'],
            'total_trades': result['total_trades'],
            'final_balance': result['final_balance']
        })
    return pd.DataFrame(results)

def optimize_pnl_maxhold(df):
    results = []
    logger.info("Starting PnL & MaxHold Optimization...")
    
    # Ranges
    stop_loss_range = [1.0, 2.0, 3.0, 4.0, 5.0] # 5 steps
    take_profit_range = [10.0, 20.0, 30.0, 40.0, 50.0] # 5 steps
    max_hold_range = [3, 5, 7, 10] # 4 steps
    # Total combinations: 5 * 5 * 4 = 100 runs
    
    combinations = list(itertools.product(stop_loss_range, take_profit_range, max_hold_range))
    
    for sl, tp, mh in combinations:
        # Use default RSI (or currently configured one)
        signal_gen = SignalGenerator(rsi_oversold=RSI_OVERSOLD)
        
        engine = BacktestEngine(
            df.copy(), 
            signal_generator=signal_gen,
            stop_loss_pct=sl,
            take_profit_pct=tp,
            max_hold_days=mh
        )
        
        result = engine.run()
        
        results.append({
            'stop_loss': sl,
            'take_profit': tp,
            'max_hold': mh,
            'return_pct': result['return_pct'],
            'total_trades': result['total_trades'],
            'final_balance': result['final_balance']
        })
        
    return pd.DataFrame(results)

def main():
    parser = argparse.ArgumentParser(description="Coin Bot Optimization")
    parser.add_argument("--mode", type=str, required=True, choices=['rsi', 'pnl'], help="Optimization mode: 'rsi' or 'pnl'")
    parser.add_argument("--market", type=str, default=TARGET_COIN, help="Market to optimize (e.g., KRW-BTC)")
    parser.add_argument("--days", type=int, default=365, help="Days of history to backtest")
    
    args = parser.parse_args()
    
    df = fetch_data(args.market, args.days)
    if df is None:
        return

    if args.mode == 'rsi':
        results_df = optimize_rsi(df)
        sort_cols = ['return_pct']
    elif args.mode == 'pnl':
        results_df = optimize_pnl_maxhold(df)
        sort_cols = ['return_pct']

    if not results_df.empty:
        results_df = results_df.sort_values(by=sort_cols, ascending=False)
        
        print(f"\n--- Optimization Results ({args.mode.upper()}) ---")
        print(results_df.head(10).to_string(index=False)) # Show top 10
        
        best_result = results_df.iloc[0]
        print("\nBest Parameters:")
        print(best_result)
        
        output_file = f"optimization_results_{args.mode}_{args.market}.csv"
        results_df.to_csv(output_file, index=False)
        print(f"\nResults saved to {output_file}")
    else:
        print("No results found.")

if __name__ == "__main__":
    main()
