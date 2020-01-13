import pandas as pd

def klinestodataframe(klines):
    df = pd.DataFrame(klines, columns=['time', 'open', 'high', 'low', 'close', 'volume', 'a', 'b', 'c', 'd', 'e', 'f'], dtype='float64')
    df['time'] = pd.to_datetime(df['time'], unit='ms')
    df = df.set_index('time')
    df = df.drop(columns=['a', 'b', 'c', 'd', 'e', 'f'])

    return df
