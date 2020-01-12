import argparse
import logging
import datetime
import time
import json
import threading

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

from pymongo import MongoClient

import strategies
import indicators

plt.style.use('ggplot')

class LiveTicker():

    def __init__(self, db, symbol):
        logging.basicConfig(level=logging.INFO)
        self.db = db
        self.symbol = symbol
        

        cursor = self.db.candles.find({ 'symbol' : self.symbol })
        self.df = pd.DataFrame(list(cursor), columns=['time', 'close'])
        self.df = self.df.set_index('time')

        self.add_indicators()

        cursor = self.db.orders.find({ 'symbol' : self.symbol })
        self.orders = pd.DataFrame(list(cursor), columns=['transactTime', 'side', 'status', 'price'])
        self.orders = self.orders.set_index('transactTime')
        self.orders['price'] = self.orders['price'].astype('float')

        print(self.orders, flush=True)
        print(self.orders.dtypes, flush=True)

    def watchorders(self):
        with self.db.orders.watch() as stream:
            for change in stream:
                doc = change['fullDocument']

                print(doc, flush=True)

                if doc['symbol'] == self.symbol:
                    transactTime = doc['transactTime']

                    if transactTime not in self.orders:
                        self.orders.loc[transactTime] = 0.0

                    self.orders.loc[transactTime]['side'] = doc['side']
                    self.orders.loc[transactTime]['status'] = doc['status']
                    self.orders.loc[transactTime]['price'] = doc['price']

                    print(self.orders, flush=True)

    def watchcandles(self):
        with self.db.candles.watch() as stream:
            for change in stream:
                doc = change['fullDocument']
                if doc['symbol'] == self.symbol:
                    time = doc['time']
                    close = doc['close']

                    if time not in self.df:
                        self.df.loc[time] = 0.0

                    self.df.loc[time]['close'] = close
                    self.add_indicators()


    def update(self, frame):
        #plt.clf()
        ln1, = self.ax1.plot(self.df['close'])
        ln2, = self.ax2.plot(self.rsi.df['rsi'])
        ln3, = self.ax3.plot(self.macd.df['MACD'])
        ln4, = self.ax3.plot(self.macd.df['signal'])
        #ln2, = plt.plot(self.df['ema9'], label='EMA9')
        #ln3, = plt.plot(self.df['ema21'], label='EMA21')
        #plt.plot(self.strategy.signals.loc[self.strategy.signals['positions'] == 1.0].index, self.df['sma9'].loc[self.strategy.signals['positions'] == 1.0], '^', markersize = 10, color = 'g')
        #plt.plot(self.strategy.signals.loc[self.strategy.signals['positions'] == -1.0].index, self.df['sma9'].loc[self.strategy.signals['positions'] == -1.0], 'v', markersize = 10, color = 'r')

        #plt.title(self.symbol + " " + self.interval)
        #plt.legend()

        s1, = self.ax1.plot(self.orders.loc[self.orders['side'] == 'BUY'].index, self.orders.loc[self.orders['side'] == 'BUY']['price'], '^', markersize = 10, color = 'g')
        s2, = self.ax1.plot(self.orders.loc[self.orders['side'] == 'SELL'].index, self.orders.loc[self.orders['side'] == 'SELL']['price'], 'v', markersize = 10, color = 'r')

        #if len(self.book.orders) > 0:
        #    book = self.book.getdataframe()
        #    s1, = plt.plot(book.loc[book['side'] == 'BUY'].index, book.loc[book['side'] == 'BUY']['price'], '^', markersize = 10, color = 'g')
        #    s2, = plt.plot(book.loc[book['side'] == 'SELL'].index, book.loc[book['side'] == 'SELL']['price'], 'v', markersize = 10, color = 'r')
        #    return ln1, ln2, ln3, s1, s2

        return ln1, ln2, ln3, ln4, s1, s2

    def draw(self):
        fig, (ax1, ax2, ax3) = plt.subplots(3, sharex=True)
        self.ax1 = ax1
        self.ax2 = ax2
        self.ax3 = ax3
        #ani = FuncAnimation(fig, self.update, interval=2000, blit=True)

        self.ax1.plot(self.df['close'])
        self.ax2.plot(self.rsi.df['rsi'])
        self.ax3.plot(self.macd.df['MACD'])
        self.ax3.plot(self.macd.df['signal'])
        self.ax1.plot(self.orders.loc[self.orders['side'] == 'BUY'].index, self.orders.loc[self.orders['side'] == 'BUY']['price'], '^', markersize = 10, color = 'g')
        self.ax1.plot(self.orders.loc[self.orders['side'] == 'SELL'].index, self.orders.loc[self.orders['side'] == 'SELL']['price'], 'v', markersize = 10, color = 'r')

        plt.show()

    def add_sma(self, period):
        self.df["sma" + str(period)] = self.df["close"].rolling(window=period).mean()

    def add_ema(self, period):
        self.df["ema" + str(period)] = self.df["close"].ewm(span=period).mean()

    def add_indicators(self):
        #self.add_ema(9)
        #self.add_ema(21)
        #self.strategy = strategies.CustomStrategy(self.df['close'], self.df['ema9'], self.df['ema21'])
        #return self.strategy
        self.rsi = indicators.RSI(self.df['close'], 9)
        self.macd = indicators.MACD(self.df['close'], 12, 26, 9)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol")
    args = parser.parse_args()

    f = open('config.json', 'r')
    config = json.load(f)
    f.close()

    client = MongoClient(config['db']['host'])

    db = client[config['db']['name']]
    lt = LiveTicker(db, args.symbol)

    #t1 = threading.Thread(target=lt.watchcandles)
    #t1.daemon = True
    #t1.start()

    #t2 = threading.Thread(target=lt.watchorders)
    #t2.daemon = True
    #t2.start()

    lt.draw()

if __name__ == "__main__":
    main()
