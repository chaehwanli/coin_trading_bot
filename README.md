# coin_trading_bot
Coin 거래 봇, 업비트

# 목적
업비트에서 Coin을 자동으로 매수 매도하는 봇을 구현한다.

# 증권사
업비트를 사용한다.

# API
업비트 REST API를 사용한다.

# 대상 시장
원화 거래

# BackTest
백테스트를 수행하는 로직 필요하다
전략을 백테스트로 검증한다
1. 시장에서 거래량이 많은 종목을 대상으로 백테스트후 수익이 나는 종목에 대해서 봇을 돌린다.
2. 백테스트는 1년간의 데이터를 사용한다.
3. 백테스트를 위한 데이터는 업비트 REST API를 사용하고 백테스트를 위한 데이터를 저장한다.
4. 최적의 RSI 값을 찾을수 있도록 최적화 backtest 명령이 필요하다.
5. 백테스트를 위한 데이터에는 RSI, MACD 가 필요하다.
6. 최적화는 RSI, 손절/수익 비율 두가지로 이루어진다.

# 종목
1. 예상 종목: 비트코인, 이더리움
2. 종목은 백테스트를 통해 결정한다.

# 전략
1. 정규장 시간동안 동작한다. 
2. 1시간 분봉을 확인한다.
3. 매수 시그널은 RSI + MACD 지표를 이용한다.
```
rsi_oversold = 50

        # MACD 골든크로스/데드크로스 확인
        macd_bullish = macd_line > signal_line and histogram > 0
        macd_bearish = macd_line < signal_line and histogram < 0
        
        # RSI 과매수/과매도 확인
        rsi_oversold = rsi < self.rsi_oversold
        rsi_overbought = rsi > (RSI_OVERBOUGHT - 10)
        rsi_neutral = self.rsi_oversold <= rsi <= (RSI_OVERBOUGHT - 10)

        # 매수 결정
        if macd_bullish and rsi_oversold:
            self.buy()
        else:
            self.nothing()
```
5. 손실/수익 
```
Stop Loss: -3.0%
Take Profit: 35.0%
Long Max Hold Days: 5일
```
6. 매도 규칙
6.1 손실/수익 구간을 지킨다. (Stop Loss, Take Profit)
6.2 최대 보유 기간을 지킨다. (Long Max Hold Days)

7. 거래 금액
초기 거래 시작 금액은 100만원으로 한다.
거래 수수료도 포함한다.
수익과 손실이 발생하면 초기 거래 금액에 계속 누적한다.
소수점 거래 가능하다.

8. 거래 결과 알림
거래 결과를 텔레그램으로 알림한다.

9. 매수 판단 결과 알림
매수 판단 결과를 텔레그램으로 알림한다.

10. 국내 휴장일
코인 시장은 365일 거래 가능하다.

11. 거래 시간
정규장 시간이 24시간이다.

12. 슬리피지 고려
매수/매도 시 슬리피지가 발생할 수 있으므로 이를 고려한다.
Backtest 시에도 적용한다.
거래시간도 슬리피지를 고려해서 정각 1분에 동작해. (예: 09:01에 1시간 봉 확인후 거래 여부 판단 동작)

13. 수수료 고려
매수/매도 시 수수료가 발생할 수 있으므로 이를 고려한다.
Backtest 시에도 적용한다.

14. 텔레그램 메시지 
텔레그램 메시지가 다른 봇 메시지와 구별되도록 키워드를 추가한다.
[Upbit Coin Trading Bot][실거래|모의거래][종목]

# Upbit Coin Trading Bot - Walkthrough

## Overview
This bot trades crypto on Upbit using an RSI + MACD strategy. It includes backtesting, parameter optimization, and Telegram notifications.

## 1. Setup

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Configure Environment Variables
Create a `.env` file in the project root (you can copy from `.env.example`):
```bash
cp .env.example .env
```
Edit the `.env` file with your actual keys and tokens:
```ini
UPBIT_ACCESS_KEY="your_access_key"
UPBIT_SECRET_KEY="your_secret_key"
TELEGRAM_BOT_TOKEN="your_bot_token"
TELEGRAM_CHAT_ID="your_chat_id"
```
The application uses `python-dotenv` to load these values automatically.


## 2. Data Collection (Required for Fast Backtesting)
The bot now supports local data caching to speed up backtests.
Run this command periodically to fetch the latest data from Upbit:
```bash
python collect_data.py --days 365
```
Data will be saved to the `data/` directory.

## 3. Optimization
Run the optimization script to find the best parameters.

### RSI Optimization
Find the best RSI Oversold threshold (Range: 20-50).
```bash
python optimize.py --mode rsi --market KRW-BTC --days 365
```

### Risk Parameter Optimization
Find the best combination of Stop Loss, Take Profit, and Max Hold Days.
You can specify a target RSI (e.g., 40) to test against using `--rsi`.
```bash
python optimize.py --mode pnl --market KRW-BTC --days 365 --rsi 40
```

This will save results to `optimization_results_{mode}_{market}.csv`.
**Update `config/settings.py`** with the best parameters found.

## 4. Backtesting

### Single Run
To run a specific backtest strategy and see detailed logs:
```bash
python backtest.py --market KRW-BTC --days 365 --rsi 30 --sl 3.0 --tp 35.0
```

### Batch Run (Multi-Coin Report)
To run backtests on multiple coins (BTC, ETH, XRP, SOL, DOGE, ADA) and generate a summary report:
```bash
python batch_backtest.py
```
This requires data to be collected first via `collect_data.py`.

## 5. Running the Bot
Start the bot. It will run every hour at minute 01.
```bash
python main.py
```

## 6. Features
- **Strategy**: 1-hour timeframe. Buy on RSI Oversold + MACD Golden Cross.
- **Sell Logic**: 
    - Stop Loss: -3.0%
    - Take Profit: +35.0%
    - Max Hold: 5 Days
- **Notifications**: Telegram alerts for Buys, Sells, and Errors.
- **Resilience**: Checks existing balance on restart to resume position management.

## 7. Realistic Simulation (Slippage & Fees)
To ensure backtest results match real-world conditions, the following costs are applied:
- **Trading Fee**: 0.05% (Upbit Standard, applied to Buy and Sell).
- **Slippage**: 0.05% (Conservative estimate).
    - **Buy Execution**: `Market Price * (1 + 0.0005)`
    - **Sell Execution**: `Market Price * (1 - 0.0005)`
- **Impact**: Profit margins in backtests will be slightly lower than raw indicator signals would suggest, providing a safer margin for strategy validation.
