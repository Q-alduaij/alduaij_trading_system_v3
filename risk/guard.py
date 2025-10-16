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
                return False, f"Daily loss cap hit: {dd:.2f}% â‰¥ {self.max_daily_loss_pct}%."
        else:
            pnl = self._db_daily_pnl()
            if pnl < 0 and self.max_exposure_notional > 0 and abs(pnl) >= self.max_exposure_notional:
                return False, "Daily loss (db) exceeds exposure guard."
        if acct.open_positions + new_orders > self.max_positions:
            return False, f"Position cap: {acct.open_positions}+{new_orders} > {self.max_positions}."
        if self.max_exposure_notional > 0 and est_notional > self.max_exposure_notional:
            return False, f"Exposure cap: {est_notional} > {self.max_exposure_notional}."
        return True, "OK"
