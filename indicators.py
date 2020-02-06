from abc import ABC, abstractmethod
import pandas as pd 
import numpy as np

class Indicator(ABC):

    def __init__(self, index):
        self.df = pd.DataFrame(index=index)

    @abstractmethod
    def data(self):
        pass

class SMA(Indicator):

    def __init__(self, data: pd.Series, period: int = 9):
        Indicator.__init__(self, data.index)
        self.key = 'sma{}'.format(period)
        self.df[self.key] = data.rolling(window=period).mean()

    def data(self):
        return self.df[self.key]

class EMA(Indicator):

    def __init__(self, data: pd.Series, period: int = 9):
        Indicator.__init__(self, data.index)
        self.key = 'ema{}'.format(period)
        self.df[self.key] = data.ewm(span=period).mean()

    def data(self):
        return self.df[self.key]

class MACD(Indicator):

    def __init__(self, data: pd.Series, short_period: int, long_period: int, period: int):
        Indicator.__init__(self, data.index)
        
        self.short_period = short_period
        self.long_period = long_period
        self.period = period

        short_ema = EMA(data, short_period)
        long_ema = EMA(data, long_period)
        
        self.df['MACD'] = short_ema.data() - long_ema.data()
        self.df['signal'] = EMA(self.df['MACD'], period).data()

    def data(self):
        return (self.df['MACD'], self.df['signal'])

class RSI(Indicator):

    def __init__(self, data: pd.Series, period: int = 14):
        Indicator.__init__(self, data.index)

        rsi = pd.DataFrame(index=data.index)
        rsi['close'] = data

        # différence pour avoir la fluctuation
        rsi['diff'] = rsi['close'].diff()
        
        # calcul de la première moyenne de gains et de pertes
        # on saute la première valeur qui est un NaN à cause du diff
        firstgain = rsi['diff'].iloc[1:period + 1][rsi['diff'] > 0.0].sum() / period
        firstloss = rsi['diff'].iloc[1:period + 1][rsi['diff'] < 0.0].sum() / period

        # initialisation de deux colonnes contenant les gains et les pertes moyens
        rsi['avg_gain'] = 0.0
        rsi['avg_loss'] = 0.0

        # ajout des premiers gains et pertes
        rsi['avg_gain'].iloc[period - 1] = firstgain
        rsi['avg_loss'].iloc[period - 1] = firstloss

        # les gains et pertes suivants sont calculés en lissant les valeurs avec la formule suivante :
        # nouveau gain moyen = ((gain moyen précédent / période -1) + nouveau gain) / période
        # et de même pour les pertes.
        tmpgain = firstgain
        tmploss = firstloss
        for index, row in rsi[period - 1:].iterrows():
            newloss = tmploss * (period - 1)
            newgain = tmpgain * (period - 1)
            if row['diff'] < 0:    
                newloss = newloss + row['diff']
            else:
                newgain = newgain + row['diff']
            newloss = newloss / period
            newgain = newgain / period
            row['avg_loss'] = newloss
            row['avg_gain'] = newgain
            tmploss = newloss
            tmpgain = newgain

        rs = rsi['avg_gain'] / abs(rsi['avg_loss'])
        self.df['rsi'] = 100.0 - (100.0 / ( 1.0 + rs))

    def data(self):
        return self.df['rsi']

class BollingerBands(Indicator):

    def __init__(self, data: pd.Series, period: int = 20, std: int = 2):
        Indicator.__init__(self, data.index)
        self.df['close'] = data
        self.df['ma'] =  self.df['close'].rolling(window=period).mean()
        self.df['upper'] = self.df['ma'] + (self.df['close'].rolling(window=period).std(ddof=0) * std)
        self.df['lower'] = self.df['ma'] - (self.df['close'].rolling(window=period).std(ddof=0) * std)

    def data(self):
        return self.df['ma'], self.df['upper'], self.df['lower']