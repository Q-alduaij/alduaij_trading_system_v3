# web/dashboard.py
import os, json, time, html
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, Depends, Header, Query, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from dotenv import load_dotenv

load_dotenv()

DASHBOARD_TOKEN = os.getenv("DASHBOARD_TOKEN", "")
JOURNAL_PATH = Path(os.getenv("JOURNAL_PATH", "memory/journal.jsonl"))
TITLE = "The pearl ..lolo AI trading system"

app = FastAPI(title=TITLE)

def require_token(
    x_auth: Optional[str] = Header(None),
    token_q: Optional[str] = Query(None, alias="token"),
):
    token = x_auth or token_q
    if not DASHBOARD_TOKEN:
        return True
    if not token or token != DASHBOARD_TOKEN:
        raise HTTPException(status_code=401, detail="Missing/invalid token. Use header X-Auth or ?token=")
    return True

def tail_jsonl(path: Path, limit: int = 50) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            try:
                rows.append(json.loads(s))
            except Exception:
                continue
    return rows[-limit:]

def get_mt5_account() -> Dict[str, Any]:
    acc: Dict[str, Any] = {"connected": False}
    try:
        import MetaTrader5 as mt5
        if not mt5.initialize():
            return acc
        info = mt5.account_info()
        if info is None:
            return acc
        acc.update(
            connected=True,
            login=int(info.login),
            server=str(info.server),
            balance=float(info.balance),
            equity=float(info.equity),
            margin=float(info.margin),
            margin_free=float(info.margin_free),
            currency=str(getattr(info, "currency", "USD")),
        )
        return acc
    except Exception:
        return acc

def get_open_positions() -> List[Dict[str, Any]]:
    try:
        import MetaTrader5 as mt5
        if not mt5.initialize():
            return []
        poss = mt5.positions_get()
        out: List[Dict[str, Any]] = []
        if poss:
            for p in poss:
                out.append(
                    {
                        "ticket": int(p.ticket),
                        "symbol": str(p.symbol),
                        "type": "buy" if p.type == 0 else "sell",
                        "volume": float(p.volume),
                        "price": float(p.price_open),
                        "sl": float(p.sl) if p.sl else None,
                        "tp": float(p.tp) if p.tp else None,
                        "profit": float(p.profit),
                        "time": int(p.time),
                    }
                )
        return out
    except Exception:
        return []

@app.get("/healthz", response_class=PlainTextResponse)
def healthz():
    return "ok"

@app.get("/api/summary", dependencies=[Depends(require_token)])
def api_summary():
    acc = get_mt5_account()
    positions = get_open_positions()
    journal = tail_jsonl(JOURNAL_PATH, limit=200)

    decisions, orders = [], []
    for r in reversed(journal):
        kind = r.get("type") or r.get("kind")
        if kind in ("decision", "ai_decision"):
            decisions.append(r)
        elif kind in ("order", "execution"):
            orders.append(r)

    return {
        "title": TITLE,
        "server_time": int(time.time()),
        "account": acc,
        "positions": positions,
        "orders": orders[:50],
        "decisions": decisions[:50],
    }

