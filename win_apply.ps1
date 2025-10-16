# win_apply.ps1 - Bootstrap Lolo Trading Agent files (no Git patches needed)
# Usage:
#   Set-ExecutionPolicy Bypass -Scope Process -Force
#   .\win_apply.ps1

$ErrorActionPreference = "Stop"

function Write-TextFile($Path, $Content) {
  $dir = Split-Path -Parent $Path
  if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
  Set-Content -LiteralPath $Path -Value $Content -Encoding UTF8 -Force
  Write-Host "Wrote $Path" -ForegroundColor Green
}

# ---- Files to write ----

$ENV_EXAMPLE = @'
# Copy this file to .env and fill in real values

# LLM / OpenRouter / OpenAI
OPENROUTER_API_KEY=
OPENROUTER_MODEL=deepseek/deepseek-chat-v3.1:free
OPENAI_API_KEY=

# MetaTrader5 (if using MT5 Python package)
MT5_PATH=
MT5_LOGIN=
MT5_PASSWORD=
MT5_SERVER=
MT5_ENABLE_EXPERTS=true

# Market data providers
POLYGON_API_KEY=
FINNHUB_API_KEY=
ALPHAVANTAGE_API_KEY=
TWELVEDATA_API_KEY=
FMP_API_KEY=

# News / Sentiment
NEWSAPI_KEY=

# Storage / memory
SQLITE_PATH=./memory/lolo.db
CHROMA_DIR=./memory/chroma
PAPER_TRADING=true

# Optional: logging / debug
LOG_LEVEL=INFO

# Example test symbols used by health-checks
TEST_SYMBOL=AAPL

# --- Safety rails for execution ---
LOLO_KILL_SWITCH=false
MAX_POSITIONS=5
MAX_DAILY_LOSS_PCT=5
MAX_EXPOSURE_NOTIONAL=0   # 0=disabled
'@

$INSTRUMENTS_YAML = @'
instruments:
  - symbol: EURUSD
    type: forex
    lot_min: 0.01
    lot_max: 1.0
  - symbol: XAUUSD
    type: commodity
    lot_min: 0.01
    lot_max: 0.5
  - symbol: US500
    type: index
    lot_min: 0.01
    lot_max: 2.0
  - symbol: AAPL
    type: stock
    lot_min: 1
    lot_max: 100

session:
  timezone: UTC
  trading_hours:
    start: '00:00'
    end: '23:59'
'@

$STRATEGIES_YAML = @'
strategy:
  name: example_momentum
  timeframe: 60  # minutes
  indicators:
    - name: sma
      period: 50
    - name: rsi
      period: 14

risk:
  risk_per_trade_pct: 1.0
  max_daily_loss_pct: 5.0
  max_positions: 5
  max_drawdown_pct: 10.0

execution:
  slippage: 0.5
  order_type: market
'@

$DB_INIT = @'
import os, sqlite3
from pathlib import Path

DB_PATH = os.environ.get("SQLITE_PATH", "./memory/lolo.db")

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT,
    indicator_snapshot TEXT,
    side TEXT,
    confidence REAL,
    processed INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opened_at TEXT NOT NULL,
    closed_at TEXT,
    symbol TEXT NOT NULL,
    size REAL,
    entry_price REAL,
    exit_price REAL,
    pnl REAL,
    status TEXT
);

CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    position_id INTEGER,
    executed_at TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT,
    price REAL,
    size REAL,
    fees REAL DEFAULT 0,
    FOREIGN KEY(position_id) REFERENCES positions(id) ON DELETE SET NULL
);
"""

def ensure_db(path: str = DB_PATH):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p))
    try:
        cur = conn.cursor()
        cur.executescript(SCHEMA)
        conn.commit()
        print(f"Initialized DB at: {p}")
    finally:
        conn.close()

if __name__ == "__main__":
    ensure_db()
'@

$HEALTH_CHECK = @'
import os, sys, requests
from typing import Dict
from dotenv import load_dotenv
load_dotenv()
TEST_SYMBOL = os.getenv("TEST_SYMBOL", "AAPL")

def test_openrouter(key: str) -> Dict:
    url = "https://api.openrouter.ai/v1/models"
    headers = {"Authorization": f"Bearer {key}"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        return {"ok": r.status_code == 200, "status_code": r.status_code, "body": r.text[:200]}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def test_finnhub(key: str) -> Dict:
    url = f"https://finnhub.io/api/v1/quote?symbol={TEST_SYMBOL}&token={key}"
    try:
        r = requests.get(url, timeout=8)
        j = r.json()
        ok = r.status_code == 200 and ("c" in j)
        return {"ok": ok, "status_code": r.status_code, "json_keys": list(j.keys())}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def test_alphavantage(key: str) -> Dict:
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=IBM&interval=5min&apikey={key}"
    try:
        r = requests.get(url, timeout=8)
        ok = r.status_code == 200 and "Time Series" in r.text
        return {"ok": ok, "status_code": r.status_code, "snippet": r.text[:200]}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def test_newsapi(key: str) -> Dict:
    url = f"https://newsapi.org/v2/top-headlines?country=us&apiKey={key}"
    try:
        r = requests.get(url, timeout=8)
        return {"ok": r.status_code == 200, "status_code": r.status_code, "text": r.text[:200]}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def test_twelvedata(key: str) -> Dict:
    url = f"https://api.twelvedata.com/time_series?symbol={TEST_SYMBOL}&interval=1min&apikey={key}"
    try:
        r = requests.get(url, timeout=8)
        j = r.json()
        ok = r.status_code == 200 and (("values" in j) or ("status" in j and j.get("status") != "error"))
        return {"ok": ok, "status_code": r.status_code, "snippet": r.text[:200]}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def test_polygon(key: str) -> Dict:
    url = f"https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/tickers?active=true&apiKey={key}"
    try:
        r = requests.get(url, timeout=8)
        return {"ok": r.status_code == 200, "status_code": r.status_code, "snippet": r.text[:200]}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def test_openai(key: str) -> Dict:
    url = "https://api.openai.com/v1/models"
    headers = {"Authorization": f"Bearer {key}"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        return {"ok": r.status_code == 200, "status_code": r.status_code}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def test_mt5() -> Dict:
    try:
        import MetaTrader5 as mt5
    except Exception as e:
        return {"ok": False, "error": f"MetaTrader5 import failed: {e}"}
    mt5_path = os.getenv("MT5_PATH")
    try:
        init_res = mt5.initialize(mt5_path) if mt5_path else mt5.initialize()
        if not init_res:
            err = mt5.last_error()
            return {"ok": False, "error": f"mt5.initialize() returned False, last_error={err}"}
        mt5.shutdown()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}

CHECKS = [
    ("OPENROUTER_API_KEY", "OpenRouter", test_openrouter),
    ("OPENAI_API_KEY", "OpenAI", test_openai),
    ("FINNHUB_API_KEY", "Finnhub", test_finnhub),
    ("ALPHAVANTAGE_API_KEY", "AlphaVantage", test_alphavantage),
    ("NEWSAPI_KEY", "NewsAPI", test_newsapi),
    ("TWELVEDATA_API_KEY", "TwelveData", test_twelvedata),
    ("POLYGON_API_KEY", "Polygon", test_polygon),
]

def main():
    results = {}
    failures = 0
    for envvar, label, fn in CHECKS:
        key = os.getenv(envvar)
        if not key:
            results[label] = {"ok": False, "error": f"Env var {envvar} not set"}
            failures += 1
            continue
        try:
            res = fn(key)
            results[label] = res
            if not res.get("ok"):
                failures += 1
        except Exception as e:
            results[label] = {"ok": False, "error": str(e)}
            failures += 1

    try:
        mt5_res = test_mt5()
        results["MetaTrader5"] = mt5_res
        if not mt5_res.get("ok"):
            failures += 1
    except Exception as e:
        results["MetaTrader5"] = {"ok": False, "error": str(e)}
        failures += 1

    sqlite_path = os.getenv("SQLITE_PATH", "./memory/lolo.db")
    chroma_dir = os.getenv("CHROMA_DIR", "./memory/chroma")
    from pathlib import Path
    Path(os.path.dirname(sqlite_path) or ".").mkdir(parents=True, exist_ok=True)
    results["SQLiteDir"] = {"ok": os.path.isdir(os.path.dirname(sqlite_path) or ".")}
    results["ChromaDir"] = {"ok": os.path.isdir(chroma_dir), "path": chroma_dir}

    print("\nAPI Key Health Check Summary:\n")
    for k, v in results.items():
        ok = v.get("ok")
        if ok:
            print(f"[OK]   {k}")
        else:
            err = v.get("error") or v.get("status_code") or v.get("snippet") or "unknown"
            print(f"[FAIL] {k}: {err}")

    if failures > 0:
        print(f"\nCompleted with {failures} failure(s). Review the errors above.\n")
        sys.exit(2)
    else:
        print("\nAll required checks passed.\n")
        sys.exit(0)

if __name__ == "__main__":
    main()
'@

$CONFIG_VALIDATE = @'
from __future__ import annotations
import os, sys
from typing import Any
try:
    from pydantic import BaseModel, Field, ValidationError
except Exception:
    print("pydantic not installed. `pip install pydantic` or add to requirements.txt.")
    sys.exit(0)
try:
    import yaml
except Exception:
    print("PyYAML not installed. `pip install PyYAML` or add to requirements.txt.")
    sys.exit(0)

class EnvCfg(BaseModel):
    PAPER_TRADING: bool = Field(default=True)
    SQLITE_PATH: str = Field(default="./memory/lolo.db")
    OPENROUTER_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None
    FINNHUB_API_KEY: str | None = None
    ALPHAVANTAGE_API_KEY: str | None = None
    NEWSAPI_KEY: str | None = None
    TWELVEDATA_API_KEY: str | None = None
    POLYGON_API_KEY: str | None = None

def load_env() -> EnvCfg:
    def as_bool(v: str, default: bool) -> bool:
        if v is None: return default
        return str(v).strip().lower() in {"1","true","yes","y"}
    return EnvCfg(
        PAPER_TRADING=as_bool(os.getenv("PAPER_TRADING","true"), True),
        SQLITE_PATH=os.getenv("SQLITE_PATH","./memory/lolo.db"),
        OPENROUTER_API_KEY=os.getenv("OPENROUTER_API_KEY"),
        OPENAI_API_KEY=os.getenv("OPENAI_API_KEY"),
        FINNHUB_API_KEY=os.getenv("FINNHUB_API_KEY"),
        ALPHAVANTAGE_API_KEY=os.getenv("ALPHAVANTAGE_API_KEY"),
        NEWSAPI_KEY=os.getenv("NEWSAPI_KEY"),
        TWELVEDATA_API_KEY=os.getenv("TWELVEDATA_API_KEY"),
        POLYGON_API_KEY=os.getenv("POLYGON_API_KEY"),
    )

def load_yaml(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        import yaml as _y
        return _y.safe_load(f) or {}

def main() -> int:
    try:
        env = load_env()
    except ValidationError as e:
        print(f"[ENV] Validation error:\n{e}")
        return 2
    print("[ENV] OK — PAPER_TRADING =", env.PAPER_TRADING, ", SQLITE_PATH =", env.SQLITE_PATH)

    missing = []
    for f in ("config/instruments.yaml","config/strategies.yaml"):
        if not os.path.isfile(f):
            missing.append(f); continue
        try:
            doc = load_yaml(f)
            if not isinstance(doc, dict):
                print(f"[CFG] {f}: not a mapping/dict at top-level")
                return 2
            print(f"[CFG] {f}: OK")
        except Exception as e:
            print(f"[CFG] {f}: failed to load — {e}")
            return 2
    if missing:
        print("[CFG] Missing files:", ", ".join(missing))
    return 0

if __name__ == "__main__":
    sys.exit(main())
'@

$SIMPLE_BT = @'
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
'@

$EXECUTOR = @'
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass
class OrderResult:
    ok: bool
    comment: str
    ticket: Optional[int] = None
    last_error: Optional[tuple] = None

class MT5Executor:
    def __init__(self, path: str | None = None):
        self.path = path
        self._mt5 = None

    def connect(self) -> bool:
        import MetaTrader5 as mt5
        self._mt5 = mt5
        return mt5.initialize(self.path) if self.path else mt5.initialize()

    def disconnect(self):
        if self._mt5: self._mt5.shutdown()

    def ensure_symbol(self, symbol: str) -> bool:
        mt5 = self._mt5
        if not mt5.symbol_select(symbol, True): return False
        info = mt5.symbol_info(symbol)
        return bool(info and info.visible)

    def price(self, symbol: str):
        mt5 = self._mt5
        tick = mt5.symbol_info_tick(symbol)
        if not tick: return None
        return float(tick.bid), float(tick.ask)

    def market_order(self, symbol: str, side: str, volume: float,
                     sl_points: int | None = None, tp_points: int | None = None,
                     comment: str = "lolo-agent", magic: int = 20251014) -> OrderResult:
        mt5 = self._mt5
        if side not in ("buy","sell"):
            return OrderResult(False, f"invalid side={side}")
        if not self.ensure_symbol(symbol):
            return OrderResult(False, f"symbol not available: {symbol}")
        px = self.price(symbol)
        if not px: return OrderResult(False, "no price")
        bid, ask = px
        order_type = mt5.ORDER_TYPE_BUY if side=="buy" else mt5.ORDER_TYPE_SELL
        price = ask if side=="buy" else bid
        req = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(volume),
            "type": order_type,
            "price": price,
            "deviation": 20,
            "magic": magic,
            "comment": comment,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }
        if sl_points or tp_points:
            info = mt5.symbol_info(symbol); point = info.point if info else 0.0001
            if side == "buy":
                if sl_points: req["sl"] = price - sl_points * point
                if tp_points: req["tp"] = price + tp_points * point
            else:
                if sl_points: req["sl"] = price + sl_points * point
                if tp_points: req["tp"] = price - tp_points * point
        res = mt5.order_send(req)
        if res and res.retcode == mt5.TRADE_RETCODE_DONE:
            return OrderResult(True, "ok", ticket=res.order)
        return OrderResult(False, f"order_send retcode={getattr(res,'retcode',None)}", last_error=mt5.last_error())
'@

$RISK_GUARD = @'
from __future__ import annotations
import os, sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

@dataclass
class AccountState:
    balance: float = 0.0
    equity: float = 0.0
    margin_free: float = 0.0
    open_positions: int = 0

class RiskGuard:
    def __init__(self, sqlite_path: str | None = None):
        self.sqlite_path = sqlite_path or os.getenv("SQLITE_PATH","./memory/lolo.db")
        self.kill_switch = os.getenv("LOLO_KILL_SWITCH","false").lower() in {"1","true","yes","y"}
        self.max_positions = int(os.getenv("MAX_POSITIONS","5"))
        self.max_daily_loss_pct = float(os.getenv("MAX_DAILY_LOSS_PCT","5"))
        self.max_exposure_notional = float(os.getenv("MAX_EXPOSURE_NOTIONAL","0"))

    def _today_iso(self) -> str:
        return datetime.now(timezone.utc).date().isoformat()

    def _db_daily_pnl(self) -> float:
        p = Path(self.sqlite_path)
        if not p.exists(): return 0.0
        try:
            con = sqlite3.connect(str(p)); cur = con.cursor()
            cur.execute("SELECT COALESCE(SUM(pnl),0.0) FROM positions WHERE closed_at LIKE ?", (self._today_iso()+"%",))
            row = cur.fetchone(); con.close()
            return float(row[0] or 0.0)
        except Exception: return 0.0

    def _mt5_account(self):
        try:
            import MetaTrader5 as mt5
            info = mt5.account_info(); positions = mt5.positions_get()
            return AccountState(
                balance=info.balance if info else 0.0,
                equity=info.equity if info else 0.0,
                margin_free=info.margin_free if info else 0.0,
                open_positions=len(positions) if positions else 0,
            )
        except Exception: return AccountState()

    def check_all(self, new_orders: int = 0, est_notional: float = 0.0):
        if self.kill_switch:
            return False, "Kill switch is active (LOLO_KILL_SWITCH=true)."
        acct = self._mt5_account()
        if acct.balance > 0:
            dd = ((acct.equity - acct.balance)/max(acct.balance,1e-9))*100.0
            if abs(dd) >= self.max_daily_loss_pct and (acct.equity < acct.balance):
                return False, f"Daily loss cap hit: {dd:.2f}% ≥ {self.max_daily_loss_pct}%."
        else:
            pnl = self._db_daily_pnl()
            if pnl < 0 and self.max_exposure_notional > 0 and abs(pnl) >= self.max_exposure_notional:
                return False, "Daily loss (db) exceeds exposure guard."
        if acct.open_positions + new_orders > self.max_positions:
            return False, f"Position cap: {acct.open_positions}+{new_orders} > {self.max_positions}."
        if self.max_exposure_notional > 0 and est_notional > self.max_exposure_notional:
            return False, f"Exposure cap: {est_notional} > {self.max_exposure_notional}."
        return True, "OK"
'@

$SMA_AGENT = @'
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
'@

$MAIN = @'
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
    rng = np.random.default_rng(7); ts0 = datetime(2024,1,1)
    ts = [ts0 + timedelta(minutes=i) for i in range(n)]
    base = start + 2.0*np.sin(np.linspace(0,25,n)) + rng.normal(0,0.3,n).cumsum()*0.01
    close = np.maximum(0.1, base)
    open_ = close * (1 + rng.normal(0,0.0005,n))
    high  = (open_.where(open_>close, close)) * (1 + abs(rng.normal(0,0.0008,n)))
    low   = (open_.where(open_<close, close)) * (1 - abs(rng.normal(0,0.0008,n)))
    vol = rng.integers(100,1000,n)
    import pandas as pd
    return pd.DataFrame({"timestamp":ts,"open":open_,"high":high,"low":low,"close":close,"volume":vol})

def run_demo(fast:int, slow:int):
    from backtesting import simple_runner
    df = make_sinewave_ohlcv()
    result = simple_runner.run(df, {"fast":fast,"slow":slow})
    print("[demo] result:", result["summary"]); return 0

def main():
    load_dotenv()
    p = argparse.ArgumentParser(description="Lolo Trading Agent — runtime")
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
'@

$PYPROJECT = @'
[tool.black]
line-length = 100
target-version = ["py311"]
exclude = "\\.venv|dist|build|__pycache__|.git|.chroma|memory|logs"

[tool.ruff]
line-length = 100
target-version = "py311"
select = ["E","F","I","UP","W","B"]
ignore = ["E203","E501"]
exclude = [".venv","dist","build","__pycache__", ".git",".chroma","memory","logs"]

[tool.isort]
profile = "black"
line_length = 100
'@

$PRECOMMIT = @'
repos:
  - repo: https://github.com/psf/black
    rev: 24.8.0
    hooks:
      - id: black
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.8
    hooks:
      - id: ruff
        args: ["--fix"]
  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort
  - repo: https://github.com/adrienverge/yamllint
    rev: v1.35.1
    hooks:
      - id: yamllint
'@

$CI = @'
name: ci
on:
  push:
  pull_request:

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install deps
        run: |
          python -m pip install -U pip
          pip install black ruff isort pytest
          if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
      - name: Ruff (lint)
        run: ruff check .
      - name: Black (format check)
        run: black --check .
      - name: isort (imports)
        run: isort --check-only .
      - name: Run tests
        run: |
          if [ -d tests ]; then pytest -q; fi
'@

$MAKEFILE = @'
PY=python
VENV=.venv

.PHONY: init db health lint fmt precommit

init:
	$(PY) -m venv $(VENV); . $(VENV)/Scripts/activate; pip install -r requirements.txt

db:
	$(PY) utils/db_init.py

health:
	$(PY) tools/api_key_health_check.py

lint:
	ruff check . && black --check . && isort --check-only .

fmt:
	black . && ruff check --fix . && isort .

precommit:
	pip install pre-commit && pre-commit install
'@

$CONSTRAINTS = @'
black==24.8.0
eventlet==0.36.1
flask==3.0.3
flask-socketio==5.3.6
isort==5.13.2
MetaTrader5==5.0.45
numpy==2.1.2
pandas==2.2.3
PyYAML==6.0.2
python-dotenv==1.0.1
pydantic==2.9.2
requests==2.32.3
ruff==0.6.8
ta==0.10.2
chromadb==0.5.5
sentence-transformers==3.0.1
pytest==8.3.3
'@

$REQ_SNIPPET = @'
# Core
pandas>=2.2.0
numpy>=1.26.0
requests>=2.31.0
python-dotenv>=1.0.1
PyYAML>=6.0.1
pydantic>=2.7.0

# Observability (optional)
rich>=13.7.1

# Trading / MT5 (optional but recommended if you execute via MT5)
MetaTrader5>=5.0.45

# TA library (optional if you compute indicators)
ta>=0.10.2

# Memory / RAG (optional; enable if you actually use vector memory)
chromadb>=0.5.5
sentence-transformers>=3.0.1

# Web dashboard (optional; enable if you serve a UI)
flask>=3.0.0
flask-socketio>=5.3.6
eventlet>=0.36.1
'@

Write-TextFile ".env.example" $ENV_EXAMPLE
Write-TextFile "config\instruments.yaml" $INSTRUMENTS_YAML
Write-TextFile "config\strategies.yaml" $STRATEGIES_YAML
Write-TextFile "utils\db_init.py" $DB_INIT
Write-TextFile "tools\api_key_health_check.py" $HEALTH_CHECK
Write-TextFile "utils\config_validate.py" $CONFIG_VALIDATE
Write-TextFile "backtesting\simple_runner.py" $SIMPLE_BT
Write-TextFile "execution\mt5_executor.py" $EXECUTOR
Write-TextFile "risk\guard.py" $RISK_GUARD
Write-TextFile "signals\mt5_sma_agent.py" $SMA_AGENT
Write-TextFile "main.py" $MAIN
Write-TextFile "pyproject.toml" $PYPROJECT
Write-TextFile ".pre-commit-config.yaml" $PRECOMMIT
Write-TextFile ".github\workflows\ci.yml" $CI
Write-TextFile "Makefile" $MAKEFILE
Write-TextFile "constraints.txt" $CONSTRAINTS
Write-TextFile "requirements_snippet.txt" $REQ_SNIPPET

Write-Host "`nAll files written. Next steps:" -ForegroundColor Cyan
Write-Host "  1) py -3.11 -m venv .venv" -ForegroundColor Yellow
Write-Host "  2) .\.venv\Scripts\Activate.ps1" -ForegroundColor Yellow
Write-Host "  3) notepad requirements.txt   (paste from requirements_snippet.txt)" -ForegroundColor Yellow
Write-Host "  4) pip install -r requirements.txt -c constraints.txt" -ForegroundColor Yellow
Write-Host "  5) Copy-Item .env.example .env ; notepad .env  (set MT5_PATH, keep PAPER_TRADING=true)" -ForegroundColor Yellow
Write-Host "  6) python .\utils\db_init.py" -ForegroundColor Yellow
Write-Host "  7) python .\main.py --demo" -ForegroundColor Yellow
Write-Host "  8) python .\main.py --health" -ForegroundColor Yellow
Write-Host "  9) python .\main.py --paper-exec --symbols EURUSD --timeframe M1 --fast 10 --slow 30 --lot 0.01 --once" -ForegroundColor Yellow


