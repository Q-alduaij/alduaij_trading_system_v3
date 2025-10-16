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
