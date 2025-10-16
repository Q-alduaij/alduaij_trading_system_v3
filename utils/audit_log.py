from __future__ import annotations
import os, json, csv, hashlib
from datetime import datetime
from typing import Any, Dict, Optional

def _now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def _ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)

def _hash(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", errors="ignore")).hexdigest()[:16]

class AuditLogger:
    """
    Writes:
      - logs/decisions.jsonl  (one JSON object per line)
      - logs/orders.jsonl
      - logs/orders.csv
      - logs/journal.jsonl    (merged stream of decisions + orders; include run_id to correlate a cycle)
    Configure base dir via env LOG_DIR (default: ./logs).
    """
    def __init__(self, base_dir: Optional[str] = None):
        self.base = base_dir or os.getenv("LOG_DIR", "./logs")
        _ensure_dir(self.base)
        self.decisions_path = os.path.join(self.base, "decisions.jsonl")
        self.orders_jsonl   = os.path.join(self.base, "orders.jsonl")
        self.orders_csv     = os.path.join(self.base, "orders.csv")
        self.journal_path   = os.path.join(self.base, "journal.jsonl")

        # Create CSV header if missing
        if not os.path.isfile(self.orders_csv):
            with open(self.orders_csv, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow([
                    "ts", "symbol", "side", "size", "price",
                    "provider", "model", "confidence",
                    "sl_points", "tp_points", "ticket", "status", "message"
                ])

    # ------------ LLM call trace (optional) ------------
    @staticmethod
    def _now_iso() -> str:
        return _now_iso()

    def log_llm_call(self, *, agent: str, system: str, user: str, response: str,
                     provider: str = "openrouter", model: Optional[str] = None,
                     meta: Optional[Dict[str, Any]] = None, run_id: Optional[str] = None):
        rec = {
            "ts": _now_iso(),
            "type": "llm_call",
            "run_id": run_id,
            "agent": agent,
            "provider": provider,
            "model": model,
            "prompt_hash": _hash((system or "") + "\n" + (user or "")),
            "system_len": len(system or ""),
            "user_len": len(user or ""),
            "response_len": len(response or ""),
            "meta": meta or {},
        }
        with open(self.decisions_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        # also mirror into journal
        self._append_journal(rec)

    # ------------ High level decision logging ------------
    def log_decision(self, *, symbol: str, decision: Dict[str, Any],
                     provider: str = "openrouter", model: Optional[str] = None,
                     prompt_hash: Optional[str] = None, notes: Optional[Dict[str, Any]] = None,
                     run_id: Optional[str] = None):
        rec = {
            "ts": _now_iso(),
            "type": "decision",
            "run_id": run_id,
            "symbol": symbol,
            "provider": provider,
            "model": model,
            "prompt_hash": prompt_hash,
            "decision": decision,
            "notes": notes or {},
        }
        with open(self.decisions_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        # also mirror into journal
        self._append_journal(rec)

    # ------------ Order logging ------------
    def log_order(self, *, symbol: str, side: str, size: float, price: float | None,
                  provider: str, model: Optional[str], confidence: float | None,
                  sl_points: int | None, tp_points: int | None,
                  ticket: int | None, status: str, message: str = "",
                  run_id: Optional[str] = None):
        js = {
            "ts": _now_iso(),
            "type": "order",
            "run_id": run_id,
            "symbol": symbol,
            "side": side,
            "size": size,
            "price": price,
            "provider": provider,
            "model": model,
            "confidence": confidence,
            "sl_points": sl_points,
            "tp_points": tp_points,
            "ticket": ticket,
            "status": status,
            "message": message,
        }
        # JSONL
        with open(self.orders_jsonl, "a", encoding="utf-8") as f:
            f.write(json.dumps(js, ensure_ascii=False) + "\n")
        # CSV
        with open(self.orders_csv, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([
                js["ts"], symbol, side, size, price,
                provider, model, confidence, sl_points, tp_points, ticket, status, message
            ])
        # also mirror into journal
        self._append_journal(js)

    # ------------ Unified journal ------------
    def _append_journal(self, record: Dict[str, Any]):
        with open(self.journal_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
