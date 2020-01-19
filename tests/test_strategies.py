import unittest
import pandas as pd
import numpy as np
import math
from datetime import datetime

import indicators
import strategies

class TestStrategies(unittest.TestCase):
    """Tests strategies."""

    def setUp(self):
        self.ohlc = pd.read_csv('tests/data/BTCUSDT_15m.csv', index_col='time', parse_dates=True)

    def test_buy_and_hold(self):
        strategy = strategies.BuyAndHoldStrategy(self.ohlc.close)

        result = strategy.backtest(self.ohlc.close)

        self.assertEqual(result.start, datetime(2020, 1, 8, 1, 30, 0))
        self.assertEqual(result.end, datetime(2020, 1, 18, 11, 15, 0))
        self.assertEqual(result.trades, 1)
        self.assertTrue(math.isclose(result.netret, 6.14, rel_tol=1e-02))
        self.assertTrue(math.isclose(result.sharpe, 0.0191, rel_tol=1e-03))
        self.assertTrue(math.isclose(result.maxdrawdown, -8.74, rel_tol=1e-02))
        self.assertEqual(result.maxdrawdownduration, 527)

    def test_avg_cross(self):
        sma9 = indicators.SMA(self.ohlc.close, period=9)
        sma21 = indicators.SMA(self.ohlc.close, period=21)
        strategy = strategies.AvgCrossStrategy(self.ohlc.close, sma9.df.sma9, sma21.df.sma21)
        
        result = strategy.backtest(self.ohlc.close)

        self.assertEqual(result.start, datetime(2020, 1, 8, 1, 30, 0))
        self.assertEqual(result.end, datetime(2020, 1, 18, 11, 15, 0))
        self.assertEqual(result.trades, 27)
        self.assertTrue(math.isclose(result.netret, 9.8, rel_tol=1e-02))
        self.assertTrue(math.isclose(result.sharpe, 0.0533, rel_tol=1e-03))
        self.assertTrue(math.isclose(result.maxdrawdown, -3.94, rel_tol=1e-02))
        self.assertEqual(result.maxdrawdownduration, 207)
        

    def test_RSI(self):
        rsi = indicators.RSI(self.ohlc.close, period=9)
        strategy = strategies.RSIStrategy(self.ohlc, rsi)

        result = strategy.backtest(self.ohlc.close)

        self.assertEqual(result.start, datetime(2020, 1, 8, 1, 30, 0))
        self.assertEqual(result.end, datetime(2020, 1, 18, 11, 15, 0))
        self.assertEqual(result.trades, 11)
        self.assertTrue(math.isclose(result.netret, 12.81, rel_tol=1e-02))
        self.assertTrue(math.isclose(result.sharpe, 0.1164, rel_tol=1e-03))
        self.assertTrue(math.isclose(result.maxdrawdown, -4.0, rel_tol=1e-02))
        self.assertEqual(result.maxdrawdownduration, 174)

    def test_MACD(self):
        macd = indicators.MACD(self.ohlc.close, 12, 26, 9)
        strategy = strategies.MACDStrategy(self.ohlc, macd)

        result = strategy.backtest(self.ohlc.close)

        self.assertEqual(result.start, datetime(2020, 1, 8, 1, 30, 0))
        self.assertEqual(result.end, datetime(2020, 1, 18, 11, 15, 0))
        self.assertEqual(result.trades, 41)
        self.assertTrue(math.isclose(result.netret, 22.39, rel_tol=1e-02))
        self.assertTrue(math.isclose(result.sharpe, 0.1409, rel_tol=1e-03))
        self.assertTrue(math.isclose(result.maxdrawdown, -2.97, rel_tol=1e-02))
        self.assertEqual(result.maxdrawdownduration, 156)

    def test_RSI_MACD(self):
        rsi = indicators.RSI(self.ohlc.close, period=9)
        macd = indicators.MACD(self.ohlc.close, 12, 26, 9)
        strategy = strategies.RSIMACDStrategy(self.ohlc, rsi, macd)

        result = strategy.backtest(self.ohlc.close)

        self.assertEqual(result.start, datetime(2020, 1, 8, 1, 30, 0))
        self.assertEqual(result.end, datetime(2020, 1, 18, 11, 15, 0))
        self.assertEqual(result.trades, 41)
        self.assertTrue(math.isclose(result.netret, 26.06, rel_tol=1e-02))
        self.assertTrue(math.isclose(result.sharpe, 0.1297, rel_tol=1e-03))
        self.assertTrue(math.isclose(result.maxdrawdown, -2.85, rel_tol=1e-02))
        self.assertEqual(result.maxdrawdownduration, 82)

if __name__ == '__main__':
    unittest.main()
