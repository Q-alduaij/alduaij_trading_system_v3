from __future__ import annotations
from typing import Literal, Optional
import pandas as pd

Side = Literal["buy","sell","flat"]

def _copy_rates(mt5, symbol: str, timeframe, bars: int = 200) -> Optional[pd.DataFrame]:
    r = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
    if r is None: return None
    df = pd.DataFrame(r)
    if "time" in df.columns:
        df["timestamp"] = pd.to_datetime(df["time"], unit="s", utc=True)
    return df[["timestamp","open","high","low","close","tick_volume"]].rename(columns={"tick_volume":"volume"})

def _tf_to_mt5(mt5, tf: str):
    tf = tf.upper()
    mapping = {"M1": mt5.TIMEFRAME_M1,"M5": mt5.TIMEFRAME_M5,"M15": mt5.TIMEFRAME_M15,"M30": mt5.TIMEFRAME_M30,"H1": mt5.TIMEFRAME_H1}
    return mapping.get(tf, mt5.TIMEFRAME_M1)

def _sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period, min_periods=period).mean()

def last_signal(symbol: str, timeframe: str="M1", fast: int=10, slow: int=30) -> Side:
    import MetaTrader5 as mt5
    if not mt5.symbol_select(symbol, True): return "flat"
    tf = _tf_to_mt5(mt5, timeframe)
    df = _copy_rates(mt5, symbol, tf, bars=max(slow*3, 200))
    if df is None or df.empty: return "flat"
    df = df.sort_values("timestamp").reset_index(drop=True)
    df["sma_fast"] = _sma(df["close"], fast)
    df["sma_slow"] = _sma(df["close"], slow)
    row = df.iloc[-1]
    if pd.isna(row["sma_fast"]) or pd.isna(row["sma_slow"]): return "flat"
    if row["sma_fast"] > row["sma_slow"]: return "buy"
    if row["sma_fast"] < row["sma_slow"]: return "sell"
    return "flat"
