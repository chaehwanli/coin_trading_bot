import pandas as pd
from utils.data_loader import load_data
from backtester.backtest_engine import BacktestEngine
from strategy.signal import SignalGenerator
from config.logging_config import setup_logging, get_logger
from config.settings import (
    RSI_OVERSOLD, STOP_LOSS_PCT, TAKE_PROFIT_PCT, MAX_HOLD_DAYS
)

# Suppress logs for batch run to keep output clean
setup_logging()
logger = get_logger("BatchBacktester")
logger.setLevel("WARNING") 

COINS = [
    ("KRW-BTC", "Bitcoin"),
    ("KRW-ETH", "Ethereum"),
    ("KRW-XRP", "Ripple"),
    ("KRW-SOL", "Solana"),
    ("KRW-DOGE", "Dogecoin"),
    ("KRW-ADA", "Cardano")
]

def run_batch_backtest(days=365):
    results = []
    
    print("Loading data and running backtests...")
    
    for code, name in COINS:
        try:
            # Load Data
            df = load_data(code, days)
            if df is None or df.empty:
                print(f"Skipping {name} (No Data. Run collect_data.py)")
                continue
                
            # Run Backtest
            signal_gen = SignalGenerator(rsi_oversold=RSI_OVERSOLD)
            engine = BacktestEngine(
                df,
                signal_generator=signal_gen
            )
            result = engine.run()
            trades = result['trades']
            
            # metrics
            total_trades = result['total_trades']
            final_return = result['return_pct']
            
            wins = 0
            sl_count = 0
            tp_count = 0
            mh_win = 0
            mh_loss = 0
            total_fees = 0
            
            for t in trades:
                if t['type'] == 'sell':
                    total_fees += t['fee']
                    reason = t.get('reason', '')
                    
                    # Logic to count types
                    # Check real_pnl_amount > 0 for generic 'win' if needed, but request asks for categories
                    
                    if reason == 'Stop Loss':
                        sl_count += 1
                        # SL is typically a loss
                        
                    elif reason == 'Take Profit':
                        tp_count += 1
                        wins += 1 # TP is a win
                        
                    elif reason == 'Trailing Stop':
                        tp_count += 1 # Trailing Stop is essentially a winning exit (usually)
                        wins += 1 
                        
                    elif reason.startswith('Max Hold Days'):
                         # Legacy check, but keeping just in case
                        pnl = t.get('real_pnl_amount', 0)
                        if pnl > 0:
                            mh_win += 1
                            wins += 1
                        else:
                            mh_loss += 1
                            
                    else:
                        # Fallback for other sells?
                        pnl = t.get('real_pnl_amount', 0)
                        if pnl > 0: wins += 1
                
                elif t['type'] == 'buy':
                    total_fees += t['fee']

            results.append({
                'Code': code.replace("KRW-", ""), # Display Code
                'Name': name,
                'Return': final_return,
                'Trades': total_trades,
                'Win': wins,
                'SL': sl_count,
                'TS': tp_count, # Using TP column logic for TS in loop, let's rename or split.
                'TP': 0, # Strategy V2 has no fixed TP
                'MH(W)': mh_win,
                'MH(L)': mh_loss,
                'Fees': total_fees
            })
            
        except Exception as e:
            print(f"Error processing {name}: {e}")

    # Print Report
    print("\n" + "="*105)
    print(f"{'Code':<8} | {'Name':<15} | {'Return':<9} | {'Trades':<6} | {'Win':<4} | {'SL':<4} | {'TS':<4} | {'MH(W)':<5} | {'MH(L)':<5} | {'Fees':<7}")
    print("-" * 105)
    
    for r in results:
        print(f"{r['Code']:<8} | {r['Name']:<15} | {r['Return']:>8.2f}% | {r['Trades']:<6} | {r['Win']:<4} | {r['SL']:<4} | {r['TS']:<4} | {r['MH(W)']:<5} | {r['MH(L)']:<5} | {r['Fees']:<7.0f}")
    
    print("="*105)

if __name__ == "__main__":
    run_batch_backtest()
