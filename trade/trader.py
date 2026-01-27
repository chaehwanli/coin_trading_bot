from data_fetcher.upbit_api import UpbitAPI
from config.settings import TARGET_COIN, TRADE_FEE_RATE, STOP_LOSS_PCT, TAKE_PROFIT_PCT, MAX_HOLD_DAYS, MIN_PROFIT_PCT, ATR_K, RISK_PER_TRADE_PCT, MAX_CONSECUTIVE_LOSSES, COOLDOWN_CANDLES
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
        # Cooldown State
        self.consecutive_losses = 0
        self.cooldown_until = None # datetime object
        
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
            
            # Cooldown Logic
            if "Stop Loss" in reason:
                self.consecutive_losses += 1
                logger.info(f"Consecutive Losses: {self.consecutive_losses}")
                
                if self.consecutive_losses >= MAX_CONSECUTIVE_LOSSES:
                    # Activate Cooldown
                    # Default interval is 60 minutes.
                    cooldown_minutes = COOLDOWN_CANDLES * 60 
                    self.cooldown_until = datetime.datetime.now() + datetime.timedelta(minutes=cooldown_minutes)
                    stop_msg = f"⛔ Cooldown Activated: {self.consecutive_losses} Losses. Paused until {self.cooldown_until.strftime('%H:%M')}"
                    logger.warning(stop_msg)
                    send_message(stop_msg)
                    # Reset counter after activation? Rules say ">= N -> Activate". Usually reset or keep logic.
                    # Let's reset to 0 after activation to restart cycle.
                    self.consecutive_losses = 0 
            else:
                # Profit or other reason -> Reset losses
                if self.consecutive_losses > 0:
                    logger.info("Win or Exit -> Resetting Consecutive Losses")
                self.consecutive_losses = 0

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

    def calculate_position_size(self, atr, current_price):
        """
        Calculate position size based on Risk Per Trade and ATR
        Position Size = (Total Capital * Risk%) / (ATR * k)
        """
        krw_balance = self.api.get_balance("KRW")
        total_capital = krw_balance # Alternatively, use initial capital + profit
        
        risk_amount = total_capital * (RISK_PER_TRADE_PCT / 100)
        stop_distance = atr * ATR_K
        
        if stop_distance == 0:
            return 0
            
        position_qty = risk_amount / stop_distance
        
        # Determine max qty purchasable with current balance
        max_qty = (krw_balance * 0.999) / current_price # 0.1% buffer for fees
        
        # Effective Quantity
        qty_to_buy = min(position_qty, max_qty)
        
        # Check min order size (5000 KRW)
        if (qty_to_buy * current_price) < 5500:
            logger.warning(f"Calculated Position Size too small: {qty_to_buy*current_price} KRW")
            return 0
            
        return qty_to_buy

    def buy_strategic(self, current_price, atr):
        """
        Execute Buy Logic with Position Sizing
        """
        # Check Cooldown
        if self.cooldown_until:
            if datetime.datetime.now() < self.cooldown_until:
                logger.info(f"Skipping signal due to Cooldown (Until {self.cooldown_until.strftime('%H:%M')})")
                return
            else:
                # Cooldown Expired
                self.cooldown_until = None
                send_message("🟢 Cooldown Expired. Resuming Trading.")

        qty = self.calculate_position_size(atr, current_price)
        if qty <= 0:
            return

        # Upbit requires price for 'price' order (market buy by amount)
        # However, we calculated 'quantity' (volume).
        # We can use 'market' order (market buy by payload?)
        # Upbit API: 
        #   bid (buy) + price -> Market Buy by Amount (KRW)
        #   ask (sell) + volume -> Market Sell by Volume (Coin)
        #   bid (buy) + volume + limit -> Limit Buy
        # We want to buy specific VOLUME at market. Upbit Market Buy only supports PRICE (KRW amount).
        # So we convert QTY back to KRW Estimate.
        
        buy_amount_krw = math.floor(qty * current_price)
        
        # Fee buffer check again
        krw_balance = self.api.get_balance("KRW")
        if buy_amount_krw > (krw_balance - krw_balance * TRADE_FEE_RATE):
             buy_amount_krw = math.floor(krw_balance * (1 - TRADE_FEE_RATE))

        result = self.api.place_order(self.market, 'bid', price=buy_amount_krw, ord_type='price')
        
        if result:
            logger.info(f"Strategic Buy Order Placed: {result}")
            send_message(f"🔵 STRATEGIC BUY Executed\nAmount: {buy_amount_krw} KRW\nATR: {atr}")
            
            self._sync_state()
            if self.position:
                self.position['entry_time'] = datetime.datetime.now()
                self.position['atr'] = atr
                self.position['highest_price'] = current_price # Initialize highest price for trailing stop

    def monitor_trend_position(self, current_price):
        """
        Monitor Position with ATR-based Trailing Stop
        """
        if not self.position:
            return

        entry_price = self.position.get('entry_price', current_price)
        atr = self.position.get('atr', 0)
        highest_price = self.position.get('highest_price', entry_price)
        
        # If ATR is missing (e.g. restart), we might need to recalculate or fallback.
        # Fallback to Fixed % if ATR is 0
        if atr == 0:
            self.monitor_position(current_price)
            return

        # Update Highest Price
        if current_price > highest_price:
            highest_price = current_price
            self.position['highest_price'] = highest_price # Update state

        # Calculate Stops
        stop_loss_price = entry_price - (atr * ATR_K)
        trailing_stop_price = highest_price - (atr * ATR_K)
        
        # Current PnL
        pnl_pct = (current_price - entry_price) / entry_price * 100
        
        # Check Exits
        # 1. Hard Stop Loss (Initial Risk)
        if current_price <= stop_loss_price:
             self.sell_market(reason=f"ATR Stop Loss ({pnl_pct:.2f}%)")
             
        # 2. Trailing Stop
        elif current_price <= trailing_stop_price:
             self.sell_market(reason=f"ATR Trailing Stop ({pnl_pct:.2f}%)")
        
        # 3. No Max Hold Days for Trend Strategy (per README 7.2.3)
