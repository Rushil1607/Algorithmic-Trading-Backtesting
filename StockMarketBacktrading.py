import pandas as pd
import matplotlib.pyplot as plt
import backtrader as bt

# Load and preprocess data
data = pd.read_csv('your_data.csv')
data['Date'] = pd.to_datetime(data['Date'])
data.set_index('Date', inplace=True)

# Define the strategy
class EMACrossStrategy(bt.Strategy):
    params = (
        ('short_period', 8),
        ('long_period', 11),
    )

    def __init__(self):
        self.short_ema = bt.indicators.EMA(self.data.close, period=self.params.short_period)
        self.long_ema = bt.indicators.EMA(self.data.close, period=self.params.long_period)

    def next(self):
        if self.short_ema[0] > self.long_ema[0]:
            self.buy()
        elif self.short_ema[0] < self.long_ema[0]:
            self.sell()

# Backtest setup
cerebro = bt.Cerebro()
cerebro.addstrategy(EMACrossStrategy)

# Add data
data_feed = bt.feeds.PandasData(dataname=data)
cerebro.adddata(data_feed)

# Run backtest
cerebro.run()

# Plot results
cerebro.plot()
plt.show()
