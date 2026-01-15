import pandas as pd
from strategy.signal import SignalGenerator
from config.settings import STOP_LOSS_PCT, TAKE_PROFIT_PCT, MAX_HOLD_DAYS, TRADE_FEE_RATE, SLIPPAGE_RATE
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
                    # Sell Price = Market Price * (1 - Slippage)
                    execution_price = current_price * (1 - SLIPPAGE_RATE)
                    sell_amount = quantity * execution_price
                    fee = sell_amount * TRADE_FEE_RATE
                    self.balance += (sell_amount - fee)
                    
                    # Calculate real PnL based on execution price and net of all fees
                    # Buy Cost = Quantity * Entry Price + Buy Fee (already deducted from balance)
                    # Sell Proceeds = Quantity * Execution Price - Sell Fee
                    # But self.trades already tracked fee for buy.
                    # Simplest PnL: Final Proceeds - Cost Basis
                    
                    cost_basis = quantity * entry_price # Raw cost
                    # Note: We should probably track total cost including buy fee in 'position' for accurate PnL.
                    # For now, pnl_amount = (Sell Amount - Sell Fee) - (Buy Amount + Buy Fee?)
                    # Let's approximate:
                    # Entry was: self.balance -= (amount_to_invest) -> quantity * price + fee
                    
                    # Correct PnL calculation:
                    # Net Profit = (Sell Amount - Sell Fee) - (Original Investment)
                    # Where Original Investment = Quantity * Entry Price + Entry Fee (But Entry Fee reduced our quantity if we did quantity = (invest - fee)/price)
                    # Actually logic was: quantity = (invest - fee) / price.
                    # So Cost = invest - fee. 
                    # Wait, 'invest' is the amount removed from balance.
                    
                    self.trades.append({
                        'type': 'sell',
                        'time': current_time,
                        'price': current_price,
                        'execution_price': execution_price,
                        'quantity': quantity,
                        'reason': sell_reason,
                        'pnl_pct': pnl_pct, # Strategy/Signal PnL (on raw price)
                        'real_pnl_amount': (sell_amount - fee) - (quantity * entry_price), # Roughly
                        'fee': fee,
                        'slippage_cost': (current_price - execution_price) * quantity,
                        'balance': self.balance
                    })
                    self.position = None
                    continue # Cannot buy on the same candle we sold (simplification)

            # --- Buy Logic ---
            if not self.position:
                if self.signal_generator.check_buy_signal(row):
                    # Execute Buy
                    amount_to_invest = self.balance # Compound everything
                    
                    # Fee is deducted from investment amount usually or charged on top.
                    # Upbit KRW market: Fee is deducted from KRW amount? Or we buy X coin and pay fee in KRW?
                    # Generally: we pay fee from KRW.
                    # Net Buy Amount = Invest - Fee
                    # Fee = Invest * Fee Rate (approx, strictly it's Amount / (1+Rate) * Rate)
                    # Let's stick to simple model: Fee is taken from capital.
                    
                    fee = amount_to_invest * TRADE_FEE_RATE
                    net_capital = amount_to_invest - fee
                    
                    # Buy Execution Price = Market Price * (1 + Slippage)
                    execution_price = current_price * (1 + SLIPPAGE_RATE)
                    
                    if net_capital > 0:
                        quantity = net_capital / execution_price
                        self.balance = 0 # All in
                        
                        self.position = {
                            'entry_price': execution_price, # We track execution price as entry for PnL
                            'quantity': quantity,
                            'entry_time': current_time
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
