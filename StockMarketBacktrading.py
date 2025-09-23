import pandas as pd
import yfinance as yf
import backtrader as bt

# ------------------------------
# 1. Download Historical Data
# ------------------------------
tickers = ["AAPL", "MSFT"]
start_date = "2020-01-01"
end_date = "2024-12-31"

data_dict = {}
for ticker in tickers:
    df = yf.download(ticker, start=start_date, end=end_date)
    df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
    keep_cols = [col for col in ['Open', 'High', 'Low', 'Close', 'Volume', 'Adj Close'] if col in df.columns]
    df = df[keep_cols]
    df.index = pd.to_datetime(df.index)
    data_dict[ticker] = df

# ------------------------------
# 2. Enhanced Strategy
# ------------------------------
class EnhancedEMAStrategy(bt.Strategy):
    params = dict(
        short_period=8,
        long_period=21,
        rsi_period=14,
        atr_period=14,
        risk_per_trade=0.02  # 2% risk
    )

    def __init__(self):
        self.short_ema = bt.indicators.EMA(self.data.close, period=self.p.short_period)
        self.long_ema = bt.indicators.EMA(self.data.close, period=self.p.long_period)
        self.rsi = bt.indicators.RSI(self.data.close, period=self.p.rsi_period)
        self.macd = bt.indicators.MACD(self.data.close)
        self.macd_signal = bt.indicators.MACD(self.data.close).signal
        self.atr = bt.indicators.ATR(self.data, period=self.p.atr_period)

        self.order = None
        self.buy_price = None
        self.stop_price = None
        self.take_profit = None

    def next(self):
        if self.order:
            return

        cash = self.broker.get_cash()

        # ENTRY CONDITION
        if not self.position:
            if (self.short_ema[0] > self.long_ema[0] and
                self.rsi[0] > 45 and
                self.macd.macd[0] > self.macd.signal[0]):

                entry_price = self.data.close[0]
                atr = self.atr[0]

                # ATR-based stop-loss & take-profit
                self.stop_price = entry_price - 2 * atr
                self.take_profit = entry_price + 3 * atr

                # Position sizing (2% risk of portfolio)
                risk_amount = cash * self.p.risk_per_trade
                position_size = risk_amount / (entry_price - self.stop_price)

                self.order = self.buy(size=position_size)
                self.buy_price = entry_price

        # EXIT CONDITION
        else:
            if (self.data.close[0] <= self.stop_price or
                self.data.close[0] >= self.take_profit or
                self.short_ema[0] < self.long_ema[0]):
                self.order = self.sell(size=self.position.size)

# ------------------------------
# 3. Backtest Setup
# ------------------------------
cerebro = bt.Cerebro()
cerebro.addstrategy(EnhancedEMAStrategy)

# Add analyzers
cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe", timeframe=bt.TimeFrame.Days, riskfreerate=0.0)
cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")

cerebro.broker.setcash(100000.0)
cerebro.broker.setcommission(commission=0.001)

# Add data
for ticker, df in data_dict.items():
    df_bt = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(df_bt, name=ticker)

# Run backtest
results = cerebro.run()
strat = results[0]

# ------------------------------
# 4. Print Results
# ------------------------------
start_value = 100000.0
end_value = cerebro.broker.getvalue()
cagr = strat.analyzers.returns.get_analysis()["rnorm100"]
sharpe = strat.analyzers.sharpe.get_analysis().get("sharperatio", None)
max_dd = strat.analyzers.drawdown.get_analysis()["max"]["drawdown"]

print(f"Initial Portfolio Value: {start_value:.2f}")
print(f"Final Portfolio Value: {end_value:.2f}")
print(f"CAGR: {cagr:.2f}%")
print(f"Sharpe Ratio: {sharpe:.2f}")
print(f"Max Drawdown: {max_dd:.2f}%")

# Plot
cerebro.plot(iplot=False, style="candlestick", volume=False, numfigs=2)
