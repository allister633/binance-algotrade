import argparse
import logging
import datetime
import time
import json
import websockets
import socket
import time

import pandas as pd

from pymongo import MongoClient

from api.binance import Binance, OrderStatus, OrderType, OrderSide
import strategies
import indicators
import utils

class Book():
    """Emits and persists buy and sell orders.
    Calculates profit and loss, and adjusts initial quantity.
    """

    def __init__(self, api, db, symbol, quantity):
        self.api = api
        self.db = db
        self.symbol = symbol
        self.quantity = float(quantity)
        # indique si on possède de la devise
        self.holding = False
        # contient les ordres de cette session indexés par orderId
        self.orders = {}
        self.lastbuyorderid = None
        self.lastsellorderid = None

        # récupère le dernier ordree, si c'est un ordre d'achat, on le retient
        cursor = self.db.orders.find({'symbol' : self.symbol}).limit(1).sort('transactTime', -1)
        if cursor.count() > 0:
            order = cursor.next()
            if order['side'] == 'BUY':
                logging.info("Retrieving last BUY order {}".format(order))
                self.orders[order['orderId']] = order
                self.lastbuyorderid = order['orderId']
                self.holding = True

    def buy(self, price) -> bool:
        """Emits a buy order and perists it in the database.
        Returns True if the brocker accepted the order.
        The order is sent only if we are not holding the currency.
        """

        # on ne rachète pas de devise si on en possède déjà
        if self.holding == False:

            # s'il y a déjà eu un ordre d'achat et qu'il n'a été FILLED, on l'annule
            if self.lastbuyorderid != None:
                if self.orders[self.lastbuyorderid]['status'] != OrderStatus.FILLED.name:
                    logging.info("Cancelling last unfilled BUY order {}".format(self.lastbuyorderid))
                    status, data = self.api.cancelorder(self.symbol, self.lastbuyorderid)
                    if status == 200:
                        logging.info("Successfuly canceled order {}".format(self.lastbuyorderid))
                        del self.orders[self.lastbuyorderid]
                        self.lastbuyorderid = None
                    else:
                        logging.error("Could not cancel order {} : {}".format(self.lastbuyorderid, data))
                        return

            status, order = self.api.order(self.symbol, OrderSide.BUY, OrderType.LIMIT, self.quantity, price)
            if status == 200:
                logging.info("Order sent {}".format(order))

                order['transactTime'] = datetime.datetime.utcfromtimestamp(order['transactTime'] / 1000)

                if order['status'] == OrderStatus.FILLED.name or order['status'] == OrderStatus.PARTIALLY_FILLED.name:
                    self.holding = True

                self.orders[order['orderId']] = order
                self.lastbuyorderid = order['orderId']

                self.db.orders.insert_one(order)

                return True
            else:
                logging.error("Could not send order : {}".format(order))

        return False

    def sell(self, price) -> bool:
        """Emits a sell order and perists it in the database.
        Returns True if the brocker accepted the order.
        The order is sent only if we are holding the currency.
        """

        # on vend seulement si le dernier ordre d'achat a été FILLED et que l'on possède de la devise
        if self.lastbuyorderid != None and self.holding == True:

            # s'il y a déjà eu un ordre de vente et qu'il n'a été FILLED ou PARTIALLY_FILLED, on l'annule
            if self.lastsellorderid != None:
                if self.orders[self.lastsellorderid]['status'] != OrderStatus.FILLED.name and self.orders[self.lastsellorderid]['status'] != OrderStatus.PARTIALLY_FILLED.name:
                    logging.info("Cancelling last unfilled SELL order {}".format(self.lastbuyorderid))
                    status, data = self.api.cancelorder(self.symbol, self.lastsellorderid)
                    if status == 200:
                        logging.info("Successfuly canceled order {}".format(self.lastsellorderid))
                        del self.orders[self.lastsellorderid]
                        self.lastsellorderid = None
                    else:
                        logging.error("Could not cancel order {} : {}".format(self.lastsellorderid, data))
                        return

            if self.orders[self.lastbuyorderid]['status'] == OrderStatus.FILLED.name or self.orders[self.lastbuyorderid]['status'] == OrderStatus.PARTIALLY_FILLED.name:
                # Attention : s'assurer que le compte contient une quantité de BNB pour couvrir les commissions

                # on récupère la quantité achetée
                if "filledQuantity" in self.orders[self.lastbuyorderid]:
                    quantity = self.orders[self.lastbuyorderid]["filledQuantity"]
                else:
                    quantity = self.quantity

                status, order = self.api.order(self.symbol, OrderSide.SELL, OrderType.LIMIT, quantity, price)
                if status == 200:
                    logging.info("Order sent {}".format(order))

                    order['transactTime'] = datetime.datetime.utcfromtimestamp(order['transactTime'] / 1000)

                    if order['status'] == OrderStatus.FILLED.name or order['status'] == OrderStatus.PARTIALLY_FILLED.name:
                        self.holding = False

                    self.orders[order['orderId']] = order
                    self.lastsellorderid = order['orderId']
                    
                    self.db.orders.insert_one(order)

                    return True
                else:
                    logging.error("Could not send order : {}".format(order))

        return False

    def calcpnl(self):
        if self.lastsellorderid != None and self.lastbuyorderid != None:
            lastsellprice = float(self.orders[self.lastsellorderid]['price'])
            lastbuyprice = float(self.orders[self.lastbuyorderid]['price'])

            pnl = ((lastsellprice - lastbuyprice) / lastbuyprice) * 100.0
            self.quantity = self.quantity + (self.quantity * pnl / 100.0)
            self.quantity = round(self.quantity, 5)

            logging.info("{} - PnL {}, new quantity {}".format(self.symbol, pnl, self.quantity))

    def update_order(self, data):
        logging.info("{}".format(data))

        order = {}
        order['symbol'] = data['s']
        order['side'] = data['S']
        order['status'] = data['X']
        order['price'] = data['p']
        order['orderId'] = data['i']
        order['transactTime'] = data['T']
        order['orderQuantity'] = float(data['q'])
        order['filledQuantity'] = float(data['z'])

        self.filledquantity = order['filledQuantity']

        order['transactTime'] = datetime.datetime.utcfromtimestamp(order['transactTime'] / 1000)

        if order['orderId'] in self.orders:
            self.orders[order['orderId']] = order

            storedorder = self.db.orders.find_one({'orderId' : order['orderId']})
            if storedorder != None:
                self.db.orders.replace_one({'_id' : storedorder.get('_id')}, order)

            logging.info("Order updated {}".format(order))
        else:
            logging.info("Unkown order {}".format(order))

        # si l'ordre concerne le dernier ordre de vente
        if self.lastsellorderid != None and self.lastsellorderid == order['orderId']:

            # s'il est FILLED, ça veut dire qu'on ne detient plus de devise, on pourra donc en racheter
            if self.orders[self.lastsellorderid]['status'] == OrderStatus.FILLED.name or self.orders[self.lastsellorderid]['status'] == OrderStatus.PARTIALLY_FILLED.name:
                self.holding = False
                self.calcpnl()

        # si l'ordre concerne le dernier ordre d'achat
        if self.lastbuyorderid != None and self.lastbuyorderid == order['orderId']:

            # s'il est FILLED, ça veut dire qu'on detient de la devise, on ne pourra donc pas en racheter
            if self.orders[self.lastbuyorderid]['status'] == OrderStatus.FILLED.name or self.orders[self.lastbuyorderid]['status'] == OrderStatus.PARTIALLY_FILLED.name:
                self.holding = True

