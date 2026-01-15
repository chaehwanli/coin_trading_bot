import requests
import jwt
import uuid
import hashlib
from urllib.parse import urlencode
import pandas as pd
import time
import datetime
from config.settings import ACCESS_KEY, SECRET_KEY, get_logger

logger = get_logger("UpbitAPI")

SERVER_URL = "https://api.upbit.com"

class UpbitAPI:
    def __init__(self):
        self.access_key = ACCESS_KEY
        self.secret_key = SECRET_KEY

    def _get_headers(self, query=None):
        payload = {
            'access_key': self.access_key,
            'nonce': str(uuid.uuid4()),
        }

        if query:
            m = hashlib.sha512()
            m.update(urlencode(query).encode())
            query_hash = m.hexdigest()
            payload['query_hash'] = query_hash
            payload['query_hash_alg'] = 'SHA512'

        jwt_token = jwt.encode(payload, self.secret_key, algorithm='HS256')
        authorize_token = f'Bearer {jwt_token}'
        headers = {"Authorization": authorize_token}
        return headers

    def get_candles(self, market="KRW-BTC", interval="minute60", count=200, to=None):
        """
        Fetch candles from Upbit
        interval: minute1, minute3, minute5, minute10, minute15, minute30, minute60, minute240, day, week, month
        """
        if "minute" in interval:
            unit = interval.replace("minute", "")
            url = f"{SERVER_URL}/v1/candles/minutes/{unit}"
        else:
            url = f"{SERVER_URL}/v1/candles/{interval}s" # day -> days

        params = {
            "market": market,
            "count": count
        }
        if to:
            params["to"] = to

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch candles: {e}")
            return []

    def get_ohlcv(self, market="KRW-BTC", interval="minute60", days=365):
        """
        Fetch historical OHLCV data with pagination
        """
        logger.info(f"Fetching historical data for {market} ({interval}) - {days} days")
        
        all_candles = []
        limit_per_req = 200
        
        # Calculate end time (now)
        current_to = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        
        # Approximate number of requests needed
        # 1 day = 24 hours (for minute60)
        if interval == "minute60":
            total_hours = days * 24
            total_reqs = (total_hours // limit_per_req) + 2
        elif interval == "day":
            total_reqs = (days // limit_per_req) + 2
        else:
            # Default fallback calculation
            total_reqs = 50 

        for i in range(total_reqs):
            candles = self.get_candles(market, interval, count=limit_per_req, to=current_to)
            if not candles:
                break
            
            all_candles.extend(candles)
            
            # Update 'to' for next request (the last candle's candle_date_time_utc)
            last_candle = candles[-1]
            current_to = last_candle['candle_date_time_utc'] + "Z" # Add Z for UTC format or handle explicitly
            
            # Upbit Request Limit handling (10 req/sec usually safe, but sleep 0.1s to be safe)
            time.sleep(0.1) 
            
            # Check if we have enough data (rough check)
            if len(all_candles) >= (days * 24 if interval == "minute60" else days):
                 break

        if not all_candles:
            return pd.DataFrame()

        df = pd.DataFrame(all_candles)
        df = df[['candle_date_time_kst', 'opening_price', 'high_price', 'low_price', 'trade_price', 'candle_acc_trade_volume']]
        df.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.sort_values('datetime').reset_index(drop=True)
        
        # Filter exact date range if needed, here we just return all fetched logic
        return df

    def get_current_price(self, market="KRW-BTC"):
        url = f"{SERVER_URL}/v1/ticker"
        try:
            response = requests.get(url, params={"markets": market})
            response.raise_for_status()
            return float(response.json()[0]['trade_price'])
        except Exception as e:
            logger.error(f"Failed to fetch ticker: {e}")
            return None

    def get_balance(self, ticker="KRW"):
        """Get balance for a specific ticker (e.g., KRW, BTC)"""
        url = f"{SERVER_URL}/v1/accounts"
        headers = self._get_headers()
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            for account in data:
                if account['currency'] == ticker:
                    return float(account['balance'])
            return 0.0
        except Exception as e:
            logger.error(f"Failed to fetch balance: {e}")
            return 0.0

    def place_order(self, market, side, volume=None, price=None, ord_type="limit"):
        """
        side: 'bid' (buy), 'ask' (sell)
        ord_type: 'limit', 'price' (market buy), 'market' (market sell)
        """
        url = f"{SERVER_URL}/v1/orders"
        
        query = {
            'market': market,
            'side': side,
            'ord_type': ord_type,
        }
        if volume:
            query['volume'] = str(volume)
        if price:
            query['price'] = str(price)

        headers = self._get_headers(query)

        try:
            response = requests.post(url, json=query, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to place order: {e}, Response: {response.text if 'response' in locals() else 'N/A'}")
            return None
