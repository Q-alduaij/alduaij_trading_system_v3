from __future__ import annotations
import argparse, os, sys, time, uuid
from dotenv import load_dotenv
from agents.portfolio_manager import PortfolioManager
from utils.audit_log import AuditLogger

def resolve_model_provider() -> tuple[str, str]:
    # We’re using OpenRouter in BaseAgent.call_llm.
    provider = "openrouter"
    model = os.getenv("LLM_MODEL") or os.getenv("OPENROUTER_MODEL") or "unknown"
    return provider, model

def run_once(pm: PortfolioManager, logger: AuditLogger, run_id: str) -> int:
    # Tag this cycle so BaseAgent audit hooks can correlate events
    os.environ["RUN_ID"] = run_id

    result = pm.analyze({})   # PM orchestrates all 7 agents internally

    provider, model = resolve_model_provider()
    sym = result.get("symbol") or "MULTI"
    decision_obj = {
        "recommendation": result.get("recommendation"),
        "confidence": result.get("confidence"),
        "reasoning": result.get("reasoning"),
        "data": result.get("data", {}),
    }

    # log decision to decisions.jsonl and unified journal.jsonl
    logger.log_decision(
        symbol=sym,
        decision=decision_obj,
        provider=provider,
        model=model,
        run_id=run_id,
    )

    # pretty print to console
    status = result.get("recommendation")
    conf   = result.get("confidence")
    reason = result.get("reasoning")
    print(f"[PM] final={status} conf={conf} reason={reason}")

    # If a trade was attempted, log order outcome as well
    trade = (result.get("data") or {}).get("trade_details") or {}
    if trade:
        price = trade.get("price")
        price = float(price) if isinstance(price, (int, float)) else None
        logger.log_order(
            symbol=trade.get("symbol", sym),
            side=str(trade.get("side", "flat")),
            size=float(trade.get("size", 0) or 0),
            price=price,
            provider=provider,
            model=model,
            confidence=result.get("confidence"),
            sl_points=trade.get("sl_points"),
            tp_points=trade.get("tp_points"),
            ticket=trade.get("ticket"),
            status=str(trade.get("status","")).lower() or ("submitted" if trade.get("ticket") else "unknown"),
            message=str(trade.get("message","")),
            run_id=run_id,
        )
        print(f"[trade] {trade}")

    return 0

def main():
    load_dotenv()

    ap = argparse.ArgumentParser(description="Run the full 7-agent pipeline via PortfolioManager")
    ap.add_argument("--interval", type=int, default=0,
                    help="If >0, run continuously every N seconds; if 0, run once and exit.")
    args = ap.parse_args()

    pm = PortfolioManager()
    logger = AuditLogger()

    if args.interval and args.interval > 0:
        # Continuous mode
        print(f"[runner] Starting continuous mode with interval={args.interval}s (Ctrl+C to stop)")
        try:
            while True:
                run_id = str(uuid.uuid4())
                try:
                    run_once(pm, logger, run_id)
                except Exception as e:
                    # Never crash the loop; log the error to journal as a synthetic event
                    logger._append_journal({
                        "ts": AuditLogger._now_iso() if hasattr(AuditLogger, "_now_iso") else "",
                        "type": "runner_error",
                        "run_id": run_id,
                        "error": str(e),
                    })
                    print(f"[runner] Error: {e}")
                time.sleep(max(1, args.interval))
        except KeyboardInterrupt:
            print("\n[runner] Stopped by user.")
            return 0
    else:
        # Single pass
        run_id = str(uuid.uuid4())
        return run_once(pm, logger, run_id)

if __name__ == "__main__":
    sys.exit(main())
