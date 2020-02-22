import asyncio
import websockets
from datetime import timedelta
import time
import random
from enum import Enum

import http.client, urllib.parse
import hmac, hashlib
import json

Intervals = {
    "1m" : timedelta(minutes=1),
    "3m" : timedelta(minutes=3),
    "5m" : timedelta(minutes=5),
    "15m" : timedelta(minutes=15),
    "30m" : timedelta(minutes=30),
    "1h" : timedelta(hours=1),
    "2h" : timedelta(hours=2),
    "4h" : timedelta(hours=4),
    "6h" : timedelta(hours=6),
    "8h" : timedelta(hours=8),
    "12h" : timedelta(hours=12),
    "1d" : timedelta(days=1),
    "3d" : timedelta(days=3),
    "1w" : timedelta(days=7),
    "1M" : timedelta(days=30),
}

class OrderStatus(Enum):
    NEW = 1
    PARTIALLY_FILLED = 2
    FILLED = 3
    CANCELED = 4
    PENDING_CANCEL = 5
    REJECTED = 6
    EXPIRED = 7

class OrderType(Enum):
    LIMIT = 1
    MARKET = 2
    STOP_LOSS = 3
    STOP_LOSS_LIMIT = 4
    TAKE_PROFIT = 5
    TAKE_PROFIT_LIMIT = 6
    LIMIT_MAKER = 7

class OrderSide(Enum):
    BUY = 1
    SELL = 2

class Binance():

    def __init__(self, config, test=True):
        self.config = config

        if 'api' in self.config and 'apikey' in self.config['api'] and 'secretkey' in self.config['api']:
            self.apikey = self.config['api']['apikey']
            self.secretkey = self.config['api']['secretkey']
        self.test = test

    def _request(self, method, url, body=None, headers={}):
        conn = http.client.HTTPSConnection("api.binance.com")
        conn.request(method, url, body, headers=headers)
        r1 = conn.getresponse()
        data1 = r1.read()
        conn.close()
        
        data = json.loads(data1)

        return r1.status, data

    def exchangeinfo(self):
        return self._request('GET', '/api/v3/exchangeInfo')

    def getklines(self, symbol, interval, limit, start = None, end = None):
        url = "/api/v3/klines?symbol={}&interval={}&limit={}".format(symbol, interval, limit)
        if start != None:
            url += "&startTime={}".format(start)
        if end != None:
            url += "&endTime={}".format(end)
        return self._request('GET', url)

    def getorder(self, symbol, orderid):
        timestamp = self.timestamp()
        params = urllib.parse.urlencode({"symbol": symbol, "orderId": orderid, "timestamp": timestamp})
        signature = hmac.new(bytes(self.secretkey, "latin-1"), bytes(params, "latin-1"), hashlib.sha256)
        params = urllib.parse.urlencode({"symbol": symbol, "orderId": orderid, "timestamp": timestamp, "signature": signature.hexdigest()})
        return self._request('GET', "/api/v3/order?{}".format(params), headers={"X-MBX-APIKEY": self.apikey})

    def getorders(self, symbol):
        timestamp = self.timestamp()
        params = urllib.parse.urlencode({"symbol": symbol, "timestamp": timestamp})
        signature = hmac.new(bytes(self.secretkey, "latin-1"), bytes(params, "latin-1"), hashlib.sha256)
        params = urllib.parse.urlencode({"symbol": symbol, "timestamp": timestamp, "signature": signature.hexdigest()})
        return self._request('GET', "/api/v3/allOrders?{}".format(params), headers={"X-MBX-APIKEY": self.apikey})

    def time(self):
        return self._request('GET', '/api/v3/time')

    def account(self):
        timestamp = self.timestamp()
        params = urllib.parse.urlencode({"timestamp": timestamp})
        signature = hmac.new(bytes(self.secretkey, "latin-1"), bytes(params, "latin-1"), hashlib.sha256)
        params = urllib.parse.urlencode({"timestamp": timestamp, "signature": signature.hexdigest()})
        return self._request('GET', "/api/v3/account?{}".format(params), headers={"X-MBX-APIKEY": self.apikey})

    def order(self, symbol: str, side: OrderSide, type: OrderType, quantity: float, price: float):
        if self.test == True:
            url = "/api/v3/order/test"
        else:
            url = "/api/v3/order"
        timestamp = self.timestamp()
        params = urllib.parse.urlencode({
            "symbol": symbol,
            "side": side.name,
            "type": type.name,
            "timeInForce": "GTC",
            "quantity": quantity,
            "price": '{:.8f}'.format(price),
            "timestamp": timestamp
        })
        signature = hmac.new(bytes(self.secretkey, "latin-1"), bytes(params, "latin-1"), hashlib.sha256)
        params = params + "&" + urllib.parse.urlencode({"signature": signature.hexdigest()})

        status, data = self._request('POST', url, params, headers={"X-MBX-APIKEY": self.apikey, "Content-Type": "application/x-www-form-urlencoded"})

        # lorsqu'on est en mode test, l'API ne répond pas d'objet à l'ordre, on insère une fausse réponse
        if self.test == True and status == 200:
            data = {'symbol': symbol, 'side': side.name, 'status': 'FILLED', 'price': str(price), 'orderId': random.randint(1000, 9999), 'transactTime': self.timestamp()}

        return status, data

    def cancelorder(self, symbol: str, orderid):
        url = "/api/v3/order"
        headers = {"X-MBX-APIKEY": self.apikey, "Content-Type": "application/x-www-form-urlencoded"}
        timestamp = self.timestamp()
        params = urllib.parse.urlencode({
            "symbol": symbol,
            "orderId": orderid,
            "timestamp": timestamp
        })
        signature = hmac.new(bytes(self.secretkey, "latin-1"), bytes(params, "latin-1"), hashlib.sha256)
        params = params + "&" + urllib.parse.urlencode({"signature": signature.hexdigest()})

        return self._request('DELETE', url, params, headers=headers)

    def createlistenkey(self):
        headers = {"X-MBX-APIKEY": self.apikey, "Content-Type": "application/x-www-form-urlencoded"}
        return self._request('POST', "/api/v3/userDataStream", headers=headers)

    def pinglistenkey(self, listenkey):
        headers = {"X-MBX-APIKEY": self.apikey, "Content-Type": "application/x-www-form-urlencoded"}
        return self._request('PUT', "/api/v3/userDataStream?listenKey={}".format(listenkey), headers=headers)

    async def ws(self, handler, symbol = None, interval = None, listenkey = None):
        if symbol == None and interval == None:
            uri = 'wss://stream.binance.com:9443/stream?streams='
            for key in self.config['pairs']:
                uri += "{}@kline_{}/".format(key.lower(), self.config['pairs'][key]['interval'])
            uri = uri[:-1]
        else:
            uri = 'wss://stream.binance.com:9443/ws/' + symbol.lower() + '@kline_' + interval

        if listenkey != None:
            uri += "/{}".format(listenkey)

        async with websockets.connect(
            uri, ssl=True
        ) as websocket:
            async for message in websocket:
                data = json.loads(message)
                handler(data['stream'], data['data'])

    def subscribe(self, handler, symbol = None, interval = None, listenkey = None):
        asyncio.get_event_loop().run_until_complete(self.ws(handler, symbol, interval, listenkey))

    def unsubscribe(self):
        asyncio.get_event_loop().stop()

    def timestamp(self):
        return int(time.time() * 1000)
