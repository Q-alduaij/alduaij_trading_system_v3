# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd

from agents.base_agent import BaseAgent
from data_collection.mt5_connector import MT5Connector

log = logging.getLogger(__name__)

# -------------------------------
# Helpers
# -------------------------------

_FALLBACK_TIMEFRAME = "M5"


def _fmt_ts(ts: Optional[pd.Timestamp]) -> str:
    if ts is None or pd.isna(ts):
        return ""
    try:
        if isinstance(ts, pd.Timestamp):
            return ts.isoformat()
        return pd.to_datetime(ts).isoformat()
    except Exception:
        return ""


def _normalize_bars(df: Optional[pd.DataFrame]) -> pd.DataFrame:
    """Ensure MT5Connector output has a usable schema."""
    if df is None or df.empty:
        return pd.DataFrame()

    bars = df.copy()
    if "time" not in bars.columns:
        bars = bars.reset_index()
    if "time" not in bars.columns and bars.columns.size > 0:
        bars = bars.rename(columns={bars.columns[0]: "time"})

    if "time" not in bars.columns:
        return pd.DataFrame()

    bars["time"] = pd.to_datetime(bars["time"], errors="coerce")
    bars = bars.dropna(subset=["time"])
    required = {"open", "high", "low", "close"}
    if not required.issubset(bars.columns):
        return pd.DataFrame()

    bars = bars.sort_values("time").reset_index(drop=True)
    return bars


def _fetch_bars_any(
    connector: MT5Connector,
    symbol: str,
    tf_primary: str,
    min_rows: int,
    need_rows: int,
) -> Tuple[pd.DataFrame, str]:
    """
    Try the requested timeframe first; fall back to a coarser TF if empty.
    Returns (df, reason) where reason == "" indicates success.
    """

    if not connector.check_symbol_availability(symbol):
        return pd.DataFrame(), "symbol_unavailable"

    tf_primary = (tf_primary or "M1").upper()
    df_primary = _normalize_bars(
        connector.get_historical_data(symbol, tf_primary, num_bars=need_rows)
    )
    if len(df_primary) >= min_rows:
        return df_primary, ""

    tf_fallback = _FALLBACK_TIMEFRAME if tf_primary != _FALLBACK_TIMEFRAME else None
    if tf_fallback:
        df_fallback = _normalize_bars(
            connector.get_historical_data(symbol, tf_fallback, num_bars=need_rows)
        )
        if len(df_fallback) >= min_rows:
            return df_fallback, ""

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


