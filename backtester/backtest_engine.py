import pandas as pd
from strategy.signal import SignalGenerator
from config.settings import STOP_LOSS_PCT, TAKE_PROFIT_PCT, MAX_HOLD_DAYS, TRADE_FEE_RATE
import logging

logger = logging.getLogger("BacktestEngine")

class BacktestEngine:
    def __init__(self, df, initial_capital=1000000, signal_generator=None, 
                 stop_loss_pct=STOP_LOSS_PCT, take_profit_pct=TAKE_PROFIT_PCT, max_hold_days=MAX_HOLD_DAYS):
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
        
        # Validation checks
        if self.df is None or self.df.empty:
            logger.warning("Backtest initialized with empty dataframe")

    def run(self):
        """
        Run the backtest simulation
        """
        # 1. Process Indicators
        self.df = self.signal_generator.process(self.df)
        
        # 2. Iterate through candles
        for index, row in self.df.iterrows():
            # Skip if indicators are NaN (start of data)
            if pd.isna(row['rsi']) or pd.isna(row['macd']):
                continue
                
            current_price = row['close']
            current_time = row['datetime']
            
            # --- Sell Logic (Check existing position) ---
            if self.position:
                entry_price = self.position['entry_price']
                entry_time = self.position['entry_time']
                quantity = self.position['quantity']
                
                # Calculate PnL %
                # Current Value = quantity * current_price
                # Entry Value = quantity * entry_price
                # PnL % = (current_price - entry_price) / entry_price * 100
                pnl_pct = (current_price - entry_price) / entry_price * 100
                
                days_held = (current_time - entry_time).total_seconds() / (24 * 3600)
                
                sell_reason = None
                
                # 6.1 Stop Loss / Take Profit
                if pnl_pct <= -self.stop_loss_pct:
                    sell_reason = "Stop Loss"
                elif pnl_pct >= self.take_profit_pct:
                    sell_reason = "Take Profit"
                # 6.2 Max Hold Days
                elif days_held >= self.max_hold_days:
                    sell_reason = "Max Hold Days"
                
                if sell_reason:
                    # Execute Sell
                    sell_amount = quantity * current_price
                    fee = sell_amount * TRADE_FEE_RATE
                    self.balance += (sell_amount - fee)
                    
                    self.trades.append({
                        'type': 'sell',
                        'time': current_time,
                        'price': current_price,
                        'quantity': quantity,
                        'reason': sell_reason,
                        'pnl_pct': pnl_pct,
                        'pnl_amount': sell_amount - fee - (quantity * entry_price),
                        'balance': self.balance
                    })
                    self.position = None
                    continue # Cannot buy on the same candle we sold (simplification)

            # --- Buy Logic ---
            if not self.position:
                if self.signal_generator.check_buy_signal(row):
                    # Execute Buy
                    amount_to_invest = self.balance # Compound everything
                    fee = amount_to_invest * TRADE_FEE_RATE
                    net_investment = amount_to_invest - fee
                    
                    if net_investment > 0:
                        quantity = net_investment / current_price
                        self.balance = 0 # All in
                        
                        self.position = {
                            'entry_price': current_price,
                            'quantity': quantity,
                            'entry_time': current_time
                        }
                        
                        self.trades.append({
                            'type': 'buy',
                            'time': current_time,
                            'price': current_price,
                            'quantity': quantity,
                            'fee': fee,
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
