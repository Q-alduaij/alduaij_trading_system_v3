# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import time
import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

import pandas as pd
import MetaTrader5 as mt5

from data.mt5_data import MT5Data

log = logging.getLogger(__name__)

# -------------------------------
# Helpers
# -------------------------------

_TIMEFRAMES = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
}

def _tf_to_mt5(tf: str):
    tf = (tf or "M1").upper()
    return _TIMEFRAMES.get(tf, mt5.TIMEFRAME_M1)

def _fmt_ts(ts: Optional[pd.Timestamp]) -> str:
    try:
        return "" if ts is None else str(pd.to_datetime(ts, unit="s"))
    except Exception:
        return ""

def _ensure_symbol(symbol: str) -> bool:
    # Subscribe the symbol to Market Watch so copy_rates works
    if not mt5.symbol_select(symbol, True):
        # Try adding a known suffix/prefix variants if broker uses them
        # (no-op here, just return False if first try failed)
        return False
    return True

def _download_bars(symbol: str, tf, count: int, attempts: int = 4, sleep_s: float = 0.6) -> pd.DataFrame:
    """
    Try a few times; some brokers only deliver data after the first request.
    """
    df: pd.DataFrame = pd.DataFrame()
    for i in range(attempts):
        rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
        if rates is not None and len(rates) > 0:
            df = pd.DataFrame(rates)
            break
        time.sleep(sleep_s)
    return df

def _fetch_bars_any(symbol: str, tf_primary: str, min_rows: int, need_rows: int) -> Tuple[pd.DataFrame, str]:
    """
    Try primary TF; if empty, try M5 as a pragmatic fallback.
    Returns (df, reason) where reason == "" means OK.
    """
    if not _ensure_symbol(symbol):
        return pd.DataFrame(), "symbol_select_failed"

    tf1 = _tf_to_mt5(tf_primary)
    df = _download_bars(symbol, tf1, need_rows)
    if len(df) >= min_rows:
        return df, ""

    # Fallback to M5 when M1 is dry
    tf2 = _TIMEFRAMES["M5"]
    if tf1 != tf2:
        df2 = _download_bars(symbol, tf2, need_rows)
        if len(df2) >= min_rows:
            return df2, ""

    return pd.DataFrame(), "no_data"

# -------------------------------
# Research Agent
# -------------------------------

@dataclass
class Candidate:
    symbol: str
    tf: str
    priority: float
    meta: dict

