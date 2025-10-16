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