class LiveTicker():

    def __init__(self, api, db, symbol, interval, quantity):
        self.symbol = symbol
        self.interval = interval
        # Indique si on est au lancement, on attend de passer par un tendance baissière avant d'achater
        self.startup = True
        self.lasttimetick = None

        self.book = Book(api, db, symbol, quantity)
        status, data = api.getklines(self.symbol.upper(), self.interval, 500)
        self.df = utils.klinestodataframe(data)

        #self.rsi = indicators.RSI(self.df['open'], 9)
        #self.macd = indicators.MACD(self.df['open'], 12, 26, 9)
        self.bb1 = indicators.BollingerBands(self.df['close'], 20, 1)
        self.bb2 = indicators.BollingerBands(self.df['close'], 20, 2)

    def updateindicators(self):
        #self.rsi = indicators.RSI(self.df['open'], 9)
        #self.macd = indicators.MACD(self.df['open'], 12, 26, 9)
        #logging.info("{} - RSI {} MACD {} MACD SIGNAL {}".format(self.symbol, self.rsi.df.iloc[-1]['rsi'], self.macd.df.iloc[-1]['MACD'], self.macd.df.iloc[-1]['signal']))
        self.bb1 = indicators.BollingerBands(self.df['open'], 20, 1)
        self.bb2 = indicators.BollingerBands(self.df['open'], 20, 2)

    def runstrategy(self):
        #self.strategy = strategies.RSIMACDStrategy(self.df, self.rsi, self.macd)
        self.strategy = strategies.DBBStrategy(self.df['open'], self.bb1, self.bb2)

    def act(self, time, price):
        if self.strategy.signals['signal'].loc[time] == 1.0 and self.startup == False:
            logging.info("{} - BUY signal at {}".format(self.symbol, price))

            return self.book.buy(price)
        elif self.strategy.signals['signal'].loc[time] == 0.0:
            logging.info("{} - SELL signal at {}".format(self.symbol, price))

            self.startup = False

            return self.book.sell(price)

        return False

    def update_price(self, data):
        time = datetime.datetime.utcfromtimestamp(data['k']['t'] / 1000)
        open, high, low, close, volume  = float(data['k']['o']), float(data['k']['h']), float(data['k']['l']), float(data['k']['c']), float(data['k']['v'])
        logging.debug("{} {} {} {}".format(time, data['e'], data['s'], close))

        if time != self.lasttimetick:
            self.df.loc[time] = 0.0

            self.df.loc[time]['close'] = close
            self.df.loc[time]['open'] = open
            self.df.loc[time]['high'] = high
            self.df.loc[time]['low'] = low
            self.df.loc[time]['volume'] = volume

            logging.info("{} - OPEN {} HIGH {} LOW {} CLOSE {}".format(self.symbol, open, high, low, close))

            # nouvelle chandelle
            # mise à jour des indicateurs
            self.updateindicators()
            # la stratégie détermine les signaux d'achat / vente
            self.runstrategy()
            self.act(time, open)   
        else:
            self.df.loc[time]['close'] = close
            self.df.loc[time]['open'] = open
            self.df.loc[time]['high'] = high
            self.df.loc[time]['low'] = low
            self.df.loc[time]['volume'] = volume

        self.lasttimetick = time

