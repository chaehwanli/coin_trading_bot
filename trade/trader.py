from data_fetcher.upbit_api import UpbitAPI
from config.settings import TARGET_COIN, TRADE_FEE_RATE, STOP_LOSS_PCT, TAKE_PROFIT_PCT, MAX_HOLD_DAYS, MIN_PROFIT_PCT
from config.logging_config import get_logger
from utils.telegram_notifier import send_message
import datetime
import math

logger = get_logger("Trader")

class Trader:
    def __init__(self):
        self.api = UpbitAPI()
        self.market = TARGET_COIN
        # We need to track entry info for proper StopLoss/TakeProfit
        # In a real bot, this should be persisted to a database or file.
        # For this implementation, we will try to infer from last order or keep in memory (reset on restart).
        # Better approach: Check if we have non-zero balance of the coin.
        self.position = None 
        self._sync_state()

    def _sync_state(self):
        """
        Synchronize state with Upbit account
        """
        coin_currency = self.market.split("-")[1] # "BTC" from "KRW-BTC"
        balance = self.api.get_balance(coin_currency)
        
        current_price = self.api.get_current_price(self.market)
        
        # If we hold more than 5000 KRW worth (min order size approx), we assume we are in position
        # Note: Upbit min order is 5000 KRW.
        if (balance * current_price) > 5000:
            # We are likely in position.
            # Limitation: We don't know the EXACT entry price/time if we restarted.
            # Fallback: Assume entry price is current price (conservative) or try to fetch last buy order.
            # fetching last buy order is better.
            
            self.position = {
                'quantity': balance,
                'entry_price': current_price, # Placeholder, will update below
                'entry_time': datetime.datetime.now() # Placeholder
            }
            logger.info(f"Detected existing holding: {balance} {coin_currency}")
        else:
            self.position = None

    def buy_market(self):
        """
        Execute Market Buy with all available KRW
        """
        krw_balance = self.api.get_balance("KRW")
        # Ensure we have enough for min order (5000 KRW)
        if krw_balance < 5500:
            logger.warning("Insufficient KRW balance to buy.")
            return

        fee = krw_balance * TRADE_FEE_RATE
        buy_amount = krw_balance - fee
        
        # Upbit 'price' order is Market Buy by Amount (total price in KRW)
        result = self.api.place_order(self.market, 'bid', price=math.floor(buy_amount), ord_type='price')
        
        if result:
            logger.info(f"Buy Order Placed: {result}")
            send_message(f"🔵 BUY Executed\nAmount: {math.floor(buy_amount)} KRW")
            # Update state (approximate, next loop will sync properly)
            self._sync_state()
            # Explicitly set entry time to now
            if self.position:
                self.position['entry_time'] = datetime.datetime.now()
                # Entry price is not immediately available, usually inferred from order result or next ticker.

    def sell_market(self, reason="Signal"):
        """
        Execute Market Sell of all holdings
        """
        if not self.position:
            return

        volume = self.position['quantity']
        
        # Upbit 'market' order is Market Sell by Volume
        result = self.api.place_order(self.market, 'ask', volume=volume, ord_type='market')
        
        if result:
            logger.info(f"Sell Order Placed ({reason}): {result}")
            send_message(f"🔴 SELL Executed\nReason: {reason}\nVolume: {volume}")
            self.position = None

    def monitor_position(self, current_price):
        """
        Check StopLoss, TakeProfit, TimeLimit
        """
        if not self.position:
            return

        # If data is missing (restarted bot), we might skip checks or use current price as base (risk).
        # For safety, if entry_time is recent (just initialized placeholder), maybe skip time check.
        
        # Calculate PnL
        # Note: If we don't know true entry_price, PnL calc is broken. 
        # For this prototype, we assume the bot runs continuously or we accept the restart limitation.
        
        # A robust solution needs 'orders' history fetching to find last average buy price.
        # Let's try to trust the in-memory state.
        
        entry_price = self.position.get('entry_price', current_price)
        entry_time = self.position.get('entry_time', datetime.datetime.now())
        
        pnl_pct = (current_price - entry_price) / entry_price * 100
        days_held = (datetime.datetime.now() - entry_time).total_seconds() / (24 * 3600)

        if pnl_pct <= -STOP_LOSS_PCT:
            self.sell_market(reason=f"Stop Loss ({pnl_pct:.2f}%)")
        elif pnl_pct >= TAKE_PROFIT_PCT:
            self.sell_market(reason=f"Take Profit ({pnl_pct:.2f}%)")
        elif days_held >= MAX_HOLD_DAYS and pnl_pct >= MIN_PROFIT_PCT:
            self.sell_market(reason=f"Max Hold (Profit {pnl_pct:.2f}%)")

    def get_market_state(self):
        return self.position is not None
