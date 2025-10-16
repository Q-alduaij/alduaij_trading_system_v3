# utils/mt5_force_history.py
import sys, time
import MetaTrader5 as mt5
import pandas as pd

def tf_map(name: str):
    return {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "H1": mt5.TIMEFRAME_H1,
    }.get(name.upper(), mt5.TIMEFRAME_M1)

if __name__ == "__main__":
    if not mt5.initialize():
        print("MT5 init failed")
        sys.exit(1)
    syms = sys.argv[1].split(",")
    tf = tf_map(sys.argv[2]) if len(sys.argv) > 2 else mt5.TIMEFRAME_M1
    count = int(sys.argv[3]) if len(sys.argv) > 3 else 1200

    for s in syms:
        ok = mt5.symbol_select(s, True)
        print(f"[{s}] select={ok}")
        df = pd.DataFrame(mt5.copy_rates_from_pos(s, tf, 0, count) or [])
        print(f"[{s}] tf={sys.argv[2] if len(sys.argv)>2 else 'M1'} rows={len(df)} "
              f"last={pd.to_datetime(df['time'].iloc[-1], unit='s') if len(df) else '—'}")
