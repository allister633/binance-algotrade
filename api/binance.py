import asyncio
import websockets
import datetime
import time
import random
from enum import Enum

import http.client, urllib.parse
import hmac, hashlib
import json

import pandas as pd

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

class BinanceAPI():

    def __init__(self, config, test=True):
        self.config = config

        if 'api' in self.config and 'apikey' in self.config['api'] and 'secretkey' in self.config['api']:
            self.apikey = self.config['api']['apikey']
            self.secretkey = self.config['api']['secretkey']
        self.test = test

    def exchangeinfo(self):
        conn = http.client.HTTPSConnection("api.binance.com")
        conn.request("GET", "/api/v3/exchangeInfo")
        r1 = conn.getresponse()
        data1 = r1.read()
        conn.close()
        
        return json.loads(data1)

    def getklines(self, symbol, interval, limit):
        conn = http.client.HTTPSConnection("api.binance.com")
        conn.request("GET", "/api/v3/klines?symbol=" + symbol + "&interval=" + interval + "&limit=" + str(limit))
        r1 = conn.getresponse()
        data1 = r1.read()
        conn.close()

        klines = json.loads(data1)

        df = pd.DataFrame(klines, columns=['time', 'open', 'high', 'low', 'close', 'volume', 'a', 'b', 'c', 'd', 'e', 'f'], dtype='float64')
        df['time'] = pd.to_datetime(df['time'], unit='ms')
        df = df.set_index('time')
        df = df.drop(columns=['a', 'b', 'c', 'd', 'e', 'f'])

        return df

    def getorder(self, symbol, orderid):
        conn = http.client.HTTPSConnection("api.binance.com")
        headers = {"X-MBX-APIKEY": self.apikey}
        timestamp = self.timestamp()
        params = urllib.parse.urlencode({"symbol": symbol, "orderId": orderid, "timestamp": timestamp})
        signature = hmac.new(bytes(self.secretkey, "latin-1"), bytes(params, "latin-1"), hashlib.sha256)
        params = urllib.parse.urlencode({"symbol": symbol, "orderId": orderid, "timestamp": timestamp, "signature": signature.hexdigest()})
        conn.request("GET", "/api/v3/order?" + params, headers=headers)
        r1 = conn.getresponse()

        data1 = r1.read()
        data = json.loads(data1)

        conn.close()

        return r1.status, data

    def getorders(self, symbol):
        conn = http.client.HTTPSConnection("api.binance.com")
        headers = {"X-MBX-APIKEY": self.apikey}
        timestamp = self.timestamp()
        params = urllib.parse.urlencode({"symbol": symbol, "timestamp": timestamp})
        signature = hmac.new(bytes(self.secretkey, "latin-1"), bytes(params, "latin-1"), hashlib.sha256)
        params = urllib.parse.urlencode({"symbol": symbol, "timestamp": timestamp, "signature": signature.hexdigest()})
        conn.request("GET", "/api/v3/allOrders?" + params, headers=headers)
        r1 = conn.getresponse()

        data1 = r1.read()
        data = json.loads(data1)

        conn.close()

        return data

    def time(self):
        conn = http.client.HTTPSConnection("api.binance.com")
        conn.request("GET", "/api/v3/time")
        r1 = conn.getresponse()

        data1 = r1.read()
        data = json.loads(data1)

        conn.close()

        return data

    def account(self):
        conn = http.client.HTTPSConnection("api.binance.com")
        headers = {"X-MBX-APIKEY": self.apikey}
        timestamp = self.timestamp()
        params = urllib.parse.urlencode({"timestamp": timestamp})
        signature = hmac.new(bytes(self.secretkey, "latin-1"), bytes(params, "latin-1"), hashlib.sha256)
        params = urllib.parse.urlencode({"timestamp": timestamp, "signature": signature.hexdigest()})
        conn.request("GET", "/api/v3/account?" + params, headers=headers)
        r1 = conn.getresponse()

        data1 = r1.read()
        data = json.loads(data1)

        conn.close()

        return data

    def order(self, symbol: str, side: str, type: str, quantity: float, price: float):
        if self.test == True:
            url = "/api/v3/order/test"
        else:
            url = "/api/v3/order"
        conn = http.client.HTTPSConnection("api.binance.com")
        headers = {"X-MBX-APIKEY": self.apikey, "Content-Type": "application/x-www-form-urlencoded"}
        timestamp = self.timestamp()
        params = urllib.parse.urlencode({
            "symbol": symbol,
            "side": side,
            "type": type,
            "timeInForce": "GTC",
            "quantity": quantity,
            "price": '{:.8f}'.format(price),
            "timestamp": timestamp
        })
        signature = hmac.new(bytes(self.secretkey, "latin-1"), bytes(params, "latin-1"), hashlib.sha256)
        params = params + "&" + urllib.parse.urlencode({"signature": signature.hexdigest()})

        conn.request("POST", url, params, headers=headers)
        r1 = conn.getresponse()

        data1 = r1.read()
        data = json.loads(data1)

        conn.close()

        # lorsqu'on est en mode test, l'API ne répond pas d'objet à l'ordre, on insère une fausse réponse
        if self.test == True:
            data = {'symbol': symbol, 'side': side, 'status': 'FILLED', 'price': str(price), 'orderId': random.randint(1000, 9999), 'transactTime': self.timestamp()}

        return r1.status, data

    def cancelorder(self, symbol: str, orderid):
        url = "/api/v3/order"
        conn = http.client.HTTPSConnection("api.binance.com")
        headers = {"X-MBX-APIKEY": self.apikey, "Content-Type": "application/x-www-form-urlencoded"}
        timestamp = self.timestamp()
        params = urllib.parse.urlencode({
            "symbol": symbol,
            "orderId": orderid,
            "timestamp": timestamp
        })
        signature = hmac.new(bytes(self.secretkey, "latin-1"), bytes(params, "latin-1"), hashlib.sha256)
        params = params + "&" + urllib.parse.urlencode({"signature": signature.hexdigest()})

        conn.request("DELETE", url, params, headers=headers)
        r1 = conn.getresponse()

        data1 = r1.read()
        data = json.loads(data1)

        conn.close()

        return r1.status, data

    def createlistenkey(self):
        conn = http.client.HTTPSConnection("api.binance.com")
        headers = {"X-MBX-APIKEY": self.apikey, "Content-Type": "application/x-www-form-urlencoded"}
        conn.request("POST", "/api/v3/userDataStream", headers=headers)
        r1 = conn.getresponse()

        data1 = r1.read()
        data = json.loads(data1)

        conn.close()

        return r1.status, data

    def pinglistenkey(self, listenkey):
        conn = http.client.HTTPSConnection("api.binance.com")
        headers = {"X-MBX-APIKEY": self.apikey, "Content-Type": "application/x-www-form-urlencoded"}
        conn.request("PUT", "/api/v3/userDataStream?listenKey={}".format(listenkey), headers=headers)
        r1 = conn.getresponse()

        data1 = r1.read()
        data = json.loads(data1)

        conn.close()

        return r1.status, data

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

    def timestamp(self):
        return int(time.time() * 1000)
