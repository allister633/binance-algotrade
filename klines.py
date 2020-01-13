import argparse
import os.path
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

    if os.path.isfile(path):
        df2 = pd.read_csv(path, index_col='time', parse_dates=True)
        df = df2.append(df)
        df = df.drop_duplicates()
        df = df.loc[~df.index.duplicated(keep='last')]

    f = open(path, 'w+')
    df.to_csv(f)
    f.close()

if __name__ == "__main__":
    main()
