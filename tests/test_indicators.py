import unittest
import pandas as pd
import numpy as np

import indicators

class TestStringMethods(unittest.TestCase):
    """Tests indicators against TA-Lib output data."""

    def setUp(self):
        self.ohlc = pd.read_csv('tests/data/BTCUSDT_15m.csv', index_col='time', parse_dates=True)

    def test_SMA(self):
        sma = pd.read_csv('tests/data/BTCUSDT_15m_SMA9.csv', index_col='time', parse_dates=True)
        mysma = indicators.SMA(self.ohlc.close, period=9)
        isclose = np.isclose(sma.sma9, mysma.df.sma9, equal_nan=True)
        self.assertTrue(np.all(isclose))

    def test_BBANDS(self):
        bbands = pd.read_csv('tests/data/BTCUSDT_15m_BBANDS5.csv', index_col='time', parse_dates=True)
        mybbands = indicators.BollingerBands(self.ohlc.close, period=5)
        ismiddlebandclose = np.isclose(bbands.middleband, mybbands.df.ma, equal_nan=True)
        islowerbandclose = np.isclose(bbands.lowerband, mybbands.df.lower, equal_nan=True)
        isupperbandclose = np.isclose(bbands.upperband, mybbands.df.upper, equal_nan=True)
        self.assertTrue(np.all(ismiddlebandclose))
        self.assertTrue(np.all(islowerbandclose))
        self.assertTrue(np.all(isupperbandclose))

    def test_EMA(self):
        ema = pd.read_csv('tests/data/BTCUSDT_15m_EMA21.csv', index_col='time', parse_dates=True)
        myema = indicators.EMA(self.ohlc.close, period=21)
        # consider first 100 values as warmup
        isclose = np.isclose(ema.ema21.iloc[100:], myema.df.ema21.iloc[100:], equal_nan=True)
        self.assertTrue(np.all(isclose))

    def test_MACD(self):
        macd = pd.read_csv('tests/data/BTCUSDT_15m_MACD_12_26_9.csv', index_col='time', parse_dates=True)
        mymacd = indicators.MACD(self.ohlc.close, short_period=12, long_period=26, period=9)
        # consider first 250 values as warmup
        ismacdclose = np.isclose(macd.macd.iloc[250:], mymacd.df.MACD.iloc[250:], equal_nan=True)
        ismacdsignalclose = np.isclose(macd.macdsignal.iloc[250:], mymacd.df.signal.iloc[250:], equal_nan=True)
        self.assertTrue(np.all(ismacdclose))
        self.assertTrue(np.all(ismacdsignalclose))

    def test_RSI(self):
        rsi = pd.read_csv('tests/data/BTCUSDT_15m_RSI9.csv', index_col='time', parse_dates=True)
        myrsi = indicators.RSI(self.ohlc.close, period=9)
        isclose = np.isclose(rsi.rsi.iloc[100:], myrsi.df.rsi.iloc[100:], equal_nan=True)
        # consider first 100 values as warmup
        self.assertTrue(np.all(isclose))

if __name__ == '__main__':
    unittest.main()
