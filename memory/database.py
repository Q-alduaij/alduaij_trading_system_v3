"""
Database Management
SQLite database for storing trades, performance metrics, and agent memory
"""

import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from config.settings import Settings
from utils.logger import get_logger

logger = get_logger("main")


class Database:
    """SQLite database manager"""
    
    def __init__(self, db_path: Path = Settings.DATABASE_PATH):
        self.db_path = db_path
        self.connection = None
        self._connect()
    
    def _connect(self):
        """Establish database connection"""
        try:
            self.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=10.0
            )
            self.connection.row_factory = sqlite3.Row
            logger.info(f"Connected to database: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a query"""
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params)
            self.connection.commit()
            return cursor
        except Exception as e:
            logger.error(f"Database query error: {e}")
            logger.error(f"Query: {query}")
            raise
    
    def fetchone(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """Fetch one result"""
        cursor = self.execute(query, params)
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def fetchall(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Fetch all results"""
        cursor = self.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")
    
    # Trade Management
    
    def insert_trade(self, trade_data: Dict[str, Any]) -> int:
        """
        Insert a new trade record
        
        Args:
            trade_data: Trade information
            
        Returns:
            Trade ID
        """
        query = """
        INSERT INTO trades (
            instrument, action, entry_time, entry_price, volume,
            stop_loss, take_profit, strategy, reasoning, confidence,
            agent_votes, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            trade_data.get('instrument'),
            trade_data.get('action'),
            trade_data.get('entry_time', datetime.now().isoformat()),
            trade_data.get('entry_price'),
            trade_data.get('volume'),
            trade_data.get('stop_loss'),
            trade_data.get('take_profit'),
            trade_data.get('strategy'),
            trade_data.get('reasoning'),
            trade_data.get('confidence'),
            trade_data.get('agent_votes'),
            trade_data.get('status', 'open')
        )
        cursor = self.execute(query, params)
        return cursor.lastrowid
    
    def update_trade(self, trade_id: int, update_data: Dict[str, Any]):
        """Update trade record"""
        set_clause = ", ".join([f"{key} = ?" for key in update_data.keys()])
        query = f"UPDATE trades SET {set_clause} WHERE id = ?"
        params = tuple(update_data.values()) + (trade_id,)
        self.execute(query, params)
    
    def close_trade(
        self,
        trade_id: int,
        exit_price: float,
        exit_time: str = None,
        pnl: float = 0.0
    ):
        """Close a trade"""
        if exit_time is None:
            exit_time = datetime.now().isoformat()
        
        self.update_trade(trade_id, {
            'exit_time': exit_time,
            'exit_price': exit_price,
            'pnl': pnl,
            'status': 'closed'
        })
    
    def get_open_trades(self) -> List[Dict[str, Any]]:
        """Get all open trades"""
        query = "SELECT * FROM trades WHERE status = 'open' ORDER BY entry_time DESC"
        return self.fetchall(query)
    
    def get_closed_trades(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent closed trades"""
        query = "SELECT * FROM trades WHERE status = 'closed' ORDER BY exit_time DESC LIMIT ?"
        return self.fetchall(query, (limit,))
    
    def get_trade_by_id(self, trade_id: int) -> Optional[Dict[str, Any]]:
        """Get trade by ID"""
        query = "SELECT * FROM trades WHERE id = ?"
        return self.fetchone(query, (trade_id,))
    
    # Performance Metrics
    
    def insert_performance_metric(self, metrics: Dict[str, Any]):
        """Insert daily performance metrics"""
        query = """
        INSERT INTO performance_metrics (
            date, total_pnl, win_rate, profit_factor, avg_win, avg_loss,
            max_drawdown, sharpe_ratio, sortino_ratio, total_trades,
            winning_trades, losing_trades
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            metrics.get('date', datetime.now().date().isoformat()),
            metrics.get('total_pnl', 0.0),
            metrics.get('win_rate', 0.0),
            metrics.get('profit_factor', 0.0),
            metrics.get('avg_win', 0.0),
            metrics.get('avg_loss', 0.0),
            metrics.get('max_drawdown', 0.0),
            metrics.get('sharpe_ratio', 0.0),
            metrics.get('sortino_ratio', 0.0),
            metrics.get('total_trades', 0),
            metrics.get('winning_trades', 0),
            metrics.get('losing_trades', 0)
        )
        self.execute(query, params)
    
    def get_performance_metrics(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get performance metrics for last N days"""
        query = """
        SELECT * FROM performance_metrics
        ORDER BY date DESC
        LIMIT ?
        """
        return self.fetchall(query, (days,))
    
    # Agent Memory
    
    def insert_agent_memory(
        self,
        agent_name: str,
        memory_type: str,
        content: str,
        metadata: str = None
    ):
        """Store agent memory"""
        query = """
        INSERT INTO agent_memory (agent_name, memory_type, content, metadata, timestamp)
        VALUES (?, ?, ?, ?, ?)
        """
        params = (agent_name, memory_type, content, metadata, datetime.now().isoformat())
        self.execute(query, params)
    
    def get_agent_memory(
        self,
        agent_name: str,
        memory_type: str = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Retrieve agent memory"""
        if memory_type:
            query = """
            SELECT * FROM agent_memory
            WHERE agent_name = ? AND memory_type = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """
            params = (agent_name, memory_type, limit)
        else:
            query = """
            SELECT * FROM agent_memory
            WHERE agent_name = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """
            params = (agent_name, limit)
        
        return self.fetchall(query, params)
    
    # Market Conditions
    
    def insert_market_condition(self, condition_data: Dict[str, Any]):
        """Store market condition snapshot"""
        query = """
        INSERT INTO market_conditions (
            timestamp, instrument, timeframe, indicators, news_sentiment,
            volatility, spread, market_session
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            condition_data.get('timestamp', datetime.now().isoformat()),
            condition_data.get('instrument'),
            condition_data.get('timeframe'),
            condition_data.get('indicators'),
            condition_data.get('news_sentiment'),
            condition_data.get('volatility'),
            condition_data.get('spread'),
            condition_data.get('market_session')
        )
        self.execute(query, params)
    
    def get_market_conditions(
        self,
        instrument: str,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Get recent market conditions for instrument"""
        query = """
        SELECT * FROM market_conditions
        WHERE instrument = ?
        AND datetime(timestamp) >= datetime('now', '-' || ? || ' hours')
        ORDER BY timestamp DESC
        """
        return self.fetchall(query, (instrument, hours))


def init_database(db_path: Path = Settings.DATABASE_PATH):
    """
    Initialize database with required tables
    
    Args:
        db_path: Path to database file
    """
    logger.info("Initializing database...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Trades table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        instrument TEXT NOT NULL,
        action TEXT NOT NULL,
        entry_time TEXT NOT NULL,
        entry_price REAL NOT NULL,
        exit_time TEXT,
        exit_price REAL,
        volume REAL NOT NULL,
        stop_loss REAL,
        take_profit REAL,
        pnl REAL DEFAULT 0.0,
        strategy TEXT,
        reasoning TEXT,
        confidence REAL,
        agent_votes TEXT,
        status TEXT DEFAULT 'open',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Performance metrics table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS performance_metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL UNIQUE,
        total_pnl REAL DEFAULT 0.0,
        win_rate REAL DEFAULT 0.0,
        profit_factor REAL DEFAULT 0.0,
        avg_win REAL DEFAULT 0.0,
        avg_loss REAL DEFAULT 0.0,
        max_drawdown REAL DEFAULT 0.0,
        sharpe_ratio REAL DEFAULT 0.0,
        sortino_ratio REAL DEFAULT 0.0,
        total_trades INTEGER DEFAULT 0,
        winning_trades INTEGER DEFAULT 0,
        losing_trades INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Agent memory table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agent_memory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agent_name TEXT NOT NULL,
        memory_type TEXT NOT NULL,
        content TEXT NOT NULL,
        metadata TEXT,
        timestamp TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Market conditions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS market_conditions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        instrument TEXT NOT NULL,
        timeframe TEXT,
        indicators TEXT,
        news_sentiment REAL,
        volatility REAL,
        spread REAL,
        market_session TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_instrument ON trades(instrument)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_memory_agent ON agent_memory(agent_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_market_conditions_instrument ON market_conditions(instrument)")
    
    conn.commit()
    conn.close()
    
    logger.info("Database initialized successfully")


# Initialize database on module import
if not Settings.DATABASE_PATH.exists():
    init_database()

