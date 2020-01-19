import argparse
import pandas as pd
from api.binance import Binance
import utils

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol")
    parser.add_argument("--interval", default="1m")
    args = parser.parse_args()
    
    path = 'data/' + args.symbol + '_' + args.interval + '.csv'

    api = Binance({})
    status, data = api.getklines(args.symbol, args.interval, 1000)
    df = utils.klinestodataframe(data)

    f = open(path, 'w+')
    df.to_csv(f)
    f.close()

if __name__ == "__main__":
    main()
