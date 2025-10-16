"""
Helper Functions and Utilities
Common utility functions used across the system
"""

import time
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from functools import wraps
import pytz
from config.settings import Settings


def get_current_time(tz: str = Settings.TIMEZONE) -> datetime:
    """
    Get current time in specified timezone
    
    Args:
        tz: Timezone string (default: Kuwait time)
        
    Returns:
        Current datetime in specified timezone
    """
    timezone = pytz.timezone(tz)
    return datetime.now(timezone)


def format_currency(amount: float, currency: str = "USD") -> str:
    """
    Format amount as currency string
    
    Args:
        amount: Amount to format
        currency: Currency code
        
    Returns:
        Formatted currency string
    """
    return f"{currency} {amount:,.2f}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """
    Format value as percentage string
    
    Args:
        value: Value to format (0.05 = 5%)
        decimals: Number of decimal places
        
    Returns:
        Formatted percentage string
    """
    return f"{value * 100:.{decimals}f}%"


def calculate_position_size(
    account_balance: float,
    risk_percent: float,
    stop_loss_pips: float,
    pip_value: float
) -> float:
    """
    Calculate position size based on risk parameters
    
    Args:
        account_balance: Current account balance
        risk_percent: Risk as percentage (0.01 = 1%)
        stop_loss_pips: Stop loss distance in pips
        pip_value: Value of one pip
        
    Returns:
        Position size in lots
    """
    risk_amount = account_balance * risk_percent
    position_size = risk_amount / (stop_loss_pips * pip_value)
    return round(position_size, 2)


def calculate_pips(entry_price: float, exit_price: float, pip_value: float) -> float:
    """
    Calculate pip difference between two prices
    
    Args:
        entry_price: Entry price
        exit_price: Exit price
        pip_value: Pip value (0.0001 for most forex pairs)
        
    Returns:
        Pip difference
    """
    return abs(exit_price - entry_price) / pip_value


def retry_on_failure(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Decorator for retrying functions on failure with exponential backoff
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff: Multiplier for delay on each retry
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        raise last_exception
            
            raise last_exception
        
        return wrapper
    return decorator


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safely divide two numbers, returning default if denominator is zero
    
    Args:
        numerator: Numerator
        denominator: Denominator
        default: Default value if division by zero
        
    Returns:
        Division result or default
    """
    try:
        return numerator / denominator if denominator != 0 else default
    except (TypeError, ZeroDivisionError):
        return default


def parse_timeframe(timeframe: str) -> int:
    """
    Parse timeframe string to minutes
    
    Args:
        timeframe: Timeframe string (M1, M5, H1, D1, etc.)
        
    Returns:
        Timeframe in minutes
    """
    timeframe_map = {
        'M1': 1,
        'M5': 5,
        'M15': 15,
        'M30': 30,
        'H1': 60,
        'H4': 240,
        'D1': 1440,
        'W1': 10080,
    }
    return timeframe_map.get(timeframe.upper(), 60)


def check_kill_switch() -> bool:
    """
    Check if kill switch file exists
    
    Returns:
        True if kill switch is activated
    """
    kill_switch_path = Settings.BASE_DIR / "stop.txt"
    return kill_switch_path.exists()


def activate_kill_switch():
    """Create kill switch file to stop trading"""
    kill_switch_path = Settings.BASE_DIR / "stop.txt"
    kill_switch_path.write_text(f"Trading stopped at {get_current_time()}")


def deactivate_kill_switch():
    """Remove kill switch file to resume trading"""
    kill_switch_path = Settings.BASE_DIR / "stop.txt"
    if kill_switch_path.exists():
        kill_switch_path.unlink()


def save_json(data: Dict[str, Any], filepath: str):
    """
    Save data as JSON file
    
    Args:
        data: Data to save
        filepath: Path to save file
    """
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, default=str)


def load_json(filepath: str) -> Dict[str, Any]:
    """
    Load data from JSON file
    
    Args:
        filepath: Path to JSON file
        
    Returns:
        Loaded data
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.02) -> float:
    """
    Calculate Sharpe ratio
    
    Args:
        returns: List of returns
        risk_free_rate: Risk-free rate (annual)
        
    Returns:
        Sharpe ratio
    """
    if not returns or len(returns) < 2:
        return 0.0
    
    import numpy as np
    returns_array = np.array(returns)
    excess_returns = returns_array - (risk_free_rate / 252)  # Daily risk-free rate
    
    if np.std(excess_returns) == 0:
        return 0.0
    
    return np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)


def calculate_sortino_ratio(returns: List[float], risk_free_rate: float = 0.02) -> float:
    """
    Calculate Sortino ratio (only considers downside volatility)
    
    Args:
        returns: List of returns
        risk_free_rate: Risk-free rate (annual)
        
    Returns:
        Sortino ratio
    """
    if not returns or len(returns) < 2:
        return 0.0
    
    import numpy as np
    returns_array = np.array(returns)
    excess_returns = returns_array - (risk_free_rate / 252)
    
    # Only consider negative returns for downside deviation
    downside_returns = excess_returns[excess_returns < 0]
    
    if len(downside_returns) == 0 or np.std(downside_returns) == 0:
        return 0.0
    
    return np.mean(excess_returns) / np.std(downside_returns) * np.sqrt(252)


def calculate_max_drawdown(equity_curve: List[float]) -> float:
    """
    Calculate maximum drawdown from equity curve
    
    Args:
        equity_curve: List of equity values over time
        
    Returns:
        Maximum drawdown as percentage
    """
    if not equity_curve or len(equity_curve) < 2:
        return 0.0
    
    import numpy as np
    equity_array = np.array(equity_curve)
    
    # Calculate running maximum
    running_max = np.maximum.accumulate(equity_array)
    
    # Calculate drawdown
    drawdown = (equity_array - running_max) / running_max
    
    return abs(np.min(drawdown))


def is_market_open(instrument_type: str = "forex") -> bool:
    """
    Check if market is open for given instrument type
    
    Args:
        instrument_type: Type of instrument (forex, stocks, crypto)
        
    Returns:
        True if market is open
    """
    current_time = get_current_time()
    day_of_week = current_time.weekday()  # 0 = Monday, 6 = Sunday
    
    if instrument_type == "crypto":
        return True  # Crypto markets are 24/7
    
    if instrument_type == "forex":
        # Forex is closed on weekends
        if day_of_week == 5 or day_of_week == 6:  # Saturday or Sunday
            return False
        return True
    
    if instrument_type == "stocks":
        # Stocks trade during exchange hours (simplified)
        if day_of_week >= 5:  # Weekend
            return False
        # Check if during trading hours (9:30 AM - 4:00 PM EST)
        # This is simplified - actual implementation should check specific exchange hours
        return True
    
    return True

