import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import argparse

import backtest
import indicators
import strategies


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    parser.add_argument("--sma", type=int, nargs='+', help='Adds SMA to the price graph')
    parser.add_argument("--ema", type=int, nargs='+', help='Adds EMA to the price graph')
    parser.add_argument("--rsi", type=int, help='Adds RSI in a subplot')
    parser.add_argument("--macd", type=int, nargs=3, help='Adds MACD in a subplot')
    parser.add_argument("--bbands", type=int, nargs=2, help='Adds Bollinger Bands to the price graph')
    parser.add_argument("--strategy", type=int, nargs='+', help='Adds a strategy, 1 : EMA Cross')
    args = parser.parse_args()

    ohlc = pd.read_csv(args.file, index_col='time', parse_dates=True)
    close = ohlc['close']

    # calculates the number of sublots
    rows = 1
    if args.rsi != None:
        rows += 1
    if args.macd != None:
        rows += 1

    fig = make_subplots(rows=rows, cols=1, shared_xaxes=True)

    # plots close bar graph with averages
    row = 1
    fig.add_trace(go.Scatter(x=ohlc.index, y=close, name="Close"), row=row, col=1)
    if args.ema != None:
        for period in args.ema:
            ema = indicators.EMA(close, period)
            fig.add_trace(go.Scatter(x=ohlc.index, y=ema.df['ema{}'.format(period)], name="EMA {}".format(period)), row=row, col=1)
    if args.sma != None:
        for period in args.sma:
            sma = indicators.SMA(close, period)
            fig.add_trace(go.Scatter(x=ohlc.index, y=sma.df['sma{}'.format(period)], name="SMA {}".format(period)), row=row, col=1)

    # plots Bollinger Bands
    if args.bbands != None:
        bbands = indicators.BollingerBands(close, args.bbands[0])
        fig.add_trace(go.Scatter(x=ohlc.index, y=bbands.df.ma), row=row, col=1)
        fig.add_trace(go.Scatter(x=ohlc.index, y=bbands.df.upper), row=row, col=1)
        fig.add_trace(go.Scatter(x=ohlc.index, y=bbands.df.lower), row=row, col=1)
        row += 1

    row += 1

    # plots RSI
    if args.rsi != None:
        rsi = indicators.RSI(close, args.rsi)
        fig.add_trace(go.Scatter(x=ohlc.index, y=rsi.df.rsi, name="RSI {}".format(args.rsi)), row=row, col=1)
        row += 1

    # plots MACD
    if args.macd != None:
        macd = indicators.MACD(close, args.macd[0], args.macd[1], args.macd[2])
        fig.add_trace(go.Scatter(x=ohlc.index, y=macd.df.MACD, name="MACD {} {} {}".format(args.macd[0], args.macd[1], args.macd[2])), row=row, col=1)
        fig.add_trace(go.Scatter(x=ohlc.index, y=macd.df.signal, name="MACD Signal"), row=row, col=1)
        row += 1

    # plots strategy
    if args.strategy != None:
        if args.strategy[0] == 1:

            fast_ema = indicators.EMA(ohlc.close, period=args.strategy[1])
            slow_ema = indicators.EMA(ohlc.close, period=args.strategy[2])

            strategy = strategies.AvgCrossStrategy(ohlc.close, fast_ema.data(), slow_ema.data())

            fig.add_trace(go.Scatter(x=close.loc[strategy.signals['positions'] == 1.0].index, y=close.loc[strategy.signals['positions'] == 1.0],
            mode='markers', marker=dict(size=12, symbol='triangle-up', color='green'),  name="Buy"), row=1, col=1)

            fig.add_trace(go.Scatter(x=close.loc[strategy.signals['positions'] == -1.0].index, y=close.loc[strategy.signals['positions'] == -1.0],
            mode='markers', marker=dict(size=12, symbol='triangle-down', color='red'),  name="Sell"), row=1, col=1)

        elif args.strategy[0] == 2:

            macd = indicators.MACD(ohlc.close, args.strategy[1], args.strategy[2], args.strategy[3])

            strategy = strategies.MACDStrategy(ohlc.close, macd)

            fig.add_trace(go.Scatter(x=close.loc[strategy.signals['positions'] == 1.0].index, y=close.loc[strategy.signals['positions'] == 1.0],
            mode='markers', marker=dict(size=12, symbol='triangle-up', color='green'),  name="Buy"), row=1, col=1)

            fig.add_trace(go.Scatter(x=close.loc[strategy.signals['positions'] == -1.0].index, y=close.loc[strategy.signals['positions'] == -1.0],
            mode='markers', marker=dict(size=12, symbol='triangle-down', color='red'),  name="Sell"), row=1, col=1)

        elif args.strategy[0] == 3:

            bb1 = indicators.BollingerBands(ohlc.close, 20, 1)
            bb2 = indicators.BollingerBands(ohlc.close, 20, 2)
            strategy = strategies.DBBStrategy(ohlc.close, bb1, bb2)

            fig.add_trace(go.Scatter(x=close.loc[strategy.signals['positions'] == 1.0].index, y=close.loc[strategy.signals['positions'] == 1.0],
            mode='markers', marker=dict(size=12, symbol='triangle-up', color='green'),  name="Buy"), row=1, col=1)

            fig.add_trace(go.Scatter(x=close.loc[strategy.signals['positions'] == -1.0].index, y=close.loc[strategy.signals['positions'] == -1.0],
            mode='markers', marker=dict(size=12, symbol='triangle-down', color='red'),  name="Sell"), row=1, col=1)

        elif args.strategy[0] == 4:

            rsi = indicators.RSI(ohlc.close, 9)
            macd = indicators.MACD(ohlc.close, 12, 26, 9)
            strategy = strategies.RSIMACDStrategy(ohlc.close, rsi, macd)

            fig.add_trace(go.Scatter(x=close.loc[strategy.signals['positions'] == 1.0].index, y=close.loc[strategy.signals['positions'] == 1.0],
            mode='markers', marker=dict(size=12, symbol='triangle-up', color='green'),  name="Buy"), row=1, col=1)

            fig.add_trace(go.Scatter(x=close.loc[strategy.signals['positions'] == -1.0].index, y=close.loc[strategy.signals['positions'] == -1.0],
            mode='markers', marker=dict(size=12, symbol='triangle-down', color='red'),  name="Sell"), row=1, col=1)

    fig.show()

if __name__ == "__main__":
    main()
