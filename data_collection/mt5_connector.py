"""
MetaTrader 5 Connector
Handles connection and data retrieval from MT5 platform
"""

import MetaTrader5 as mt5
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
from config.settings import Settings
from utils.logger import get_logger
from utils.helpers import retry_on_failure
from utils.notifications import notification_manager

logger = get_logger("data")


class MT5Connector:
    """MetaTrader 5 connection and data management"""
    
    def __init__(self):
        self.connected = False
        self.account_info = None
        self.retry_interval = 10  # seconds
    
    @retry_on_failure(max_retries=5, delay=10.0)
    def connect(self) -> bool:
        """
        Connect to MetaTrader 5
        
        Returns:
            True if connected successfully
        """
        try:
            # Initialize MT5
            if not mt5.initialize():
                error = mt5.last_error()
                logger.error(f"MT5 initialization failed: {error}")
                return False
            
            # Login to account
            authorized = mt5.login(
                login=Settings.MT5_ACCOUNT,
                password=Settings.MT5_PASSWORD,
                server=Settings.MT5_SERVER
            )
            
            if not authorized:
                error = mt5.last_error()
                logger.error(f"MT5 login failed: {error}")
                mt5.shutdown()
                return False
            
            # Get account info
            self.account_info = mt5.account_info()
            if self.account_info is None:
                logger.error("Failed to get account info")
                mt5.shutdown()
                return False
            
            self.connected = True
            logger.info(f"Connected to MT5 - Account: {Settings.MT5_ACCOUNT}, Server: {Settings.MT5_SERVER}")
            logger.info(f"Account Balance: ${self.account_info.balance:.2f}, Equity: ${self.account_info.equity:.2f}")
            
            notification_manager.notify_connection_restored("MetaTrader 5")
            
            return True
            
        except Exception as e:
            logger.error(f"MT5 connection error: {e}")
            self.connected = False
            notification_manager.notify_connection_lost("MetaTrader 5")
            return False
    
    def disconnect(self):
        """Disconnect from MT5"""
        if self.connected:
            mt5.shutdown()
            self.connected = False
            logger.info("Disconnected from MT5")
    
    def ensure_connection(self) -> bool:
        """Ensure MT5 is connected, reconnect if necessary"""
        if not self.connected:
            return self.connect()
        
        # Test connection
        try:
            account_info = mt5.account_info()
            if account_info is None:
                logger.warning("MT5 connection lost, reconnecting...")
                self.connected = False
                return self.connect()
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            self.connected = False
            return self.connect()
    
    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """
        Get current account information
        
        Returns:
            Account info dictionary
        """
        if not self.ensure_connection():
            return None
        
        try:
            info = mt5.account_info()
            if info is None:
                return None
            
            return {
                'balance': info.balance,
                'equity': info.equity,
                'margin': info.margin,
                'free_margin': info.margin_free,
                'margin_level': info.margin_level,
                'profit': info.profit,
                'leverage': info.leverage,
                'currency': info.currency,
                'server': info.server,
                'name': info.name,
                'company': info.company
            }
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return None
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get symbol information
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Symbol info dictionary
        """
        if not self.ensure_connection():
            return None
        
        try:
            info = mt5.symbol_info(symbol)
            if info is None:
                logger.warning(f"Symbol not found: {symbol}")
                return None
            
            return {
                'symbol': info.name,
                'bid': info.bid,
                'ask': info.ask,
                'spread': info.spread,
                'digits': info.digits,
                'point': info.point,
                'volume_min': info.volume_min,
                'volume_max': info.volume_max,
                'volume_step': info.volume_step,
                'trade_contract_size': info.trade_contract_size,
                'trade_mode': info.trade_mode,
                'description': info.description
            }
        except Exception as e:
            logger.error(f"Error getting symbol info for {symbol}: {e}")
            return None
    
    def get_current_price(self, symbol: str) -> Optional[Tuple[float, float]]:
        """
        Get current bid/ask price
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Tuple of (bid, ask) prices
        """
        info = self.get_symbol_info(symbol)
        if info:
            return (info['bid'], info['ask'])
        return None
    
    def get_historical_data(
        self,
        symbol: str,
        timeframe: str,
        num_bars: int = 500
    ) -> Optional[pd.DataFrame]:
        """
        Get historical price data
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe (M1, M5, H1, D1, etc.)
            num_bars: Number of bars to retrieve
            
        Returns:
            DataFrame with OHLCV data
        """
        if not self.ensure_connection():
            return None
        
        try:
            # Map timeframe string to MT5 constant
            timeframe_map = {
                'M1': mt5.TIMEFRAME_M1,
                'M5': mt5.TIMEFRAME_M5,
                'M15': mt5.TIMEFRAME_M15,
                'M30': mt5.TIMEFRAME_M30,
                'H1': mt5.TIMEFRAME_H1,
                'H4': mt5.TIMEFRAME_H4,
                'D1': mt5.TIMEFRAME_D1,
                'W1': mt5.TIMEFRAME_W1,
            }
            
            tf = timeframe_map.get(timeframe.upper(), mt5.TIMEFRAME_H1)
            
            # Get bars
            rates = mt5.copy_rates_from_pos(symbol, tf, 0, num_bars)
            
            if rates is None or len(rates) == 0:
                logger.warning(f"No data retrieved for {symbol} {timeframe}")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.set_index('time', inplace=True)
            
            # Rename columns
            df.columns = ['open', 'high', 'low', 'close', 'tick_volume', 'spread', 'real_volume']
            
            return df[['open', 'high', 'low', 'close', 'tick_volume']]
            
        except Exception as e:
            logger.error(f"Error getting historical data for {symbol}: {e}")
            return None
    
    def get_open_positions(self) -> List[Dict[str, Any]]:
        """
        Get all open positions
        
        Returns:
            List of open positions
        """
        if not self.ensure_connection():
            return []
        
        try:
            positions = mt5.positions_get()
            if positions is None:
                return []
            
            result = []
            for pos in positions:
                result.append({
                    'ticket': pos.ticket,
                    'symbol': pos.symbol,
                    'type': 'buy' if pos.type == mt5.ORDER_TYPE_BUY else 'sell',
                    'volume': pos.volume,
                    'open_price': pos.price_open,
                    'current_price': pos.price_current,
                    'sl': pos.sl,
                    'tp': pos.tp,
                    'profit': pos.profit,
                    'swap': pos.swap,
                    'commission': pos.commission,
                    'open_time': datetime.fromtimestamp(pos.time),
                    'comment': pos.comment
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting open positions: {e}")
            return []
    
    def get_closed_trades(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get closed trades from history
        
        Args:
            days: Number of days to look back
            
        Returns:
            List of closed trades
        """
        if not self.ensure_connection():
            return []
        
        try:
            # Get history
            from_date = datetime.now() - timedelta(days=days)
            to_date = datetime.now()
            
            deals = mt5.history_deals_get(from_date, to_date)
            if deals is None:
                return []
            
            result = []
            for deal in deals:
                if deal.entry == mt5.DEAL_ENTRY_OUT:  # Only closing deals
                    result.append({
                        'ticket': deal.ticket,
                        'order': deal.order,
                        'symbol': deal.symbol,
                        'type': 'buy' if deal.type == mt5.DEAL_TYPE_BUY else 'sell',
                        'volume': deal.volume,
                        'price': deal.price,
                        'profit': deal.profit,
                        'swap': deal.swap,
                        'commission': deal.commission,
                        'time': datetime.fromtimestamp(deal.time),
                        'comment': deal.comment
                    })
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting closed trades: {e}")
            return []
    
    def check_symbol_availability(self, symbol: str) -> bool:
        """
        Check if symbol is available for trading
        
        Args:
            symbol: Trading symbol
            
        Returns:
            True if symbol is available
        """
        if not self.ensure_connection():
            return False
        
        info = mt5.symbol_info(symbol)
        if info is None:
            return False
        
        # Enable symbol if not visible
        if not info.visible:
            if not mt5.symbol_select(symbol, True):
                logger.warning(f"Failed to enable symbol: {symbol}")
                return False
        
        return True
    
    def get_market_status(self, symbol: str) -> str:
        """
        Get market status for symbol
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Market status (open, closed, unknown)
        """
        info = self.get_symbol_info(symbol)
        if info is None:
            return "unknown"
        
        # Check if market is open based on trade mode
        if info['trade_mode'] == 4:  # SYMBOL_TRADE_MODE_FULL
            return "open"
        elif info['trade_mode'] == 0:  # SYMBOL_TRADE_MODE_DISABLED
            return "closed"
        else:
            return "limited"

