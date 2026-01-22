from .indicators import Indicators
from config.settings import RSI_OVERBOUGHT

class SignalGenerator:
    def __init__(self, rsi_oversold=30, rsi_period=14, macd_fast=12, macd_slow=26, macd_signal=9):
        self.rsi_oversold = rsi_oversold
        self.rsi_period = rsi_period
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal

    def process(self, df):
        """
        Adds indicators to the dataframe and generates signals
        """
        # Calculate Indicators
        df['rsi'] = Indicators.calculate_rsi(df['close'], period=self.rsi_period)
        df['macd'], df['macd_signal'], df['macd_hist'] = Indicators.calculate_macd(
            df['close'], 
            fast=self.macd_fast, 
            slow=self.macd_slow, 
            signal=self.macd_signal
        )

        return df

    def check_buy_signal(self, row):
        """
        Check if the latest row meets buy entry conditions
        """
        rsi = row['rsi']
        macd_line = row['macd']
        signal_line = row['macd_signal']
        histogram = row['macd_hist']

        # Logic from user request
        # macd_bullish = macd_line > signal_line
        macd_bullish = macd_line > signal_line
        
        # rsi_oversold = rsi < self.rsi_oversold
        rsi_is_oversold = rsi < self.rsi_oversold

        if macd_bullish and rsi_is_oversold:
            return True
        return False
