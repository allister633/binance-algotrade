import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import argparse

import backtest
import indicators

plt.style.use('ggplot')

def add_ema(df, period):
    df["ema" + str(period)] = df["close"].ewm(span=period).mean()

def add_sma(df, period):
    df["sma" + str(period)] = df["close"].rolling(window=period).mean()

def runstrategy(close, rsi: indicators.RSI, macd: indicators.MACD):
    """ Emet un signal d'achat lorsque le RSI croise par en dessous la valeur 33
    ou lorsque la MACD croise la ligne de signal.

    Un achat par RSI peut être confirmé avec la MACD dans quel cas on attendra son signal
    pour vendre.
    """

    # indique le signal en cours sachant que MACD > RSI
    buysignalstrat = None

    macdcrossedfromdown = False
    macdcrossedfromtop = False

    lowthreshpassed = False
    lowlowthreshpassed = False
    hithreshpassed = False
    hihithreshpassed = False
    hasbought = False
    close['positions'] = 0.0
    close['rsi'] = rsi.data()
    close['macd'], close['macd_signal'] = macd.data()
    for index, row in close.iterrows():
        # achat en fonction du RSI
        if row['rsi'] < 33:
            lowthreshpassed = True
        if row['rsi'] < 20:
            lowlowthreshpassed = True
        if row['rsi'] > 66:
            hithreshpassed = True
        if row['rsi'] > 80:
            hihithreshpassed = True

        if row['rsi'] > 20 and lowlowthreshpassed == True:
            lowlowthreshpassed = False
            if hasbought == False:
                print('{} BUY at {} by RSI'.format(index, row['close']))
                hasbought = True
                close['positions'].loc[index] = 1.0
                buysignalstrat = "RSI"
        if row['rsi'] > 33 and lowthreshpassed == True:
            lowthreshpassed = False
            if hasbought == False:
                print('{} BUY at {} by RSI'.format(index, row['close']))
                hasbought = True
                close['positions'].loc[index] = 1.0
                buysignalstrat = "RSI"
        # on revend par RSI seulement si c'est le seul signal qui a généré l'achat
        if row['rsi'] < 80 and hihithreshpassed == True:
            hihithreshpassed = False
            if hasbought == True and buysignalstrat == "RSI":
                print('{} SELL at {} by RSI'.format(index, row['close']))
                hasbought = False
                close['positions'].loc[index] = -1.0
                buysignalstrat = None
        if row['rsi'] < 66 and hithreshpassed == True:
            hithreshpassed = False
            if hasbought == True and buysignalstrat == "RSI":
                print('{} SELL at {} by RSI'.format(index, row['close']))
                hasbought = False
                close['positions'].loc[index] = -1.0
                buysignalstrat = None

        # achat en fonction de la MACD
        # TODO : lorsque le marché stagne, la MACD génère beaucoup de faux signaux, comment les éviter ?
        if row['macd'] > row['macd_signal'] and macdcrossedfromdown == False:
            print('MACD CROSSED FROM BOTTOM AT ' + str(index))
            macdcrossedfromdown = True
            macdcrossedfromtop = False
            if hasbought == False:
                print('{} BUY at {} by MACD'.format(index, row['close']))
                hasbought = True
                close['positions'].loc[index] = 1.0
            # même si nous avions acheté avec le RSI, si le signal est confirmé par la MACD
            # il sera considéré comme étant prévalant
            buysignalstrat = "MACD"
        if  row['macd'] < row['macd_signal'] and macdcrossedfromtop == False:
            print('MACD CROSSED FROM TOP AT ' + str(index))
            macdcrossedfromtop = True
            macdcrossedfromdown = False
            if hasbought == True:
                print('{} SELL at {} by MACD'.format(index, row['close']))
                hasbought = False
                close['positions'].loc[index] = -1.0
                buysignalstrat = None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    args = parser.parse_args()
    
    df = pd.read_csv(args.file, index_col='time')
    df.index = df.index.astype('datetime64')

    #close = df.loc['20191220':,['close']].astype('float64')
    #close = df.loc['20191220':,['close']].astype('float64')
    close = df

    #add_ema(close, 12)
    #add_ema(close, 26)
    add_sma(close, 50)
    add_sma(close, 100)

    rsi = indicators.RSI(close['close'], 9)
    macd = indicators.MACD(close['close'], 12, 26, 9)

    runstrategy(close, rsi, macd)

    fig, (ax1, ax2, ax3) = plt.subplots(3, sharex=True)
    fig.suptitle(args.file)
    ax1.plot(close['close'])
    ax1.plot(close['close'].loc[close['positions'] == 1.0].index, close['close'].loc[close['positions'] == 1.0], '^', markersize = 10, color = 'g')
    ax1.plot(close['close'].loc[close['positions'] == -1.0].index, close['close'].loc[close['positions'] == -1.0], 'v', markersize = 10, color = 'r')
    ax1.plot(close['sma50'], label='SMA50')
    ax1.plot(close['sma100'], label='SMA100')
    ax1.legend()
    ax2.plot(rsi.data(), label='RSI 9')
    ax2.legend()
    macd, macd_signal = macd.data()
    ax3.plot(macd, label='MACD 12 26 9')
    ax3.plot(macd_signal)
    ax3.legend()

    plt.show()

if __name__ == "__main__":
    main()
