import pandas as pd
from strategy.signal import SignalGenerator
from config.settings import STOP_LOSS_PCT, TAKE_PROFIT_PCT, MAX_HOLD_DAYS, MIN_PROFIT_PCT, TRADE_FEE_RATE, SLIPPAGE_RATE, ATR_K, RISK_PER_TRADE_PCT, MAX_CONSECUTIVE_LOSSES, COOLDOWN_CANDLES
import datetime
import logging

logger = logging.getLogger("BacktestEngine")

class BacktestEngine:
    def __init__(self, df, initial_capital=1000000, signal_generator=None, 
                 stop_loss_pct=STOP_LOSS_PCT, take_profit_pct=TAKE_PROFIT_PCT, 
                 max_hold_days=MAX_HOLD_DAYS, min_profit_pct=MIN_PROFIT_PCT):
        self.df = df
        self.initial_capital = initial_capital
        self.balance = initial_capital
        self.signal_generator = signal_generator if signal_generator else SignalGenerator()
        self.trades = []
        self.position = None # { 'entry_price': float, 'quantity': float, 'entry_time': datetime }
        
        # Risk Management Params (Dynamic for optimization)
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.max_hold_days = max_hold_days
        self.min_profit_pct = min_profit_pct
        
        # Validation checks
        if self.df is None or self.df.empty:
            logger.warning("Backtest initialized with empty dataframe")

    def run(self):
        """
        Run the backtest simulation (Strategy V2)
        """
        # 1. Process Indicators
        self.df = self.signal_generator.process(self.df)
        
        # State Variables
        consecutive_losses = 0
        cooldown_until = None
        
        # 2. Iterate through candles
        for index, row in self.df.iterrows():
            # Skip if indicators are NaN (start of data)
            if pd.isna(row['rsi']) or pd.isna(row['atr']):
                continue
                
            current_price = row['close']
            current_time = row['datetime']
            
            # --- Sell Logic (Check existing position) ---
            if self.position:
                entry_price = self.position['entry_price']
                entry_time = self.position['entry_time']
                quantity = self.position['quantity']
                atr_at_entry = self.position['atr']
                highest_price = self.position['highest_price']
                
                # Update Highest Price for Trailing Stop
                if current_price > highest_price:
                    highest_price = current_price
                    self.position['highest_price'] = highest_price

                # Calculate Stops
                # Note: atr_at_entry is fixed at entry.
                # Stop Loss = Entry - (ATR * K)
                # Trailing = Highest - (ATR * K)
                
                stop_loss_price = entry_price - (atr_at_entry * ATR_K)
                trailing_stop_price = highest_price - (atr_at_entry * ATR_K)
                
                sell_reason = None
                
                # PnL Pct (for logging/analysis/min_profit checks if needed - V2 relies on ATR)
                pnl_pct = (current_price - entry_price) / entry_price * 100
                
                # Check Exits
                if current_price <= stop_loss_price:
                    sell_reason = "Stop Loss"
                elif current_price <= trailing_stop_price:
                    sell_reason = "Trailing Stop"
                
                if sell_reason:
                    # Execute Sell
                    execution_price = current_price * (1 - SLIPPAGE_RATE)
                    sell_amount = quantity * execution_price
                    fee = sell_amount * TRADE_FEE_RATE
                    self.balance += (sell_amount - fee)
                    
                    real_pnl_amount = (sell_amount - fee) - (quantity * entry_price) # Approx cost basis
                    
                    # Update Cooldown State
                    if sell_reason == "Stop Loss":
                        consecutive_losses += 1
                        if consecutive_losses >= MAX_CONSECUTIVE_LOSSES:
                             # Activate Cooldown
                             # 5 Candles from NOW. 
                             # Assuming row['datetime'] is hourly close or open? 
                             # If hourly data, +5 hours.
                             cooldown_until = current_time + datetime.timedelta(hours=COOLDOWN_CANDLES)
                    else:
                        consecutive_losses = 0

                    self.trades.append({
                        'type': 'sell',
                        'time': current_time,
                        'price': current_price,
                        'execution_price': execution_price,
                        'quantity': quantity,
                        'reason': sell_reason,
                        'pnl_pct': pnl_pct, 
                        'real_pnl_amount': real_pnl_amount,
                        'fee': fee,
                        'slippage_cost': (current_price - execution_price) * quantity,
                        'balance': self.balance
                    })
                    self.position = None
                    continue 

            # --- Buy Logic ---
            if not self.position:
                # Check Cooldown
                if cooldown_until:
                    if current_time < cooldown_until:
                        continue # Skip
                    else:
                        cooldown_until = None
                
                # Use Trend Following Signal
                if self.signal_generator.check_trend_following_buy_signal(row):
                    # Use Prev ATR for sizing (Rule 3.2.2: ATR = ATR[t-1])
                    # We added 'prev_atr' to DF in signal generator.
                    atr = row.get('prev_atr', row['atr']) # Fallback to current if prev not found
                    if pd.isna(atr) or atr == 0:
                         continue

                    # Position Sizing
                    # Risk Amount = Capital * risk_pct
                    # Size = Risk Amount / (ATR * K)
                    
                    capital = self.balance
                    risk_amount = capital * (RISK_PER_TRADE_PCT / 100)
                    stop_distance = atr * ATR_K
                    
                    if stop_distance == 0: continue
                        
                    target_qty = risk_amount / stop_distance
                    
                    # Ensure we don't buy more than we have cash for
                    # Max Qty = (Capital * 0.999) / Price
                    max_qty = (capital * 0.999) / (current_price * (1 + SLIPPAGE_RATE))
                    quantity = min(target_qty, max_qty)
                    
                    # Min Value Check (e.g. 5000 KRW)
                    if (quantity * current_price) < 5000:
                        continue

                    # Execute Buy
                    execution_price = current_price * (1 + SLIPPAGE_RATE)
                    cost = quantity * execution_price
                    fee = cost * TRADE_FEE_RATE
                    
                    self.balance -= (cost + fee)
                    
                    self.position = {
                        'entry_price': execution_price,
                        'quantity': quantity,
                        'entry_time': current_time,
                        'atr': atr, # Store entry ATR for fixed stop distance
                        'highest_price': execution_price
                    }
                    
                    self.trades.append({
                        'type': 'buy',
                        'time': current_time,
                        'price': current_price,
                        'execution_price': execution_price,
                        'quantity': quantity,
                        'fee': fee,
                        'slippage_cost': (execution_price - current_price) * quantity,
                        'balance': self.balance
                    })

        # End of Backtest: Force close position if open? 
        # Usually better to leave it open or mark as 'open' in report.
        # For simple PnL calc, we can value it at last price.
        final_balance = self.balance
        if self.position:
            last_price = self.df.iloc[-1]['close']
            quantity = self.position['quantity']
            value = quantity * last_price
            fee = value * TRADE_FEE_RATE
            final_balance += (value - fee)
            
        return {
            'initial_balance': self.initial_capital,
            'final_balance': final_balance,
            'return_pct': (final_balance - self.initial_capital) / self.initial_capital * 100,
            'trades': self.trades,
            'total_trades': len([t for t in self.trades if t['type'] == 'sell'])
        }

    def save_results(self, filename="backtest_results.csv"):
        trades_df = pd.DataFrame(self.trades)
        if not trades_df.empty:
            trades_df.to_csv(filename, index=False)
            logger.info(f"Backtest results saved to {filename}")
        else:
            logger.info("No trades executed.")
