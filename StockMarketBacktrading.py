import pandas as pd
import yfinance as yf
import backtrader as bt

# ------------------------------
# 1. Download Historical Data
# ------------------------------
tickers = ["AAPL", "MSFT"]  # example portfolio
start_date = "2020-01-01"
end_date = "2024-12-31"

data_dict = {}
for ticker in tickers:
    df = yf.download(ticker, start=start_date, end=end_date)

    # Flatten MultiIndex columns if they exist
    df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]

    # Keep only available OHLCV columns (Adj Close optional)
    keep_cols = [col for col in ['Open', 'High', 'Low', 'Close', 'Volume', 'Adj Close'] if col in df.columns]
    df = df[keep_cols]

    # Ensure datetime index
    df.index = pd.to_datetime(df.index)

    # Save cleaned DataFrame
    data_dict[ticker] = df

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

# Add analyzers for performance metrics
cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe", timeframe=bt.TimeFrame.Days, riskfreerate=0.0)
cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name="annualreturn")
cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")

# Initial capital and commission
cerebro.broker.setcash(100000.0)
cerebro.broker.setcommission(commission=0.001)  # 0.1% commission

# Add cleaned data for each ticker
for ticker, df in data_dict.items():
    df_bt = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(df_bt, name=ticker)

# Run backtest
results = cerebro.run()
strat = results[0]

# ------------------------------
# 5. Print Results
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

# ------------------------------
# 6. Plot
# ------------------------------
cerebro.plot(iplot=False, style="candlestick")