class ResearchAgent(BaseAgent):
    def __init__(self):
        super().__init__("ResearchAgent")
        # ENV-tunable knobs (safe defaults)
        self.min_score = float(os.getenv("RESEARCH_MIN_SCORE", "0.0"))
        self.min_atr_pct = float(os.getenv("RESEARCH_MIN_ATR_PCT", "0.00005"))  # 0.005%
        self.top_k_fallback = int(os.getenv("RESEARCH_TOP_K_FALLBACK", "2"))
        self.debug = os.getenv("DEBUG_RESEARCH", "0") == "1"

        # Optional “force” selectors to help debugging
        force_syms = os.getenv("RESEARCH_FORCE_SYMBOLS")
        self.force_symbols: Optional[List[str]] = [
            s.strip() for s in force_syms.split(",")
        ] if force_syms else None
        self.force_tf: Optional[str] = os.getenv("RESEARCH_FORCE_TF")  # e.g. "M1" or "M5"

        # Internal
        self.mt5 = MT5Connector()

        log.info(
            "[ResearchAgent cfg] MIN_SCORE=%s MIN_ATR_PCT=%s TOP_K_FALLBACK=%s DEBUG=%s FORCE_SYMBOLS=%s FORCE_TF=%s",
            self.min_score,
            self.min_atr_pct,
            self.top_k_fallback,
            self.debug,
            self.force_symbols,
            self.force_tf,
        )

    # ---- public API --------------------------------------------------------

    def _normalise_instruments(self, instruments: Iterable[Any]) -> List[dict]:
        normalised: List[dict] = []
        for item in instruments:
            symbol: Optional[str] = None
            timeframe: Optional[str] = None

            if isinstance(item, dict):
                symbol = item.get("symbol")
                timeframe = item.get("timeframe")
            elif isinstance(item, (list, tuple)):
                if item:
                    symbol = item[0]
                    if len(item) > 1:
                        timeframe = item[1]
            elif isinstance(item, str):
                symbol = item

            if symbol:
                normalised.append({"symbol": str(symbol), "timeframe": timeframe})

        return normalised

    def find_opportunities(self, instruments: List[dict]) -> List[Candidate]:
        if not instruments:
            log.warning("No instruments received. Returning no opportunities.")
            return []

        # Which symbols/TF to scan
        if self.force_symbols:
            scan = [
                {"symbol": s, "timeframe": (self.force_tf or "M1")}
                for s in self.force_symbols
            ]
        else:
            scan = [
                {
                    "symbol": it["symbol"],
                    "timeframe": (self.force_tf or it.get("timeframe", "M1")),
                }
                for it in instruments
            ]

        candidates: List[Candidate] = []
        admitted_lines = []

        # Ensure MT5 is connected
        if not self.mt5.ensure_connection():
            log.error("[ResearchAgent] Failed to connect to MT5. Returning no opportunities.")
            return []

        account = self.mt5.get_account_info()
        if account:
            log.info(
                "[diag] MT5 connected balance=%.2f equity=%.2f server=%s",
                account.get("balance", 0.0),
                account.get("equity", 0.0),
                account.get("server", "?"),
            )

        min_rows_required = int(os.getenv("RESEARCH_MIN_ROWS", "200"))
        desired_rows = int(os.getenv("RESEARCH_WANT_ROWS", "1500"))

        for item in scan:
            sym = item["symbol"]
            tf = (item["timeframe"] or "M1").upper()

            df, reason = _fetch_bars_any(
                self.mt5,
                sym,
                tf,
                min_rows=min_rows_required,
                need_rows=desired_rows,
            )
            if df.empty:
                if self.debug:
                    log.info("[diag] (%r, %r) rejected: %s", sym, tf, reason)
                continue

            atr_series = (df["high"] - df["low"]).rolling(14).mean()
            atr14 = float(atr_series.iloc[-1]) if not atr_series.empty and pd.notna(atr_series.iloc[-1]) else 0.0
            last_close = float(df["close"].iloc[-1]) if not df.empty else 0.0
            rng_pct = (
                (float(df["high"].max()) - float(df["low"].min())) / last_close
                if last_close
                else 0.0
            )
            atr_pct = (atr14 / last_close) if last_close else 0.0

            df["sma10"] = df["close"].rolling(10).mean()
            mom_val = df["close"] - df["sma10"]
            mom = float(mom_val.iloc[-1]) if not mom_val.empty and pd.notna(mom_val.iloc[-1]) else 0.0

            score = max(self.min_score, 1e-4 + max(mom, 0.0) * 1e-4 + atr_pct)

            last_ts = _fmt_ts(df["time"].iloc[-1]) if not df.empty else ""
            if self.debug:
                log.info(
                    "[diag] %s tf=%s atr%%=%.4f%% mom=%.4f score=%.4f last=%s",
                    sym,
                    tf,
                    atr_pct * 100.0,
                    mom,
                    score,
                    last_ts,
                )

            if atr_pct >= self.min_atr_pct and score >= self.min_score:
                candidate = Candidate(
                    symbol=sym,
                    tf=tf,
                    priority=score,
                    meta={
                        "atr_pct": atr_pct,
                        "rng_pct": rng_pct,
                        "mom": mom,
                        "last": last_ts,
                    },
                )
                candidates.append(candidate)
                admitted_lines.append(f"{sym}({score:.4f})")
            else:
                if self.debug:
                    log.info(
                        "[diag] (%r, %r) rejected: low_signal (atr%%=%.5f, score=%.5f)",
                        sym,
                        tf,
                        atr_pct * 100.0,
                        score,
                    )

        if not candidates and self.top_k_fallback > 0 and scan:
            temp: List[Candidate] = []
            for item in scan:
                sym = item["symbol"]
                tf = (item["timeframe"] or "M1").upper()
                df, _ = _fetch_bars_any(
                    self.mt5,
                    sym,
                    tf,
                    min_rows=50,
                    need_rows=max(600, min_rows_required),
                )
                if df.empty:
                    continue
                atr_series = (df["high"] - df["low"]).rolling(14).mean()
                atr14 = float(atr_series.iloc[-1]) if not atr_series.empty and pd.notna(atr_series.iloc[-1]) else 0.0
                last_close = float(df["close"].iloc[-1]) if not df.empty else 0.0
                atr_pct = (atr14 / last_close) if last_close else 0.0
                score = 1e-4 + atr_pct
                temp.append(
                    Candidate(
                        symbol=sym,
                        tf=tf,
                        priority=score,
                        meta={"atr_pct": atr_pct},
                    )
                )
            candidates = sorted(temp, key=lambda c: c.priority, reverse=True)[: self.top_k_fallback]

        if self.debug:
            msg = "NONE" if not candidates else ", ".join(
                admitted_lines or [f"{c.symbol}({c.priority:.4f})" for c in candidates]
            )
            log.info("[diag] admitted: %s", msg)

        return sorted(candidates, key=lambda c: c.priority, reverse=True)

    # ---- BaseAgent API ----------------------------------------------------

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        instruments_raw = (data or {}).get("instruments") or []
        instruments = self._normalise_instruments(instruments_raw)

        if not instruments:
            log.warning("[ResearchAgent] No valid instruments supplied to analyze().")

        opportunities = self.find_opportunities(instruments)
        payload = {
            "opportunities": [
                {
                    "symbol": c.symbol,
                    "timeframe": c.tf,
                    "priority": c.priority,
                    "meta": c.meta,
                }
                for c in opportunities
            ]
        }

        has_opportunities = bool(opportunities)
        reasoning = (
            "Identified potential trading opportunities"
            if has_opportunities
            else "No instruments met research screening criteria"
        )

        confidence = 0.6 if has_opportunities else 0.4

        return self.format_analysis_result(
            recommendation="opportunities_found" if has_opportunities else "no_opportunities",
            confidence=confidence,
            reasoning=reasoning,
            data=payload,
        )
