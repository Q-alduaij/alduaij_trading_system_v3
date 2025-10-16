# utils/mt5_sanity_check.py
import os, sys
from datetime import datetime
import pandas as pd
import MetaTrader5 as mt5

SYMBOLS = os.getenv("DIAG_SYMBOLS","XAGUSD,EURUSD,AUDCHF").split(",")
TF_NAME = os.getenv("DIAG_TF","TIMEFRAME_H1")
TIMEFRAME = getattr(mt5, TF_NAME)

def load(symbol, bars=500):
    rates = mt5.copy_rates_from_pos(symbol, TIMEFRAME, 0, bars)
    if rates is None:
        return None
    df = pd.DataFrame(rates)
    if df.empty:
        return df
    df["time"] = pd.to_datetime(df["time"], unit="s")
    return df

def main():
    if not mt5.initialize():
        print("MT5 init failed:", mt5.last_error()); sys.exit(1)
    info = mt5.terminal_info()
    print("MT5 connected:", bool(info), "| account:", getattr(info,'login',None))

    for s in [x.strip() for x in SYMBOLS if x.strip()]:
        df = load(s)
        if df is None or df.empty:
            print(f"[{s}] no data")
            continue
        close = df["close"].astype(float)
        rng = (df["high"].max()-df["low"].min())/close.iloc[-1]
        atr = (df["high"]-df["low"]).rolling(14).mean().iloc[-1]/close.iloc[-1]
        print(f"[{s}] rows={len(df)} last={df['time'].iloc[-1]} rng%={rng:.3%} atr14%={atr:.3%}")
    mt5.shutdown()

if __name__ == "__main__":
    main()
