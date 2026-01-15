import argparse
import pandas as pd
from data_fetcher.upbit_api import UpbitAPI
from backtester.backtest_engine import BacktestEngine
from strategy.signal import SignalGenerator
from config.settings import get_logger, TARGET_COIN

logger = get_logger("Optimizer")

def optimize_rsi(market, days=365):
    # 1. Fetch Data Once
    api = UpbitAPI()
    df = api.get_ohlcv(market=market, interval="minute60", days=days)
    
    if df.empty:
        logger.error("No data fetched for optimization.")
        return

    logger.info(f"Data fetched: {len(df)} rows")

    results = []
    
    # 2. Iterate RSI thresholds
    # Range: 20 to 50, step 2
    for rsi_val in range(20, 51, 2):
        logger.info(f"Testing RSI Oversold: {rsi_val}")
        
        signal_gen = SignalGenerator(rsi_oversold=rsi_val)
        engine = BacktestEngine(df.copy(), signal_generator=signal_gen)
        
        # Suppress writing files for each run
        result = engine.run()
        
        results.append({
            'rsi_oversold': rsi_val,
            'return_pct': result['return_pct'],
            'total_trades': result['total_trades'],
            'final_balance': result['final_balance']
        })

    # 3. Sort and Display Results
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values(by='return_pct', ascending=False)
    
    print("\n--- Optimization Results ---")
    print(results_df.to_string(index=False))
    
    best_result = results_df.iloc[0]
    print("\nBest Parameter:")
    print(best_result)
    
    # Save to file
    results_df.to_csv(f"optimization_results_{market}.csv", index=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Optimize RSI Threshold")
    parser.add_argument("--market", type=str, default=TARGET_COIN, help="Market to optimize (e.g., KRW-BTC)")
    parser.add_argument("--days", type=int, default=365, help="Days of history to backtest")
    
    args = parser.parse_args()
    
    optimize_rsi(args.market, args.days)
