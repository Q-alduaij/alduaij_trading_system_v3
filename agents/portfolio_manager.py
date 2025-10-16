"""
Portfolio Manager
Coordinates the multi-agent pipeline and decides final action
"""
from __future__ import annotations

import os
import yaml
from typing import Dict, Any, List, Tuple

from utils.logger import get_logger
from agents.base_agent import BaseAgent
from agents.research_agent import ResearchAgent
from agents.technical_agent import TechnicalAgent
from agents.fundamental_agent import FundamentalAgent
from agents.sentiment_agent import SentimentAgent
from agents.risk_agent import RiskAgent
from agents.execution_agent import ExecutionAgent

log = get_logger("agents.PortfolioManager")


class PortfolioManager(BaseAgent):
    """
    Orchestrates the multi-agent flow:
      Research -> (choose symbol) -> Technical -> Fundamental -> Sentiment -> Aggregate -> Risk -> Execute

    Enhancements:
      • Env-tunable fallback to place a trade when only Technical votes buy/sell:
          PM_TRADE_ON_TECH_ALONE = "1"      # enable fallback
          PM_MIN_TECH_CONF       = "0.65"   # min technical confidence to allow fallback
          PM_TEST_LOT            = "0.01"   # optional lot size override (paper/demo safe)

      • Reads instruments from config/instruments.yaml (respects "enabled")
    """

    def __init__(self):
        super().__init__("PortfolioManager")

        # Sub-agents
        self.research = ResearchAgent()
        self.technical = TechnicalAgent()
        self.fundamental = FundamentalAgent()
        self.sentiment = SentimentAgent()
        self.risk = RiskAgent()
        self.execution = ExecutionAgent()

        # Config / env knobs
        self._default_tf = os.getenv("RESEARCH_FORCE_TF", "H1")

        self._trade_on_tech_alone = os.getenv("PM_TRADE_ON_TECH_ALONE", "0") in ("1", "true", "True", "YES", "yes")
        try:
            self._min_tech_conf = float(os.getenv("PM_MIN_TECH_CONF", "0.65"))
        except Exception:
            self._min_tech_conf = 0.65

        # Optional lot override when we do execute (safe for paper/demo)
        _lot_env = os.getenv("PM_TEST_LOT", "").strip()
        self._test_lot = None
        if _lot_env:
            try:
                self._test_lot = float(_lot_env)
            except Exception:
                log.warning(f"Ignoring invalid PM_TEST_LOT={_lot_env!r}")

        self._cached_instruments = self._load_instruments_for_pipeline()

        log.info(
            f"[PM cfg] tech_fallback={self._trade_on_tech_alone} "
            f"min_tech_conf={self._min_tech_conf} test_lot={self._test_lot}"
        )

    # -------------------------
    # config / instruments load
    # -------------------------
    def _load_instruments_for_pipeline(self) -> List[Tuple[str, str]]:
        """
        Return list of (symbol, timeframe) pulled from config/instruments.yaml.
        Accepts either:
          instruments:
            - {symbol: "EURUSD", timeframe: "M1", enabled: true}
            - "XAUUSD"   # uses default TF
        """
        path = os.path.join("config", "instruments.yaml")
        symbols: List[Tuple[str, str]] = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                doc = yaml.safe_load(f) or {}
            items = doc.get("instruments") or doc
            if isinstance(items, list):
                for it in items:
                    if isinstance(it, dict):
                        if not it.get("enabled", True):
                            continue
                        sym = it.get("symbol")
                        tf = it.get("timeframe", self._default_tf)
                        if sym:
                            symbols.append((sym, tf))
                    elif isinstance(it, str):
                        symbols.append((it, self._default_tf))
        except Exception as e:
            log.error(f"Failed to read {path}: {e}")

        if not symbols:
            log.warning("No enabled instruments found in config; portfolio loop may do nothing.")
        else:
            log.info(f"Loaded {len(symbols)} enabled instruments")
        return symbols

    # -------------
    # main decision
    # -------------
    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        log.info("=== Portfolio Manager: Starting Analysis Cycle ===")

        # === Step 1: Research — choose candidate
        log.info("Step 1: Research Agent - Identifying opportunities...")
        research_res = self.research.analyze({"instruments": self._cached_instruments})
        opps = (research_res.get("data") or {}).get("opportunities", [])

        if not opps:
            log.info("No opportunities identified. Cycle complete.")
            return self.format_analysis_result(
                recommendation="no_action",
                confidence=0.5,
                reasoning="No trading opportunities identified",
                data={},
            )

        # Pick highest priority
        top = max(opps, key=lambda x: x.get("priority", 0.0))
        symbol = top.get("symbol")
        tf = top.get("timeframe") or self._default_tf
        if not symbol:
            return self.format_analysis_result(
                recommendation="no_action",
                confidence=0.5,
                reasoning="Research returned an invalid candidate (missing symbol)",
                data={},
            )
        log.info(f"Analyzing top opportunity: {symbol}")

        # === Step 2: Technical
        log.info("Step 2: Technical Agent - Analyzing indicators...")
        tech_res = self.technical.analyze({"instrument": symbol, "timeframe": tf})
        tech_rec = tech_res.get("recommendation", "hold")
        tech_conf = float(tech_res.get("confidence", 0.0) or 0.0)

        # === Step 3: Fundamental
        log.info("Step 3: Fundamental Agent - Analyzing fundamentals...")
        fund_res = self.fundamental.analyze({"instrument": symbol})
        fund_rec = fund_res.get("recommendation", "hold")

        # === Step 4: Sentiment
        log.info("Step 4: Sentiment Agent - Analyzing sentiment...")
        sent_res = self.sentiment.analyze({"instrument": symbol})
        sent_rec = sent_res.get("recommendation", "hold")

        # === Step 5: Aggregate (majority voting)
        log.info("Step 5: Aggregating agent recommendations...")
        votes = [tech_rec, fund_rec, sent_rec]
        buys = votes.count("buy")
        sells = votes.count("sell")

        if buys > sells and buys >= 2:
            final, conf, reason = "buy", 0.6, "Majority voting across agents"
        elif sells > buys and sells >= 2:
            final, conf, reason = "sell", 0.6, "Majority voting across agents"
        else:
            final, conf, reason = "hold", 0.5, "No strong consensus"

        # Optional fallback: trade on Technical alone if confidence high enough
        if final == "hold" and self._trade_on_tech_alone:
            if tech_rec in ("buy", "sell") and tech_conf >= self._min_tech_conf:
                log.info(
                    f"[PM] Tech-only fallback engaged: tech_rec={tech_rec} tech_conf={tech_conf:.2f} "
                    f"(min={self._min_tech_conf})"
                )
                final, conf, reason = tech_rec, tech_conf, "Tech-only fallback (confidence threshold passed)"

        # === Step 6: Risk gate
        if final in ("buy", "sell"):
            risk_res = self.risk.analyze(
                {
                    "proposed_trade": {
                        "instrument": symbol,
                        "direction": final,
                        "timeframe": tf,
                        "confidence": conf,
                        "source": reason,
                    }
                }
            )
            if risk_res.get("recommendation") != "approve":
                log.info("[PM] Risk denied trade; switching to HOLD.")
                final, conf, reason = "hold", 0.5, "Risk manager veto"

        # === Step 7: Execute
        trade_details = {}
        if final in ("buy", "sell"):
            exec_payload = {"instrument": symbol, "action": final, "timeframe": tf}
            if self._test_lot is not None:
                exec_payload["lot"] = self._test_lot  # ExecutionAgent may ignore if not supported

            exec_res = self.execution.analyze(exec_payload)
            trade_details = (exec_res or {}).get("data", {}).get("order", {}) or {}

        if final == "hold":
            log.info("Aggregated recommendation is HOLD. No trade.")

        return self.format_analysis_result(
            recommendation=final if final in ("buy", "sell") else "hold",
            confidence=conf,
            reasoning=reason,
            data={"symbol": symbol, "timeframe": tf, "votes": {"tech": tech_rec, "fund": fund_rec, "sent": sent_rec}, "trade_details": trade_details},
        )
