import pandas as pd 
import numpy as np
import indicators
import logging

class BacktestResult:

    def __init__(self, start, end, trades, netret, sharpe, maxdrawdown, maxdrawdownduration):
        self.start = start
        self.end = end
        self.trades = trades
        self.netret = netret
        self.sharpe = sharpe
        self.maxdrawdown = maxdrawdown
        self.maxdrawdownduration = maxdrawdownduration

    def __str__(self):
        return 'Start :\t\t\t{}\nEnd :\t\t\t{}\nTrades :\t\t{}\nReturn % :\t\t{}\nSharpe Ratio :\t\t{}\nMax Drawdown % :\t{}\nMax Drawdown Duration :\t{}'\
            .format(self.start, self.end, self.trades, self.netret, self.sharpe, self.maxdrawdown, self.maxdrawdownduration) 

class Strategy:

    def __init__(self, index, fee):
        self.fee = fee
        self.signals = pd.DataFrame(index=index)
        self.signals['signal'] = 0.0
        self.signals['trades'] = 0.0
        self.signals['positions'] = 0.0
        self.signals['pct_change'] = 0.0

    def backtest(self, data):
        self.signals['pct_change'] = data.pct_change()
        self.signals['equity'] = 100.0 + (self.signals['pct_change'][self.signals['signal'] == 1.0].cumsum() * 100.0)
        self.signals['equity'].iloc[0] = 100.0
        # TODO : withdraw fees
        self.signals['equity'] = self.signals['equity'].fillna(method='ffill')

        self.signals['himark'] = self.signals['equity'].cummax()
        self.signals['drawdown'] = self.signals['equity'] - self.signals['himark']

        drawdownduration = 0.0
        maxdrawdownduration = 0.0
        for index, value in self.signals['drawdown'].iteritems():
            if value != 0:
                drawdownduration += 1
            else:
                if drawdownduration > maxdrawdownduration:
                    maxdrawdownduration = drawdownduration
                drawdownduration = 0

        netret = self.signals['pct_change'][self.signals['signal'] == 1.0].sum() * 100.0
        sharpe = self.signals['pct_change'][self.signals['signal'] == 1.0].mean() / self.signals['pct_change'][self.signals['signal'] == 1.0].std()
        trades = self.signals['positions'][self.signals['positions'] == 1.0].count()
        maxdrawdown = self.signals['drawdown'].min()

        return BacktestResult(self.signals.index[0], self.signals.index[len(self.signals.index) - 1], trades, netret, sharpe, maxdrawdown, maxdrawdownduration)

class BuyAndHoldStrategy(Strategy):

    def __init__(self, close, fee=0.0):
        Strategy.__init__(self, close.index, fee)
        self.signals['signal'] = 1.0
        self.signals['positions'] = self.signals['signal'].diff()
        # replace first NaN
        self.signals['positions'].iloc[0] = 1.0

class AvgCrossStrategy(Strategy):

    def __init__(self, close, fast_avg, slow_avg, fee=0.0):
        Strategy.__init__(self, close.index, fee)
        self.signals['signal'] = np.where(fast_avg > slow_avg, 1.0, 0.0)
        self.signals['positions'] = self.signals['signal'].diff()

class RSIMACDStrategy(Strategy):

    def __init__(self, close, rsi: indicators.RSI, macd: indicators.MACD, fee=0.0):
        Strategy.__init__(self, close.index, fee=0.0)

        # indique le signal en cours sachant que MACD > RSI
        buysignalstrat = None

        macdcrossedfromdown = False
        macdcrossedfromtop = False

        lowthreshpassed = False
        lowlowthreshpassed = False
        hithreshpassed = False
        hihithreshpassed = False
        hasbought = False
        self.signals['rsi'] = rsi.data()
        self.signals['macd'], self.signals['macd_signal'] = macd.data()
        for index, row in self.signals.iterrows():
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
                    hasbought = True
                    buysignalstrat = "RSI"
            if row['rsi'] > 33 and lowthreshpassed == True:
                lowthreshpassed = False
                if hasbought == False:
                    hasbought = True
                    buysignalstrat = "RSI"
            # on revend par RSI seulement si c'est le seul signal qui a généré l'achat
            if row['rsi'] < 80 and hihithreshpassed == True:
                hihithreshpassed = False
                if hasbought == True and buysignalstrat == "RSI":
                    hasbought = False
                    buysignalstrat = None
            if row['rsi'] < 66 and hithreshpassed == True:
                hithreshpassed = False
                if hasbought == True and buysignalstrat == "RSI":
                    hasbought = False
                    buysignalstrat = None

            # achat en fonction de la MACD
            # TODO : lorsque le marché stagne, la MACD génère beaucoup de faux signaux, comment les éviter ?
            if row['macd'] > row['macd_signal'] and macdcrossedfromdown == False:
                macdcrossedfromdown = True
                macdcrossedfromtop = False
                if hasbought == False:
                    hasbought = True
                # même si nous avions acheté avec le RSI, si le signal est confirmé par la MACD
                # il sera considéré comme étant prévalant
                buysignalstrat = "MACD"
            if  row['macd'] < row['macd_signal'] and macdcrossedfromtop == False:
                macdcrossedfromtop = True
                macdcrossedfromdown = False
                if hasbought == True:
                    hasbought = False
                    buysignalstrat = None

            if hasbought == True:
                self.signals['signal'].loc[index] = 1.0

        self.signals['positions'] = self.signals['signal'].diff()

class RSIStrategy(Strategy):

    def __init__(self, close, rsi: indicators.RSI, fee=0.0):
        Strategy.__init__(self, close.index, fee=0.0)
        #self.signals['signal'] = np.where((rsi.data["rsi"] > 20.0) & (rsi.data["rsi"] < 80.0), 1.0, 0.0)
        #self.signals['positions'] = self.signals['signal'].diff()
        #self.signals['positions'] = 0.0
        #self.signals['positions'][rsi.data["rsi"] < 20.0] = -1.0
        #self.signals['positions'][rsi.data["rsi"] > 80.0] = 1.0
        #self.signals['signal'] = self.signals['positions'].diff()

        #print(self.signals)

        lowthreshpassed = False
        lowlowthreshpassed = False
        hithreshpassed = False
        hihithreshpassed = False
        hasbought = False
        close['rsi'] = rsi.data()
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
                    hasbought = True
            if row['rsi'] > 33 and lowthreshpassed == True:
                lowthreshpassed = False
                if hasbought == False:
                    hasbought = True
            # on revend par RSI seulement si c'est le seul signal qui a généré l'achat
            if row['rsi'] < 80 and hihithreshpassed == True:
                hihithreshpassed = False
                if hasbought == True:
                    hasbought = False
            if row['rsi'] < 66 and hithreshpassed == True:
                hithreshpassed = False
                if hasbought == True:
                    hasbought = False

            if hasbought == True:
                self.signals['signal'].loc[index] = 1.0

        self.signals['positions'] = self.signals['signal'].diff()

class MACDStrategy(Strategy):

    def __init__(self, close, macd: indicators.MACD, fee=0.0):
        Strategy.__init__(self, close.index, fee=0.0)
        line, signal = macd.data()
        self.signals['signal'] = np.where(line > signal, 1.0, 0.0)
        self.signals['positions'] = self.signals['signal'].diff()
