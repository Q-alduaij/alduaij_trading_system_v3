from __future__ import annotations
import pandas as pd, numpy as np

def _sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period, min_periods=period).mean()

def run(data: pd.DataFrame, config: dict | None = None) -> dict:
    if config is None: config = {}
    fast = int(config.get("fast", 10))
    slow = int(config.get("slow", 30))
    if slow <= fast: slow = max(fast+1, 20)

    df = data.copy()
    for col in ("timestamp","open","high","low","close","volume"):
        if col not in df.columns: raise ValueError(f"missing required column: {col}")
    df = df.sort_values("timestamp").reset_index(drop=True)
    df["sma_fast"] = _sma(df["close"], fast)
    df["sma_slow"] = _sma(df["close"], slow)
    df["signal"] = 0
    df.loc[df["sma_fast"]>df["sma_slow"],"signal"]=1
    df.loc[df["sma_fast"]<df["sma_slow"],"signal"]=-1
    df["signal"]=df["signal"].fillna(0)

    df["pos"] = 0
    cross_up = (df["signal"].shift(1) <= 0) & (df["signal"] > 0)
    cross_dn = (df["signal"].shift(1) >= 0) & (df["signal"] < 0)
    df.loc[cross_up,"pos"]=1
    df.loc[cross_dn,"pos"]=0
    import numpy as _np
    df["pos"]=df["pos"].replace(0,_np.nan).ffill().fillna(0)

    df["ret"]=df["close"].pct_change().fillna(0.0)
    df["pnl"]=df["ret"]*df["pos"]
    trades=int(cross_up.sum())
    pnl_in_pos=df.loc[df["pos"]==1,"pnl"]
    wins=int((pnl_in_pos>0).sum())
    losses=int((pnl_in_pos<0).sum())
    total=float(df["pnl"].sum())
    return {"trades":trades,"wins":wins,"losses":losses,"pnl":total,"summary":f"SMA({fast},{slow}) trades={trades} pnl={total:.6f}"}