class Router():

    def __init__(self, config, api, db, listenkey):
        self.tickers = {}
        self.api = api
        for key in config['pairs']:
            symbol = key
            interval = config['pairs'][key]['interval']
            quantity = config['pairs'][key]['quantity']
            ticker = LiveTicker(api, db, symbol, interval, quantity)
            self.tickers[symbol] = ticker

        # toutes les 30 minutes on ping la clé
        self.listenkey = listenkey
        self.lastlistenkeyupdate = None
        self.listenkeyupdateperiod = datetime.timedelta(minutes=30)

    def route(self, stream, data):
        eventtype = data['e']
        eventtime = data['E']
        eventtime = datetime.datetime.utcfromtimestamp(eventtime / 1000)

        if eventtype == 'kline':
            symbol = stream.split("@")[0].upper()

            if symbol in self.tickers:
                ticker = self.tickers[symbol]
                ticker.update_price(data)
            else:
                logging.error("Unrecognized stream {}".format(stream))

        elif eventtype == 'executionReport':
            symbol = data['s']

            if symbol in self.tickers:
                ticker = self.tickers[symbol]
                ticker.book.update_order(data)

        else:
            logging.info("Unhandled event{}".format(eventtype))

        # mise à jour de la listen key
        if self.lastlistenkeyupdate == None:
            self.lastlistenkeyupdate = eventtime
        elif eventtime - self.lastlistenkeyupdate > self.listenkeyupdateperiod:
            logging.info("Updating listen key")
            status, data = self.api.pinglistenkey(self.listenkey)
            if status == 200:
                self.lastlistenkeyupdate = eventtime
            else:
                logging.info("Could not update listen key : {}".format(data))

def subscribe(api, router, listenkey):
    try:
        api.subscribe(router.route, listenkey=listenkey)
    except (socket.gaierror, websockets.exceptions.ConnectionClosedError) as e:
        logging.error(e)
        time.sleep(30)
        subscribe(api, router, listenkey)

def main():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO, filename='live.log')

    parser = argparse.ArgumentParser()
    parser.add_argument("--no-test", action='store_false', dest='test')
    parser.set_defaults(test=True, dropdb=False)
    args = parser.parse_args()
    
    f = open('config.json', 'r')
    config = json.load(f)
    f.close()

    api = Binance(config, args.test)

    client = MongoClient(config['db']['host'])
    db = client[config['db']['name']]

    conn, data = api.createlistenkey()
    if conn == 200:
        listenkey = data['listenKey']
        router = Router(config, api, db, listenkey)
        subscribe(api, router, listenkey)

if __name__ == "__main__":
    main()
