import pandas as pd
import yfinance as yf
import backtrader as bt
import datetime as dt
import numpy as np

# ------------------------------
# 1. Download Historical Data
# ------------------------------
tickers = ["AAPL", "MSFT"]  # example portfolio
start_date = "2020-01-01"
end_date = "2024-12-31"

dfs = []
for ticker in tickers:
    df = yf.download(ticker, start=start_date, end=end_date)
    df["Ticker"] = ticker
    dfs.append(df)

data = pd.concat(dfs)

# ------------------------------
# 2. Define Strategy
# ------------------------------
class AdvancedEMAStrategy(bt.Strategy):
    params = dict(
        short_period=8,
        long_period=21,
        rsi_period=14,
        macd1=12, macd2=26, macdsig=9,
        stop_loss=0.95,   # 5% loss
        take_profit=1.10  # 10% profit
    )

    def __init__(self):
        # Indicators
        self.short_ema = bt.indicators.EMA(self.data.close, period=self.p.short_period)
        self.long_ema = bt.indicators.EMA(self.data.close, period=self.p.long_period)
        self.rsi = bt.indicators.RSI_SMA(self.data.close, period=self.p.rsi_period)
        self.macd = bt.indicators.MACD(self.data.close, period_me1=self.p.macd1,
                                       period_me2=self.p.macd2, period_signal=self.p.macdsig)

        self.order = None
        self.buy_price = None

    def next(self):
        if self.order:
            return  # wait for pending order

        # Entry Condition: EMA crossover + RSI confirmation + MACD bullish
        if not self.position:
            if self.short_ema[0] > self.long_ema[0] and self.rsi[0] > 50 and self.macd.macd[0] > self.macd.signal[0]:
                self.order = self.buy()
                self.buy_price = self.data.close[0]

        # Exit Condition: Stop-loss / Take-profit / Bearish signal
        else:
            if (self.data.close[0] <= self.buy_price * self.p.stop_loss) or \
               (self.data.close[0] >= self.buy_price * self.p.take_profit) or \
               (self.short_ema[0] < self.long_ema[0]):
                self.order = self.sell()

# ------------------------------
# 3. Performance Analyzer
# ------------------------------
class PerformanceAnalyzer(bt.Analyzer):
    def get_analysis(self):
        portfolio = self.strategy.broker.get_value()
        cash = self.strategy.broker.get_cash()
        pnl = portfolio - 100000  # assuming initial cash 100k
        return dict(portfolio=portfolio, cash=cash, pnl=pnl)

# ------------------------------
# 4. Backtest Setup
# ------------------------------
cerebro = bt.Cerebro()
cerebro.addstrategy(AdvancedEMAStrategy)
cerebro.addanalyzer(PerformanceAnalyzer, _name="perf")

# Initial capital and commission
cerebro.broker.setcash(100000.0)
cerebro.broker.setcommission(commission=0.001)  # 0.1% commission

# Add data for each ticker
for ticker in tickers:
    df = data[data["Ticker"] == ticker]
    df_bt = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(df_bt, name=ticker)

# Run backtest
results = cerebro.run()
analyzer = results[0].analyzers.perf.get_analysis()

# ------------------------------
# 5. Print & Plot Results
# ------------------------------
print(f"Final Portfolio Value: {analyzer['portfolio']:.2f}")
print(f"Total PnL: {analyzer['pnl']:.2f}")

cerebro.plot(iplot=False, style="candlestick")
