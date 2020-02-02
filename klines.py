import argparse
import pandas as pd
from datetime import datetime, timedelta, timezone
from api.binance import Binance, Intervals
import utils

import time

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol")
    parser.add_argument("--interval", default="1m")
    parser.add_argument("--start")
    parser.add_argument("--end")
    args = parser.parse_args()

    if args.interval not in Intervals:
        print("Invalid interval", args.interval)
        exit(1)

    delta = Intervals[args.interval]

    start = None
    if args.start != None:
        start = datetime.strptime(args.start, '%Y-%m-%dT%H:%M:%S')
        start = start.replace(tzinfo=timezone.utc)

    end = datetime.utcnow()
    if args.end != None:
        end = datetime.strptime(args.end, '%Y-%m-%dT%H:%M:%S')
        end = end.replace(tzinfo=timezone.utc)

    api = Binance({})
    status, data = api.getklines(args.symbol, args.interval, 1000, int(start.timestamp() * 1000) if start != None else None, int(end.timestamp() * 1000))
    df = utils.klinestodataframe(data)
    ohlc = df

    while data != []:
        newstart = df.index[-1] + delta

        status, data = api.getklines(args.symbol, args.interval, 1000, int(newstart.timestamp() * 1000) if start != None else None, int(end.timestamp() * 1000))

        if data != []:
            df = utils.klinestodataframe(data)
            ohlc = ohlc.append(df)

    path = "data/{}_{}_{}_{}.csv".format(args.symbol, start.strftime('%Y%m%d-%H%M%S'), end.strftime('%Y%m%d-%H%M%S'), args.interval)

    f = open(path, 'w+')
    ohlc.to_csv(f)
    f.close()

if __name__ == "__main__":
    main()
