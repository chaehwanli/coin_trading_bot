import argparse
import pandas as pd
import itertools
from utils.data_loader import load_data
from backtester.backtest_engine import BacktestEngine
from strategy.signal import SignalGenerator
from config.logging_config import get_logger
from config.settings import TARGET_COIN, RSI_OVERSOLD, STOP_LOSS_PCT, TAKE_PROFIT_PCT, MAX_HOLD_DAYS

logger = get_logger("Optimizer")

def fetch_data(market, days):
    df = load_data(market, days)
    if df is None or df.empty:
        logger.error("No data loaded. Did you run 'python collect_data.py'?")
        return None
    logger.info(f"Data loaded: {len(df)} rows")
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

def optimize_pnl_maxhold(df, rsi_val=RSI_OVERSOLD):
    results = []
    logger.info(f"Starting PnL & MaxHold Optimization (Fixed RSI={rsi_val})...")
    
    # Ranges
    stop_loss_range = [1.0, 2.0, 3.0, 4.0, 5.0] # 5 steps
    take_profit_range = [10.0, 20.0, 30.0, 40.0, 50.0] # 5 steps
    max_hold_range = [3, 5, 7, 10] # 4 steps
    # Total combinations: 5 * 5 * 4 = 100 runs
    
    combinations = list(itertools.product(stop_loss_range, take_profit_range, max_hold_range))
    
    for sl, tp, mh in combinations:
        # Use provided RSI
        signal_gen = SignalGenerator(rsi_oversold=rsi_val)
        
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
    parser.add_argument("--rsi", type=float, default=RSI_OVERSOLD, help=f"RSI Oversold Threshold (default: {RSI_OVERSOLD})")
    
    args = parser.parse_args()
    
    df = fetch_data(args.market, args.days)
    if df is None:
        return

    if args.mode == 'rsi':
        results_df = optimize_rsi(df)
        sort_cols = ['return_pct']
    elif args.mode == 'pnl':
        # Pass the custom RSI value (or default)
        results_df = optimize_pnl_maxhold(df, rsi_val=args.rsi)
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
