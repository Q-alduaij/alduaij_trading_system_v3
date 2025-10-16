from __future__ import annotations
import argparse, os, sys
from datetime import datetime, timedelta

try:
    from dotenv import load_dotenv
except Exception:
    def load_dotenv(): return None

def run_health_check() -> int:
    try:
        from tools import api_key_health_check as hk
    except Exception as e:
        print(f"[health] cannot import health checker: {e}"); return 2
    try:
        hk.main()
    except SystemExit as se:
        return int(se.code or 0)
    return 0

def ensure_db():
    try:
        from utils import db_init; db_init.ensure_db()
    except Exception as e:
        print(f"[db] initialization failed: {e}"); sys.exit(2)

def validate_config():
    try:
        from utils import config_validate; rc = config_validate.main()
        if rc != 0: print("[config] invalid; aborting."); sys.exit(rc)
    except SystemExit as se:
        raise
    except Exception as e:
        print(f"[config] validation error: {e}"); sys.exit(2)

def make_sinewave_ohlcv(n=500, start=100.0):
    import pandas as pd, numpy as np
    from datetime import datetime, timedelta

    rng = np.random.default_rng(7)
    ts0 = datetime(2024, 1, 1)

    ts = [ts0 + timedelta(minutes=i) for i in range(n)]
    base = start + 2.0 * np.sin(np.linspace(0, 25, n)) + rng.normal(0, 0.3, n).cumsum() * 0.01
    close = np.maximum(0.1, base)

    open_ = close * (1 + rng.normal(0, 0.0005, n))
    high  = np.maximum(open_, close) * (1 + np.abs(rng.normal(0, 0.0008, n)))
    low   = np.minimum(open_, close) * (1 - np.abs(rng.normal(0, 0.0008, n)))
    vol   = rng.integers(100, 1000, n)

    return pd.DataFrame({
        "timestamp": ts,
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": vol,
    })

def run_demo(fast:int, slow:int):
    from backtesting import simple_runner
    df = make_sinewave_ohlcv()
    result = simple_runner.run(df, {"fast":fast,"slow":slow})
    print("[demo] result:", result["summary"]); return 0

def main():
    load_dotenv()
    p = argparse.ArgumentParser(description="Lolo Trading Agent â€” runtime")
    p.add_argument("--health", action="store_true")
    p.add_argument("--demo", action="store_true")
    p.add_argument("--fast", type=int, default=10)
    p.add_argument("--slow", type=int, default=30)
    p.add_argument("--paper-exec", action="store_true")
    p.add_argument("--live-exec", action="store_true")
    p.add_argument("--symbols", nargs="+", default=["EURUSD"])
    p.add_argument("--timeframe", default="M1")
    p.add_argument("--lot", type=float, default=0.01)
    p.add_argument("--sl-points", type=int, default=0)
    p.add_argument("--tp-points", type=int, default=0)
    p.add_argument("--interval", type=int, default=30)
    p.add_argument("--once", action="store_true")
    args = p.parse_args()

    validate_config(); ensure_db()

    if args.health:
        rc = run_health_check(); sys.exit(rc)

    if args.demo:
        rc = run_demo(args.fast, args.slow); sys.exit(rc)

    if args.paper_exec or args.live_exec:
        paper_env = os.getenv("PAPER_TRADING","true").lower() in {"1","true","yes","y"}
        if args.live_exec and paper_env:
            print("[exec] Refusing to run live while PAPER_TRADING=true. Set PAPER_TRADING=false in .env."); sys.exit(2)
        from execution.mt5_executor import MT5Executor
        from risk.guard import RiskGuard
        from signals.mt5_sma_agent import last_signal
        import time
        ex = MT5Executor(os.getenv("MT5_PATH"))
        if not ex.connect(): print("[exec] MT5 initialize failed."); sys.exit(2)
        rg = RiskGuard()

        def one_pass():
            new_orders = 0; est_notional = 0.0
            ok, msg = rg.check_all(0,0.0)
            if not ok: print(f"[risk] {msg}"); return
            for sym in args.symbols:
                sig = last_signal(sym, args.timeframe, args.fast, args.slow)
                if sig == "flat": print(f"[signal] {sym}: flat"); continue
                px = ex.price(sym)
                if not px: print(f"[price] {sym}: no price"); continue
                bid, ask = px; quote = ask if sig=="buy" else bid
                est_notional += max(quote,0) * args.lot
                ok, why = rg.check_all(new_orders+1, est_notional)
                if not ok: print(f"[risk] block {sym}: {why}"); continue
                print(f"[order] {sym} {sig} {args.lot} @ ~{quote}")
                res = ex.market_order(sym, sig, args.lot,
                                      sl_points=(args.sl_points or None),
                                      tp_points=(args.tp_points or None),
                                      comment="lolo-agent")
                if res.ok: print(f"[order] OK ticket={res.ticket}")
                else: print(f"[order] FAIL {res.comment} err={res.last_error}")
        try:
            if args.once: one_pass()
            else:
                while True: one_pass(); time.sleep(max(args.interval,5))
        finally:
            ex.disconnect()
        sys.exit(0)

    print("No action selected. Use --health, --demo, --paper-exec, or --live-exec.")
    return 0

if __name__ == "__main__":
    main()