INDEX_HTML = r"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>__TITLE__</title>
  <style>
    :root { --bg:#0f172a; --panel:#111827; --txt:#e5e7eb; --muted:#9ca3af; --good:#10b981; --bad:#ef4444; --warn:#f59e0b; }
    * { box-sizing:border-box; }
    body { margin:0; font-family:system-ui,-apple-system,Segoe UI,Roboto,Inter,Arial; background:var(--bg); color:var(--txt); }
    header { padding:16px 20px; border-bottom:1px solid #1f2937; background:#0b1222; position:sticky; top:0; z-index:10; }
    h1 { margin:0; font-size:20px; letter-spacing:.3px; }
    .grid { display:grid; gap:16px; padding:16px; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); }
    .card { background:var(--panel); border:1px solid #1f2937; border-radius:14px; padding:16px; }
    .kpi { font-size:28px; font-weight:700; }
    .row { display:flex; gap:12px; align-items:center; justify-content:space-between; margin:6px 0; }
    table { width:100%; border-collapse:collapse; font-size:14px; }
    th,td { padding:8px 10px; border-bottom:1px solid #1f2937; text-align:left; }
    th { color:var(--muted); font-weight:600; position:sticky; top:0; background:var(--panel); }
    .tag { font-size:12px; padding:2px 8px; border-radius:999px; border:1px solid #374151; color:#cbd5e1; }
    .buy { color:var(--good); }
    .sell { color:var(--bad); }
    .pill { padding:2px 8px; border-radius:999px; background:#0b1222; border:1px solid #1f2937; color:#9ca3af; }
    footer { color:#6b7280; text-align:center; padding:12px; font-size:12px; }
    .muted { color:var(--muted); }
  </style>
</head>
<body>
  <header>
    <h1>🟣 __TITLE__</h1>
    <div class="muted" id="subtitle">Loading…</div>
  </header>

  <section class="grid">
    <div class="card">
      <div class="row"><div>Account</div><span id="acc-server" class="pill">—</span></div>
      <div class="kpi" id="acc-balance">$—</div>
      <div class="row"><div class="muted">Equity</div><div id="acc-equity">—</div></div>
      <div class="row"><div class="muted">Free Margin</div><div id="acc-freemargin">—</div></div>
      <div class="row"><div class="muted">Margin</div><div id="acc-margin">—</div></div>
      <div class="row"><div class="muted">Status</div><div id="acc-status" class="pill">—</div></div>
    </div>

    <div class="card" style="grid-column: 1 / -1;">
      <div class="row"><h3 style="margin:0">Open Positions</h3><span id="pos-count" class="pill">0</span></div>
      <div style="overflow:auto; max-height:260px;">
        <table id="tbl-pos">
          <thead><tr>
            <th>Ticket</th><th>Symbol</th><th>Type</th><th>Vol</th><th>Price</th><th>P/L</th><th>SL</th><th>TP</th><th>Time</th>
          </tr></thead>
          <tbody></tbody>
        </table>
      </div>
    </div>

    <div class="card">
      <div class="row"><h3 style="margin:0">AI Decisions</h3><span id="dec-count" class="pill">0</span></div>
      <div style="overflow:auto; max-height:320px;">
        <table id="tbl-dec">
          <thead><tr><th>Time</th><th>Agent</th><th>Symbol</th><th>Decision</th><th>Conf.</th></tr></thead>
          <tbody></tbody>
        </table>
      </div>
    </div>

    <div class="card">
      <div class="row"><h3 style="margin:0">Recent Orders</h3><span id="ord-count" class="pill">0</span></div>
      <div style="overflow:auto; max-height:320px;">
        <table id="tbl-ord">
          <thead><tr><th>Time</th><th>Symbol</th><th>Side</th><th>Vol</th><th>Price</th><th>Result/PNL</th></tr></thead>
          <tbody></tbody>
        </table>
      </div>
    </div>
  </section>

  <footer>© Lolo Trading — live preview</footer>

<script>
const qs = new URLSearchParams(location.search);
const TOKEN = qs.get("token");
const headers = TOKEN ? {"X-Auth": TOKEN} : {};

function fmtMoney(v, cur="USD"){ if(v==null) return "—"; return (v<0?"-":"") + (cur==="USD"?"$":"") + Math.abs(v).toFixed(2); }
function ts(t){ if(!t) return "—"; const d=new Date((String(t).length>11?t:t*1000)); return d.toLocaleString(); }

async function refresh(){
  const r = await fetch("/api/summary", {headers});
  if(!r.ok){
    document.getElementById("subtitle").innerText = "Auth failed — add ?token=…";
    return;
  }
  const d = await r.json();
  document.getElementById("subtitle").innerText = "Server time: " + ts(d.server_time*1000);

  const a = d.account||{};
  document.getElementById("acc-server").innerText = a.server ? (a.server + " #" + (a.login||"")) : "no-conn";
  document.getElementById("acc-balance").innerText = fmtMoney(a.balance, a.currency||"USD");
  document.getElementById("acc-equity").innerText = fmtMoney(a.equity, a.currency||"USD");
  document.getElementById("acc-freemargin").innerText = fmtMoney(a.margin_free, a.currency||"USD");
  document.getElementById("acc-margin").innerText = fmtMoney(a.margin, a.currency||"USD");
  document.getElementById("acc-status").innerText = a.connected ? "connected" : "disconnected";

  const pt = document.querySelector("#tbl-pos tbody");
  pt.innerHTML="";
  (d.positions||[]).forEach(p=>{
    const tr=document.createElement("tr");
    tr.innerHTML = `<td>${p.ticket}</td><td>${p.symbol}</td><td class="${p.type}">${p.type}</td><td>${p.volume}</td>
                    <td>${p.price?.toFixed?.(5) ?? p.price}</td><td class="${(p.profit||0)>=0?"buy":"sell"}">${fmtMoney(p.profit)}</td>
                    <td>${p.sl??"—"}</td><td>${p.tp??"—"}</td><td>${ts(p.time*1000)}</td>`;
    pt.appendChild(tr);
  });
  document.getElementById("pos-count").innerText = (d.positions||[]).length;

  const dt = document.querySelector("#tbl-dec tbody");
  dt.innerHTML="";
  (d.decisions||[]).forEach(x=>{
    const tr=document.createElement("tr");
    const side = (x.decision || x.recommendation || x.side || "").toLowerCase();
    tr.innerHTML = `<td>${ts(x.ts||x.time||Date.parse(x.timestamp||""))}</td>
                    <td>${x.agent||x.source||"AI"}</td>
                    <td>${x.symbol||x.instrument||"—"}</td>
                    <td class="${side}">${side||"—"}</td>
                    <td>${(x.confidence??x.conf??"—")}</td>`;
    dt.appendChild(tr);
  });
  document.getElementById("dec-count").innerText = (d.decisions||[]).length;

  const ot = document.querySelector("#tbl-ord tbody");
  ot.innerHTML="";
  (d.orders||[]).forEach(o=>{
    const side=(o.side||o.type||"").toLowerCase();
    const pnl = (o.pnl ?? o.profit ?? o.result ?? "—");
    const pnlStr = typeof pnl === "number" ? fmtMoney(pnl) : pnl;
    const price = o.price ?? o.price_open ?? o.filled_price;
    const tr=document.createElement("tr");
    tr.innerHTML = `<td>${ts(o.ts||o.time||Date.parse(o.timestamp||""))}</td>
                    <td>${o.symbol||"—"}</td>
                    <td class="${side}">${side||"—"}</td>
                    <td>${o.volume||o.qty||"—"}</td>
                    <td>${(typeof price==="number") ? price.toFixed(5): (price||"—")}</td>
                    <td>${pnlStr}</td>`;
    ot.appendChild(tr);
  });
  document.getElementById("ord-count").innerText = (d.orders||[]).length;
}

setInterval(refresh, 3000);
refresh();
</script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse, dependencies=[Depends(require_token)])
def index():
    html_text = INDEX_HTML.replace("__TITLE__", html.escape(TITLE))
    return HTMLResponse(html_text)

@app.get("/favicon.ico")
def favicon():
    return PlainTextResponse("", status_code=204)
