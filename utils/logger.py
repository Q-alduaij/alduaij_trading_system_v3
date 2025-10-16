"""
Logging Configuration and Setup
Provides comprehensive logging for all system components
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional
from config.settings import Settings


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{log_color}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)


def setup_logger(
    name: str,
    log_file: Optional[str] = None,
    level: str = "INFO",
    console: bool = True
) -> logging.Logger:
    """
    Setup a logger with file and console handlers
    
    Args:
        name: Logger name
        log_file: Log file name (without path)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        console: Whether to add console handler
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Create formatters
    file_formatter = logging.Formatter(
        Settings.LOG_FORMAT,
        datefmt=Settings.LOG_DATE_FORMAT
    )
    console_formatter = ColoredFormatter(
        Settings.LOG_FORMAT,
        datefmt=Settings.LOG_DATE_FORMAT
    )
    
    # File handler (rotating)
    if log_file:
        log_path = Settings.LOGS_DIR / log_file
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper()))
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get an existing logger or create a new one
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Setup main loggers on module import
def initialize_loggers():
    """Initialize all main system loggers"""
    
    # Main system logger
    setup_logger("main", "main.log", Settings.LOG_LEVEL)
    
    # Trading decisions and executions
    setup_logger("trading", "trading.log", Settings.LOG_LEVEL)
    
    # Agent reasoning and communication
    setup_logger("agents", "agents.log", Settings.LOG_LEVEL)
    
    # External API calls
    setup_logger("api", "api.log", Settings.LOG_LEVEL)
    
    # Errors only
    error_logger = setup_logger("errors", "errors.log", "ERROR", console=False)
    
    # Risk management
    setup_logger("risk", "trading.log", Settings.LOG_LEVEL)
    
    # Data collection
    setup_logger("data", "api.log", Settings.LOG_LEVEL)
    
    get_logger("main").info("Logging system initialized")


# Initialize on import
initialize_loggers()

