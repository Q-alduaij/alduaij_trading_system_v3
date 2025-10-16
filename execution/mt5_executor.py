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
