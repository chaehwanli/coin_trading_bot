from .indicators import Indicators
from config.settings import RSI_OVERBOUGHT, ATR_PERIOD, EMA_FAST, EMA_SLOW, BB_PERIOD, BB_STD, BB_WIDTH_THRESHOLD, ATR_VOLATILITY_THRESHOLD

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
        
        # New Indicators
        df['atr'] = Indicators.calculate_atr(df['high'], df['low'], df['close'], period=ATR_PERIOD)
        df['ema_fast'] = Indicators.calculate_ema(df['close'], period=EMA_FAST)
        df['ema_slow'] = Indicators.calculate_ema(df['close'], period=EMA_SLOW)
        df['upper_band'], df['lower_band'] = Indicators.calculate_bollinger_bands(df['close'], period=BB_PERIOD, std_dev=BB_STD)
        df['vol_sma'] = Indicators.calculate_sma(df['volume'], period=20) # 20 period MA for volume

        # New Indicators
        df['atr'] = Indicators.calculate_atr(df['high'], df['low'], df['close'], period=ATR_PERIOD)
        df['ema_fast'] = Indicators.calculate_ema(df['close'], period=EMA_FAST)
        df['ema_slow'] = Indicators.calculate_ema(df['close'], period=EMA_SLOW)
        df['upper_band'], df['lower_band'] = Indicators.calculate_bollinger_bands(df['close'], period=BB_PERIOD, std_dev=BB_STD)
        df['vol_sma'] = Indicators.calculate_sma(df['volume'], period=20) # 20 period MA for volume

        # Logic Refinements:
        # 1. Volatility Filter: ATR(t) / ATR(t-5)
        df['atr_ratio'] = df['atr'] / df['atr'].shift(5)
        
        # 2. Risk Management ATR: prev_atr = ATR(t-1)
        df['prev_atr'] = df['atr'].shift(1)

        return df

    def check_buy_signal(self, row):
        """
        Check if the latest row meets buy entry conditions (RSI + MACD Reversal)
        """
        rsi = row['rsi']
        macd_line = row['macd']
        signal_line = row['macd_signal']
        histogram = row['macd_hist']
        
        # Volatility Check (ATR Based)
        if self.check_volatility_explosion(row):
            return False 

        # Logic from user request
        # macd_bullish = macd_line > signal_line
        macd_bullish = macd_line > signal_line
        
        # rsi_oversold = rsi < self.rsi_oversold
        rsi_is_oversold = rsi < self.rsi_oversold

        if macd_bullish and rsi_is_oversold:
            return True
        return False
        
    def check_trend_following_buy_signal(self, row):
        """
        Check Trend Following Entry (EMA Cross + BB Breakout + Volume)
        """
        if self.check_volatility_explosion(row):
             return False

        ema_bullish = row['ema_fast'] > row['ema_slow']
        bb_breakout = row['close'] > row['upper_band']
        volume_spike = row['volume'] > row['vol_sma']
        
        if ema_bullish and bb_breakout and volume_spike:
            return True
        return False

    def check_volatility_explosion(self, row, threshold=ATR_VOLATILITY_THRESHOLD):
        """
        Detect Volatility Explosion using ATR Ratio
        Rule: ATR[t] / ATR[t-5] > 1.5
        """
        atr_ratio = row.get('atr_ratio', 0)
        
        if atr_ratio > threshold:
             return True
        return False
