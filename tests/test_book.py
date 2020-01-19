import unittest
import random
import math
from unittest.mock import MagicMock
from mongomock import MongoClient
import live
from api.binance import Binance, OrderSide, OrderType, OrderStatus

class TestBook(unittest.TestCase):

    def setUp(self):
        client = MongoClient()
        self.db = client.binance
        self.api = MagicMock()

    def order(self, symbol, side: OrderSide, price, status: OrderStatus):
        api = Binance({})
        return {'symbol': symbol, 'side': side.name, 'status': status.name, 'price': str(price), 'orderId': random.randint(1000, 9999), 'transactTime': api.timestamp()}

    def report(self, symbol, side: OrderSide, orderid, status: OrderStatus, price):
        api = Binance({})
        return { "e": "executionReport", "E": api.timestamp(), "s": symbol, "c": "mUvoqJxFIILMdfAW5iGSOW", "S": side.name, "o": "LIMIT", "f": "GTC",
        "q": "0.1", "p": str(price), "P": "0.00000000", "F": "0.00000000", "g": -1, "C": None, "x": "NEW", "X": status.name, "r": "NONE",
        "i": orderid, "l": "0.00000000", "z": "0.00000000", "L": "0.00000000", "n": "0", "N": None, "T": 1499405658657, "t": -1, "I": 8641984,
        "w": True, "m": False, "M": False, "O": 1499405658657, "Z": "0.00000000", "Y": "0.00000000", "Q": "0.00000000" }

    def test_buy_and_sell(self):
        book = live.Book(self.api, self.db, 'BTCUSDT', 0.1)
        
        # Return BUY response from API
        self.api.order.return_value = 200, self.order('BTCUSDT', OrderSide.BUY, 6500, OrderStatus.FILLED)

        # Buying currency the first time should return True
        self.assertTrue(book.buy(6500))

        # API should have been called one time
        self.assertEqual(self.api.order.call_count, 1)
        self.assertEqual(self.api.order.call_args, (('BTCUSDT', OrderSide.BUY, OrderType.LIMIT, 0.1, 6500),))

        # Buying currency a second time should return False as we are already holding currency
        self.assertFalse(book.buy(6500))

        # API should not have been called a second time
        self.assertEqual(self.api.order.call_count, 1)

        # Return SELL response from API
        self.api.order.return_value = 200, self.order('BTCUSDT', OrderSide.SELL, 7000, OrderStatus.FILLED)

        # Selling currency the first time should return True
        self.assertTrue(book.sell(7000))

        # API should have been called a second time
        self.assertEqual(self.api.order.call_count, 2)
        self.assertEqual(self.api.order.call_args, (('BTCUSDT', OrderSide.SELL, OrderType.LIMIT, 0.1, 7000),))

        # Selling currency the second time should return False
        self.assertFalse(book.sell(7000))

        # API should not have been called a third time
        self.assertEqual(self.api.order.call_count, 2)

    def test_update(self):
        book = live.Book(self.api, self.db, 'BTCUSDT', 0.1)
        
        buyorder = self.order('BTCUSDT', OrderSide.BUY, 6500, OrderStatus.NEW)
        buyorderid = buyorder['orderId']

        # Return BUY response from API
        self.api.order.return_value = 200, buyorder

        # Buying currency the first time should return True
        self.assertTrue(book.buy(6500))

        # As order has not been FILLED, book holding should be False
        self.assertFalse(book.holding)

        # Update order with FILLED status
        report = self.report('BTCUSDT', OrderSide.BUY, buyorderid, OrderStatus.FILLED, 6500)
        book.update_order(report)

        # As order has not been FILLED, book holding should be True
        self.assertTrue(book.holding)

        sellorder = self.order('BTCUSDT', OrderSide.SELL, 7000, OrderStatus.NEW)
        sellorderid = sellorder['orderId']

        # Return BUY response from API
        self.api.order.return_value = 200, sellorder

        # Selling currency the first time should return True
        self.assertTrue(book.sell(7000))

        # As order has not been FILLED, book holding should be True
        self.assertTrue(book.holding)

        # Update order with FILLED status
        report = self.report('BTCUSDT', OrderSide.SELL, sellorderid, OrderStatus.FILLED, 7000)
        book.update_order(report)

        # As order has not been FILLED, book holding should be False
        self.assertFalse(book.holding)

        # New quantity should be adjusted with PnL
        self.assertTrue(math.isclose(book.quantity, 0.10769))
