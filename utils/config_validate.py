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
    print("[ENV] OK â€” PAPER_TRADING =", env.PAPER_TRADING, ", SQLITE_PATH =", env.SQLITE_PATH)

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
            print(f"[CFG] {f}: failed to load â€” {e}")
            return 2
    if missing:
        print("[CFG] Missing files:", ", ".join(missing))
    return 0

if __name__ == "__main__":
    sys.exit(main())
