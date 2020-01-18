import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import argparse

import strategies
import indicators

plt.style.use('ggplot')

def add_ema(df, period):
    df["ema" + str(period)] = df["close"].ewm(span=period).mean()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    args = parser.parse_args()
    
    df = pd.read_csv(args.file, index_col='time', parse_dates=True)

    #close = df.loc['20191225':,['close']].astype('float64')
    close = df
    
    print("Buy And Hold Strategy :")
    strat1 = strategies.BuyAndHoldStrategy(close, 0.001)
    strat1.backtest(close['close'])
    print(flush=True)

    add_ema(close, 12)
    add_ema(close, 26)

    macd = indicators.MACD(close['close'], 12, 26, 9)
    rsi = indicators.RSI(close['close'], 9)

    print("MACD Strategy :")
    strat3 = strategies.MACDStrategy(close, macd, 0.001)
    strat3.backtest(close['close'])
    print(flush=True)

    print("RSI Strategy :")
    strat4 = strategies.RSIStrategy(close, rsi, 0.001)
    strat4.backtest(close['close'])
    print(flush=True)
    
    print("Custom RSI + MACD Strategy :")
    strat2 = strategies.RSIMACDStrategy(close, rsi, macd, 0.001)
    strat2.backtest(close['close'])

    fig, (ax1, ax2, ax3, ax4) = plt.subplots(4, sharex=True)
    fig.suptitle(args.file)
    ax1.plot(close['close'])
    ax1.plot(close['ema12'], label='EMA12')
    ax1.plot(close['ema26'], label='EMA26')
    ax1.plot(close['close'].loc[strat2.signals['positions'] == 1.0].index, close['close'].loc[strat2.signals['positions'] == 1.0], '^', markersize = 10, color = 'g')
    ax1.plot(close['close'].loc[strat2.signals['positions'] == -1.0].index, close['close'].loc[strat2.signals['positions'] == -1.0], 'v', markersize = 10, color = 'r')
    ax1.legend()
    macd, macd_signal = macd.data()
    ax2.plot(macd, label='MACD 12 26 9')
    ax2.plot(macd_signal)
    #ax3.plot(strat1.signals['equity'])
    ax3.plot(rsi.data(), label='RSI 9')
    ax4.plot(strat2.signals['equity'])
    plt.show()

if __name__ == "__main__":
    main()
