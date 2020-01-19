import unittest

from api.binance import Binance, OrderSide, OrderType
import utils

class TestBinanceAPI(unittest.TestCase):

    def setUp(self):
        apiKey = 'vmPUZE6mv9SD5VNHk4HlWFsOr6aKE2zvsw0MuIgwCIPy6utIco14y7Ju91duEh8A'
        secretKey =	'NhqPtmdSJYdKjVHjA7PZj4Mge3R5YNiP1e3UZjInClVN65XAbvqqM6A7H5fATj0j'
        config = {}
        config['api'] = {}
        config['api']['apikey'] = apiKey
        config['api']['secretkey'] = secretKey
        self.api = Binance(config)

    def test_exchangeinfo(self):
        status, data = self.api.exchangeinfo()
        self.assertEqual(status, 200)
        self.assertTrue('timezone' in data)
        self.assertTrue('serverTime' in data)
        self.assertTrue('rateLimits' in data)
        self.assertTrue('symbols' in data)

    def test_time(self):
        status, data = self.api.time()
        self.assertEqual(status, 200)
        self.assertTrue('serverTime' in data)

    def test_getklines(self):
        status, data = self.api.getklines('BTCUSDT', '1m', 10)

        df = utils.klinestodataframe(data)

        self.assertEqual(status, 200)
        self.assertEqual(len(df), 10)

    def test_order(self):
        status, data = self.api.order('BTCUSDT', OrderSide.BUY, OrderType.LIMIT, 1.0, 7500)
        self.assertEqual(status, 401)
        self.assertEqual(data['code'], -2015)

    def test_getorders(self):
        status, data = self.api.getorders('BTCUSDT')
        self.assertEqual(status, 401)
        self.assertEqual(data['code'], -2015)

    def test_getorder(self):
        status, data = self.api.getorder('BTCUSDT', 4242)
        self.assertEqual(status, 401)
        self.assertEqual(data['code'], -2015)

    def test_cancelorder(self):
        status, data = self.api.cancelorder('BTCUSDT', 4242)
        self.assertEqual(status, 401)
        self.assertEqual(data['code'], -2015)

    def test_account(self):
        status, data = self.api.account()
        self.assertEqual(status, 401)
        self.assertEqual(data['code'], -2015)

    def test_listenkey(self):
        status, data = self.api.createlistenkey()
        self.assertEqual(status, 401)
        self.assertEqual(data['code'], -2015)

if __name__ == '__main__':
    unittest.main()
