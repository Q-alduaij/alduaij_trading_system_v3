"""
Market Data Collector
Integrates multiple market data APIs with fallback mechanism
"""

import requests
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import time
from config.settings import Settings
from utils.logger import get_logger
from utils.helpers import retry_on_failure

logger = get_logger("api")


class MarketDataCollector:
    """Collects market data from multiple APIs with fallback"""
    
    def __init__(self):
        self.polygon_key = Settings.POLYGON_API_KEY
        self.finnhub_key = Settings.FINNHUB_API_KEY
        self.alpha_vantage_key = Settings.ALPHA_VANTAGE_API_KEY
        self.twelvedata_key = Settings.TWELVEDATA_API_KEY
        self.fmp_key = Settings.FMP_API_KEY
        
        self.cache = {}
        self.cache_duration = 60  # seconds
    
    def _get_cached(self, key: str) -> Optional[Any]:
        """Get cached data if still valid"""
        if key in self.cache:
            data, timestamp = self.cache[key]
            if time.time() - timestamp < self.cache_duration:
                return data
        return None
    
    def _set_cache(self, key: str, data: Any):
        """Cache data with timestamp"""
        self.cache[key] = (data, time.time())
    
    @retry_on_failure(max_retries=2, delay=1.0)
    def get_quote_polygon(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get quote from Polygon API
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Quote data
        """
        try:
            # Convert symbol format (EURUSD -> C:EURUSD for forex)
            if len(symbol) == 6 and symbol.isalpha():
                polygon_symbol = f"C:{symbol}"
            else:
                polygon_symbol = symbol
            
            url = f"https://api.polygon.io/v2/last/trade/{polygon_symbol}"
            params = {"apiKey": self.polygon_key}
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get('status') == 'OK' and 'results' in data:
                result = data['results']
                return {
                    'symbol': symbol,
                    'price': result.get('p'),
                    'size': result.get('s'),
                    'timestamp': result.get('t'),
                    'source': 'polygon'
                }
            
            return None
            
        except Exception as e:
            logger.debug(f"Polygon API error for {symbol}: {e}")
            return None
    
    @retry_on_failure(max_retries=2, delay=1.0)
    def get_quote_finnhub(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get quote from Finnhub API
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Quote data
        """
        try:
            url = "https://finnhub.io/api/v1/quote"
            params = {
                "symbol": symbol,
                "token": self.finnhub_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if 'c' in data:  # current price
                return {
                    'symbol': symbol,
                    'price': data['c'],
                    'high': data.get('h'),
                    'low': data.get('l'),
                    'open': data.get('o'),
                    'previous_close': data.get('pc'),
                    'timestamp': data.get('t'),
                    'source': 'finnhub'
                }
            
            return None
            
        except Exception as e:
            logger.debug(f"Finnhub API error for {symbol}: {e}")
            return None
    
    @retry_on_failure(max_retries=2, delay=1.0)
    def get_quote_alpha_vantage(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get quote from Alpha Vantage API
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Quote data
        """
        try:
            url = "https://www.alphavantage.co/query"
            params = {
                "function": "GLOBAL_QUOTE",
                "symbol": symbol,
                "apikey": self.alpha_vantage_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if 'Global Quote' in data:
                quote = data['Global Quote']
                return {
                    'symbol': symbol,
                    'price': float(quote.get('05. price', 0)),
                    'high': float(quote.get('03. high', 0)),
                    'low': float(quote.get('04. low', 0)),
                    'open': float(quote.get('02. open', 0)),
                    'volume': int(quote.get('06. volume', 0)),
                    'source': 'alpha_vantage'
                }
            
            return None
            
        except Exception as e:
            logger.debug(f"Alpha Vantage API error for {symbol}: {e}")
            return None
    
    @retry_on_failure(max_retries=2, delay=1.0)
    def get_quote_twelvedata(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get quote from TwelveData API
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Quote data
        """
        try:
            url = "https://api.twelvedata.com/quote"
            params = {
                "symbol": symbol,
                "apikey": self.twelvedata_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if 'close' in data:
                return {
                    'symbol': symbol,
                    'price': float(data.get('close', 0)),
                    'high': float(data.get('high', 0)),
                    'low': float(data.get('low', 0)),
                    'open': float(data.get('open', 0)),
                    'volume': int(data.get('volume', 0)),
                    'timestamp': data.get('timestamp'),
                    'source': 'twelvedata'
                }
            
            return None
            
        except Exception as e:
            logger.debug(f"TwelveData API error for {symbol}: {e}")
            return None
    
    def get_quote(self, symbol: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """
        Get quote with fallback mechanism
        
        Args:
            symbol: Trading symbol
            use_cache: Whether to use cached data
            
        Returns:
            Quote data from first available source
        """
        cache_key = f"quote_{symbol}"
        
        # Check cache
        if use_cache:
            cached = self._get_cached(cache_key)
            if cached:
                return cached
        
        # Try APIs in order
        apis = [
            self.get_quote_polygon,
            self.get_quote_finnhub,
            self.get_quote_twelvedata,
            self.get_quote_alpha_vantage,
        ]
        
        for api_func in apis:
            try:
                quote = api_func(symbol)
                if quote:
                    self._set_cache(cache_key, quote)
                    logger.debug(f"Got quote for {symbol} from {quote['source']}")
                    return quote
            except Exception as e:
                logger.debug(f"API call failed: {e}")
                continue
        
        logger.warning(f"Failed to get quote for {symbol} from all sources")
        return None
    
    def get_technical_indicators(
        self,
        symbol: str,
        indicator: str,
        interval: str = "1day"
    ) -> Optional[Dict[str, Any]]:
        """
        Get technical indicators from Alpha Vantage
        
        Args:
            symbol: Trading symbol
            indicator: Indicator name (RSI, MACD, SMA, EMA, etc.)
            interval: Time interval
            
        Returns:
            Indicator data
        """
        try:
            url = "https://www.alphavantage.co/query"
            params = {
                "function": indicator,
                "symbol": symbol,
                "interval": interval,
                "apikey": self.alpha_vantage_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return data
            
        except Exception as e:
            logger.error(f"Error getting {indicator} for {symbol}: {e}")
            return None
    
    def get_company_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get company information from Financial Modeling Prep
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Company information
        """
        try:
            url = f"https://financialmodeprep.com/api/v3/profile/{symbol}"
            params = {"apikey": self.fmp_key}
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data and len(data) > 0:
                return data[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting company info for {symbol}: {e}")
            return None
    
    def get_economic_indicators(self, indicator: str = "GDP") -> Optional[Dict[str, Any]]:
        """
        Get economic indicators from Alpha Vantage
        
        Args:
            indicator: Economic indicator (GDP, INFLATION, UNEMPLOYMENT, etc.)
            
        Returns:
            Economic indicator data
        """
        try:
            url = "https://www.alphavantage.co/query"
            params = {
                "function": indicator,
                "apikey": self.alpha_vantage_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Error getting {indicator}: {e}")
            return None
    
    def clear_cache(self):
        """Clear all cached data"""
        self.cache = {}
        logger.info("Market data cache cleared")

