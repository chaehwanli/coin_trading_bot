import os
import json
import logging
from datetime import datetime
from data_fetcher.upbit_api import UpbitAPI
from config.settings import TRADE_FEE_RATE

logger = logging.getLogger("MockUpbitAPI")

class MockUpbitAPI(UpbitAPI):
    def __init__(self, portfolio_file="mock_portfolio.json"):
        super().__init__()
        self.portfolio_file = portfolio_file
        self._initialize_portfolio()

    def _initialize_portfolio(self):
        if not os.path.exists(self.portfolio_file):
            initial_state = {
                "KRW": 10000000, # 10 Million KRW initial capital
            }
            self._save_portfolio(initial_state)
            logger.info(f"Initialized mock portfolio at {self.portfolio_file}")

    def _load_portfolio(self):
        try:
            with open(self.portfolio_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load mock portfolio: {e}")
            return {"KRW": 0}

    def _save_portfolio(self, data):
        with open(self.portfolio_file, 'w') as f:
            json.dump(data, f, indent=4)

    def get_balance(self, ticker="KRW"):
        """
        Override get_balance to read from local file
        """
        portfolio = self._load_portfolio()
        return float(portfolio.get(ticker, 0.0))

    def place_order(self, market, side, volume=None, price=None, ord_type='limit'):
        """
        Simulate order placement
        """
        portfolio = self._load_portfolio()
        currency = market.split("-")[1] # e.g., BTC from KRW-BTC
        
        current_price = self.get_current_price(market)
        if current_price is None:
            logger.error("Failed to fetch current price for mock order.")
            return None

        # Calculate transaction details
        if side == 'bid': # Buy
            if ord_type == 'price': # Market Buy by Price (Amount)
                total_cost = float(price)
                fee = total_cost * TRADE_FEE_RATE
                actual_buy_amount = total_cost - fee
                buy_volume = actual_buy_amount / current_price
                
                if portfolio.get("KRW", 0) < total_cost:
                    logger.warning("Insufficient KRW for mock buy.")
                    return None
                
                portfolio["KRW"] -= total_cost
                portfolio[currency] = portfolio.get(currency, 0) + buy_volume
                
            else: # Limit Buy (Logic simplified for mock, treating as market for now or need specific logic)
                 # For simplicity in this bot which uses market/price orders:
                 logger.warning(f"Mock Limit Buy not fully implemented. Treating as Market Buy is risky without checks. Skipping.")
                 return None

        elif side == 'ask': # Sell
            if ord_type == 'market': # Market Sell by Volume
                sell_volume = float(volume)
                if portfolio.get(currency, 0) < sell_volume:
                     logger.warning("Insufficient Coin balance for mock sell.")
                     return None
                
                total_value = sell_volume * current_price
                fee = total_value * TRADE_FEE_RATE
                payout = total_value - fee
                
                portfolio[currency] -= sell_volume
                portfolio["KRW"] = portfolio.get("KRW", 0) + payout
                
            else:
                 logger.warning("Mock Limit Sell not implemented.")
                 return None

        self._save_portfolio(portfolio)
        
        # Return fake order result structure compatible with real API
        return {
            "uuid": f"mock-{datetime.now().timestamp()}",
            "side": side,
            "ord_type": ord_type,
            "price": str(price) if price else str(current_price),
            "avg_price": str(current_price),
            "state": "done",
            "market": market,
            "created_at": datetime.now().isoformat(),
            "volume": str(volume) if volume else str(buy_volume if side=='bid' else 0),
            "remaining_volume": "0",
            "reserved_fee": "0",
            "paid_fee": str(fee),
            "locked": "0",
            "executed_volume": str(volume) if volume else str(buy_volume if side=='bid' else 0),
            "trades_count": 1
        }