class ResearchAgent:
    def __init__(self):
        # ENV-tunable knobs (safe defaults)
        self.min_score = float(os.getenv("RESEARCH_MIN_SCORE", "0.0"))
        self.min_atr_pct = float(os.getenv("RESEARCH_MIN_ATR_PCT", "0.00005"))  # 0.005%
        self.top_k_fallback = int(os.getenv("RESEARCH_TOP_K_FALLBACK", "2"))
        self.debug = os.getenv("DEBUG_RESEARCH", "0") == "1"

        # Optional “force” selectors to help debugging
        force_syms = os.getenv("RESEARCH_FORCE_SYMBOLS")
        self.force_symbols: Optional[List[str]] = [s.strip() for s in force_syms.split(",")] if force_syms else None
        self.force_tf: Optional[str] = os.getenv("RESEARCH_FORCE_TF")  # e.g. "M1" or "M5"

        # Internal
        self.mt5 = MT5Data()

        log.info(
            "[ResearchAgent cfg] MIN_SCORE=%s MIN_ATR_PCT=%s TOP_K_FALLBACK=%s DEBUG=%s FORCE_SYMBOLS=%s FORCE_TF=%s",
            self.min_score, self.min_atr_pct, self.top_k_fallback, self.debug, self.force_symbols, self.force_tf
        )

    # ---- public API --------------------------------------------------------

    def find_opportunities(self, instruments: List[dict]) -> List[Candidate]:
        if not instruments:
            log.warning("No instruments received. Returning no opportunities.")
            return []

        # Which symbols/TF to scan
        if self.force_symbols:
            scan = [{"symbol": s, "timeframe": (self.force_tf or "M1")} for s in self.force_symbols]
        else:
            scan = [{"symbol": it["symbol"], "timeframe": (self.force_tf or it.get("timeframe", "M1"))}
                    for it in instruments]

        candidates: List[Candidate] = []
        admitted_lines = []

        # Ensure MT5 is connected
        self.mt5.connect()
        # Log account (sometimes demo terminals show None before first trade)
        try:
            acc = mt5.account_info()
            log.info("[diag] MT5 connected=%s account=%s server=%s",
                     bool(acc), getattr(acc, "login", None), getattr(acc, "server", None))
        except Exception:
            pass

        for item in scan:
            sym = item["symbol"]
            tf = (item["timeframe"] or "M1").upper()

            # Hardening: get at least 200 bars; try to pull up to 1500
            min_rows = int(os.getenv("RESEARCH_MIN_ROWS", "200"))
            want_rows = int(os.getenv("RESEARCH_WANT_ROWS", "1500"))

            df, reason = _fetch_bars_any(sym, tf, min_rows=min_rows, need_rows=want_rows)
            if df.empty:
                if self.debug:
                    log.info("[diag] (%r, %r) rejected: %s", sym, tf, reason)
                continue

            # Compute a tiny heuristic score: favor volatility & small momentum sign
            df["atr"] = (df["high"] - df["low"]).rolling(14).mean()
            last_close = float(df["close"].iloc[-1])
            atr14 = float(df["atr"].iloc[-1] or 0.0)
            rng_pct = (float(df["high"].max()) - float(df["low"].min())) / last_close if last_close else 0.0
            atr_pct = (atr14 / last_close) if last_close else 0.0

            # momentum proxy: close - SMA(10)
            df["sma10"] = df["close"].rolling(10).mean()
            mom = float((df["close"].iloc[-1] - df["sma10"].iloc[-1]) if pd.notna(df["sma10"].iloc[-1]) else 0.0)

            # Score: small positive to keep permissive, weighted by ATR
            score = max(self.min_score, 1e-4 + max(mom, 0.0) * 1e-4 + atr_pct)

            last_ts = _fmt_ts(df["time"].iloc[-1]) if "time" in df.columns else ""
            if self.debug:
                log.info("[diag] %s tf=%s atr%%=%.4f%% mom=%.4f score=%.4f last=%s",
                         sym, tf, atr_pct * 100.0, mom, score, last_ts)

            if atr_pct >= self.min_atr_pct and score >= self.min_score:
                c = Candidate(symbol=sym, tf=tf, priority=score, meta={
                    "atr_pct": atr_pct, "rng_pct": rng_pct, "mom": mom, "last": last_ts
                })
                candidates.append(c)
                admitted_lines.append(f"{sym}({score:.4f})")
            else:
                if self.debug:
                    log.info("[diag] (%r, %r) rejected: low_signal (atr%%=%.5f, score=%.5f)",
                             sym, tf, atr_pct * 100.0, score)

        if not candidates and self.top_k_fallback > 0 and scan:
            # Try a very permissive fallback: admit top-1 by volatility even if below thresholds
            for item in scan:
                sym = item["symbol"]; tf = (item["timeframe"] or "M1").upper()
                df, reason = _fetch_bars_any(sym, tf, min_rows=50, need_rows=600)
                if df.empty:
                    continue
                last_close = float(df["close"].iloc[-1])
                atr14 = float((df["high"] - df["low"]).rolling(14).mean().iloc[-1] or 0.0)
                atr_pct = (atr14 / last_close) if last_close else 0.0
                score = 1e-4 + atr_pct
                candidates.append(Candidate(symbol=sym, tf=tf, priority=score, meta={"atr_pct": atr_pct}))
            candidates = sorted(candidates, key=lambda c: c.priority, reverse=True)[: self.top_k_fallback]

        if self.debug:
            msg = "NONE" if not candidates else ", ".join(admitted_lines or [f"{c.symbol}({c.priority:.4f})" for c in candidates])
            log.info("[diag] admitted: %s", msg)

        # Order by priority desc
        return sorted(candidates, key=lambda c: c.priority, reverse=True)
