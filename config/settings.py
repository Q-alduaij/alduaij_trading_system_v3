"""
Settings and Configuration Management
Loads environment variables and provides centralized configuration
"""

import os
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Central configuration class for Lolo Trading Agent"""
    
    # Project Paths
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / "data"
    LOGS_DIR = BASE_DIR / "logs"
    REPORTS_DIR = BASE_DIR / "reports"
    CONFIG_DIR = BASE_DIR / "config"
    
    # MetaTrader 5 Configuration
    MT5_ACCOUNT = int(os.getenv("MT5_ACCOUNT", "97524161"))
    MT5_PASSWORD = os.getenv("MT5_PASSWORD", "HnOaB-U8")
    MT5_SERVER = os.getenv("MT5_SERVER", "MetaQuotes-Demo")
    MT5_BROKER = os.getenv("MT5_BROKER", "Forex Hedged")
    MT5_MODE = os.getenv("MT5_MODE", "demo")  # demo or live
    
    # AI/LLM Configuration
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    LLM_MODEL = os.getenv("LLM_MODEL", "deepseek/deepseek-chat")
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.0"))
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1/chat/completions")
    
    # Market Data API Keys
    POLYGON_API_KEY = os.getenv("POLYGON_API_KEY", "")
    FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
    ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "")
    TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY", "")
    FMP_API_KEY = os.getenv("FMP_API_KEY", "")
    
    # News & Sentiment API Keys
    NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")
    
    # Web UI Configuration
    FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-in-production")
    FLASK_USERNAME = os.getenv("FLASK_USERNAME", "vimtoo")
    FLASK_PASSWORD = os.getenv("FLASK_PASSWORD", "69098900")
    FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
    FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
    
    # Trading Configuration
    INITIAL_CAPITAL = float(os.getenv("INITIAL_CAPITAL", "10000"))
    TRADING_MODE = os.getenv("TRADING_MODE", "paper")  # paper or live
    TIMEZONE = os.getenv("TIMEZONE", "Asia/Kuwait")
    
    # Risk Management Parameters
    MAX_RISK_PER_TRADE = 0.01  # 1% of account
    MAX_DAILY_LOSS = 0.05  # 5% of account
    MAX_WEEKLY_LOSS = 0.25  # 25% of account
    MAX_TOTAL_EXPOSURE = 0.10  # 10% of account
    MAX_OPEN_POSITIONS = 10
    MAX_POSITIONS_PER_INSTRUMENT = 1
    MAX_POSITION_SIZE = 0.01  # 1% of capital per trade
    MIN_POSITION_SIZE = 0.005  # 0.5% of capital per trade
    MAX_DRAWDOWN = 0.20  # 20% maximum acceptable drawdown
    
    # Safety Mechanisms
    VOLATILITY_MULTIPLIER = 3.0  # Pause if volatility > 3x normal ATR
    MAX_SPREAD_PIPS = 5  # Maximum spread for forex (pips)
    MAX_SPREAD_PERCENT = 0.005  # Maximum spread for stocks (0.5%)
    MAX_SLIPPAGE_PIPS = 2  # Maximum acceptable slippage
    
    # Database Configuration
    DATABASE_PATH = DATA_DIR / "lolo_trading.db"
    VECTOR_DB_PATH = DATA_DIR / "chroma_db"
    
    # Logging Configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
    LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    
    # GitHub Configuration
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
    GITHUB_REPO = os.getenv("GITHUB_REPO", "https://github.com/Q-alduaij/Lolo-Trading-Agent-.git")
    
    @classmethod
    def ensure_directories(cls):
        """Ensure all required directories exist"""
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        cls.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        (cls.REPORTS_DIR / "daily").mkdir(parents=True, exist_ok=True)
        (cls.REPORTS_DIR / "weekly").mkdir(parents=True, exist_ok=True)
        (cls.REPORTS_DIR / "monthly").mkdir(parents=True, exist_ok=True)
        cls.VECTOR_DB_PATH.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def get_config_dict(cls) -> Dict[str, Any]:
        """Return configuration as dictionary"""
        return {
            "mt5": {
                "account": cls.MT5_ACCOUNT,
                "server": cls.MT5_SERVER,
                "broker": cls.MT5_BROKER,
                "mode": cls.MT5_MODE,
            },
            "llm": {
                "model": cls.LLM_MODEL,
                "temperature": cls.LLM_TEMPERATURE,
                "base_url": cls.LLM_BASE_URL,
            },
            "trading": {
                "initial_capital": cls.INITIAL_CAPITAL,
                "mode": cls.TRADING_MODE,
                "timezone": cls.TIMEZONE,
            },
            "risk": {
                "max_risk_per_trade": cls.MAX_RISK_PER_TRADE,
                "max_daily_loss": cls.MAX_DAILY_LOSS,
                "max_weekly_loss": cls.MAX_WEEKLY_LOSS,
                "max_total_exposure": cls.MAX_TOTAL_EXPOSURE,
                "max_open_positions": cls.MAX_OPEN_POSITIONS,
                "max_drawdown": cls.MAX_DRAWDOWN,
            }
        }
    
    @classmethod
    def validate_config(cls) -> bool:
        """Validate that all required configuration is present"""
        required_vars = [
            ("OPENROUTER_API_KEY", cls.OPENROUTER_API_KEY),
            ("MT5_ACCOUNT", cls.MT5_ACCOUNT),
            ("MT5_PASSWORD", cls.MT5_PASSWORD),
        ]
        
        missing = []
        for var_name, var_value in required_vars:
            if not var_value:
                missing.append(var_name)
        
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")
        
        return True


# Initialize directories on import
Settings.ensure_directories()

