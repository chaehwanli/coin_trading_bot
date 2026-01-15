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
