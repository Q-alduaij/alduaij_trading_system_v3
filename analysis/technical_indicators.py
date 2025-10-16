"""
Technical Indicators Calculator
Calculates various technical indicators for trading analysis
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
# Try to use pandas_ta if available; otherwise fall back to the 'ta' library.
# This builds a tiny adapter so downstream code can still call ta.rsi(...), ta.sma(...), etc.
try:
    import pandas_ta as ta  # preferred if installed
except Exception:
    import pandas as pd
    import numpy as np
    import ta as ta_lib

    class _TAAdapter:
        @staticmethod
        def rsi(close, length: int = 14):
            from ta.momentum import RSIIndicator
            return RSIIndicator(close=pd.Series(close), window=length, fillna=False).rsi()

        @staticmethod
        def ema(close, length: int = 20):
            from ta.trend import EMAIndicator
            return EMAIndicator(close=pd.Series(close), window=length, fillna=False).ema_indicator()

        @staticmethod
        def sma(close, length: int = 20):
            from ta.trend import SMAIndicator
            return SMAIndicator(close=pd.Series(close), window=length, fillna=False).sma_indicator()

        @staticmethod
        def macd(close, fast: int = 12, slow: int = 26, signal: int = 9):
            from ta.trend import MACD
            m = MACD(
                close=pd.Series(close),
                window_slow=slow,
                window_fast=fast,
                window_sign=signal,
                fillna=False,
            )
            # Return a tuple like pandas_ta often used
            return m.macd(), m.macd_signal(), m.macd_diff()

        @staticmethod
        def atr(high, low, close, length: int = 14):
            from ta.volatility import AverageTrueRange
            a = AverageTrueRange(
                high=pd.Series(high),
                low=pd.Series(low),
                close=pd.Series(close),
                window=length,
                fillna=False,
            )
            return a.average_true_range()

    ta = _TAAdapter()

from utils.logger import get_logger

logger = get_logger("main")


class TechnicalAnalyzer:
    """Calculates and analyzes technical indicators"""
    
    def __init__(self):
        self.indicators_cache = {}
    
    def calculate_all_indicators(
        self,
        df: pd.DataFrame,
        config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Calculate all technical indicators for a dataframe
        
        Args:
            df: DataFrame with OHLCV data
            config: Configuration for indicators
            
        Returns:
            Dictionary of calculated indicators
        """
        if df is None or len(df) < 50:
            logger.warning("Insufficient data for technical analysis")
            return {}
        
        try:
            indicators = {}
            
            # RSI
            rsi = self.calculate_rsi(df)
            if rsi is not None:
                indicators['rsi'] = rsi
            
            # MACD
            macd_data = self.calculate_macd(df)
            if macd_data:
                indicators['macd'] = macd_data
            
            # Moving Averages
            ma_data = self.calculate_moving_averages(df)
            if ma_data:
                indicators['moving_averages'] = ma_data
            
            # Bollinger Bands
            bb_data = self.calculate_bollinger_bands(df)
            if bb_data:
                indicators['bollinger_bands'] = bb_data
            
            # Stochastic
            stoch_data = self.calculate_stochastic(df)
            if stoch_data:
                indicators['stochastic'] = stoch_data
            
            # ATR
            atr = self.calculate_atr(df)
            if atr is not None:
                indicators['atr'] = atr
            
            # Support/Resistance
            sr_levels = self.calculate_support_resistance(df)
            if sr_levels:
                indicators['support_resistance'] = sr_levels
            
            # Volume analysis
            volume_data = self.analyze_volume(df)
            if volume_data:
                indicators['volume'] = volume_data
            
            return indicators
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            return {}
    
    def calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> Optional[float]:
        """Calculate RSI (Relative Strength Index)"""
        try:
            rsi = ta.rsi(df['close'], length=period)
            if rsi is not None and len(rsi) > 0:
                current_rsi = float(rsi.iloc[-1])
                return {
                    'value': current_rsi,
                    'signal': 'overbought' if current_rsi > 70 else 'oversold' if current_rsi < 30 else 'neutral',
                    'period': period
                }
            return None
        except Exception as e:
            logger.debug(f"Error calculating RSI: {e}")
            return None
    
    def calculate_macd(
        self,
        df: pd.DataFrame,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> Optional[Dict[str, Any]]:
        """Calculate MACD"""
        try:
            macd = ta.macd(df['close'], fast=fast, slow=slow, signal=signal)
            if macd is not None and len(macd) > 0:
                macd_line = float(macd[f'MACD_{fast}_{slow}_{signal}'].iloc[-1])
                signal_line = float(macd[f'MACDs_{fast}_{slow}_{signal}'].iloc[-1])
                histogram = float(macd[f'MACDh_{fast}_{slow}_{signal}'].iloc[-1])
                
                return {
                    'macd': macd_line,
                    'signal': signal_line,
                    'histogram': histogram,
                    'trend': 'bullish' if macd_line > signal_line else 'bearish'
                }
            return None
        except Exception as e:
            logger.debug(f"Error calculating MACD: {e}")
            return None
    
    def calculate_moving_averages(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate multiple moving averages"""
        try:
            result = {}
            
            # SMA
            for period in [20, 50, 200]:
                sma = ta.sma(df['close'], length=period)
                if sma is not None and len(sma) > 0:
                    result[f'sma_{period}'] = float(sma.iloc[-1])
            
            # EMA
            for period in [9, 21, 55]:
                ema = ta.ema(df['close'], length=period)
                if ema is not None and len(ema) > 0:
                    result[f'ema_{period}'] = float(ema.iloc[-1])
            
            # Current price
            current_price = float(df['close'].iloc[-1])
            result['current_price'] = current_price
            
            # Determine trend
            if 'sma_20' in result and 'sma_50' in result:
                if result['sma_20'] > result['sma_50']:
                    result['trend'] = 'bullish'
                else:
                    result['trend'] = 'bearish'
            
            return result
        except Exception as e:
            logger.debug(f"Error calculating moving averages: {e}")
            return {}
    
    def calculate_bollinger_bands(
        self,
        df: pd.DataFrame,
        period: int = 20,
        std_dev: float = 2.0
    ) -> Optional[Dict[str, Any]]:
        """Calculate Bollinger Bands"""
        try:
            bbands = ta.bbands(df['close'], length=period, std=std_dev)
            if bbands is not None and len(bbands) > 0:
                upper = float(bbands[f'BBU_{period}_{std_dev}'].iloc[-1])
                middle = float(bbands[f'BBM_{period}_{std_dev}'].iloc[-1])
                lower = float(bbands[f'BBL_{period}_{std_dev}'].iloc[-1])
                current_price = float(df['close'].iloc[-1])
                
                # Determine position
                if current_price > upper:
                    position = 'above_upper'
                elif current_price < lower:
                    position = 'below_lower'
                else:
                    position = 'within_bands'
                
                return {
                    'upper': upper,
                    'middle': middle,
                    'lower': lower,
                    'current_price': current_price,
                    'position': position,
                    'bandwidth': upper - lower
                }
            return None
        except Exception as e:
            logger.debug(f"Error calculating Bollinger Bands: {e}")
            return None
    
    def calculate_stochastic(
        self,
        df: pd.DataFrame,
        k_period: int = 14,
        d_period: int = 3
    ) -> Optional[Dict[str, Any]]:
        """Calculate Stochastic Oscillator"""
        try:
            stoch = ta.stoch(df['high'], df['low'], df['close'], k=k_period, d=d_period)
            if stoch is not None and len(stoch) > 0:
                k_value = float(stoch[f'STOCHk_{k_period}_{d_period}_3'].iloc[-1])
                d_value = float(stoch[f'STOCHd_{k_period}_{d_period}_3'].iloc[-1])
                
                return {
                    'k': k_value,
                    'd': d_value,
                    'signal': 'overbought' if k_value > 80 else 'oversold' if k_value < 20 else 'neutral'
                }
            return None
        except Exception as e:
            logger.debug(f"Error calculating Stochastic: {e}")
            return None
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> Optional[float]:
        """Calculate ATR (Average True Range)"""
        try:
            atr = ta.atr(df['high'], df['low'], df['close'], length=period)
            if atr is not None and len(atr) > 0:
                return {
                    'value': float(atr.iloc[-1]),
                    'period': period
                }
            return None
        except Exception as e:
            logger.debug(f"Error calculating ATR: {e}")
            return None
    
    def calculate_support_resistance(
        self,
        df: pd.DataFrame,
        num_levels: int = 3
    ) -> Dict[str, List[float]]:
        """
        Calculate support and resistance levels
        
        Args:
            df: Price dataframe
            num_levels: Number of levels to identify
            
        Returns:
            Dictionary with support and resistance levels
        """
        try:
            # Use pivot points method
            highs = df['high'].values
            lows = df['low'].values
            closes = df['close'].values
            
            # Find local maxima (resistance) and minima (support)
            resistance_levels = []
            support_levels = []
            
            # Simple method: use recent highs and lows
            recent_data = df.tail(100)
            
            # Resistance: recent highs
            resistance_candidates = recent_data.nlargest(num_levels * 2, 'high')['high'].values
            resistance_levels = list(set([float(x) for x in resistance_candidates]))[:num_levels]
            
            # Support: recent lows
            support_candidates = recent_data.nsmallest(num_levels * 2, 'low')['low'].values
            support_levels = list(set([float(x) for x in support_candidates]))[:num_levels]
            
            return {
                'resistance': sorted(resistance_levels, reverse=True),
                'support': sorted(support_levels)
            }
        except Exception as e:
            logger.debug(f"Error calculating support/resistance: {e}")
            return {'resistance': [], 'support': []}
    
    def analyze_volume(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze volume indicators"""
        try:
            current_volume = float(df['tick_volume'].iloc[-1])
            avg_volume = float(df['tick_volume'].tail(20).mean())
            
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
            
            return {
                'current': current_volume,
                'average': avg_volume,
                'ratio': volume_ratio,
                'signal': 'high' if volume_ratio > 1.5 else 'low' if volume_ratio < 0.5 else 'normal'
            }
        except Exception as e:
            logger.debug(f"Error analyzing volume: {e}")
            return {}
    
    def calculate_fibonacci_levels(
        self,
        df: pd.DataFrame,
        lookback: int = 100
    ) -> Dict[str, float]:
        """Calculate Fibonacci retracement levels"""
        try:
            recent_data = df.tail(lookback)
            high = float(recent_data['high'].max())
            low = float(recent_data['low'].min())
            diff = high - low
            
            levels = {
                '0.0': high,
                '0.236': high - (diff * 0.236),
                '0.382': high - (diff * 0.382),
                '0.500': high - (diff * 0.500),
                '0.618': high - (diff * 0.618),
                '0.786': high - (diff * 0.786),
                '1.0': low
            }
            
            return levels
        except Exception as e:
            logger.debug(f"Error calculating Fibonacci levels: {e}")
            return {}
    
    def get_trading_signals(self, indicators: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate trading signals from indicators
        
        Args:
            indicators: Dictionary of calculated indicators
            
        Returns:
            Dictionary of signals
        """
        signals = {}
        
        try:
            # RSI signal
            if 'rsi' in indicators:
                signals['rsi'] = indicators['rsi']['signal']
            
            # MACD signal
            if 'macd' in indicators:
                signals['macd'] = indicators['macd']['trend']
            
            # Moving average signal
            if 'moving_averages' in indicators:
                signals['ma_trend'] = indicators['moving_averages'].get('trend', 'neutral')
            
            # Bollinger Bands signal
            if 'bollinger_bands' in indicators:
                bb_pos = indicators['bollinger_bands']['position']
                if bb_pos == 'above_upper':
                    signals['bollinger'] = 'overbought'
                elif bb_pos == 'below_lower':
                    signals['bollinger'] = 'oversold'
                else:
                    signals['bollinger'] = 'neutral'
            
            # Stochastic signal
            if 'stochastic' in indicators:
                signals['stochastic'] = indicators['stochastic']['signal']
            
            # Overall signal (simple majority voting)
            bullish_count = sum(1 for s in signals.values() if 'bullish' in str(s).lower() or 'oversold' in str(s).lower())
            bearish_count = sum(1 for s in signals.values() if 'bearish' in str(s).lower() or 'overbought' in str(s).lower())
            
            if bullish_count > bearish_count:
                signals['overall'] = 'bullish'
            elif bearish_count > bullish_count:
                signals['overall'] = 'bearish'
            else:
                signals['overall'] = 'neutral'
            
            return signals
            
        except Exception as e:
            logger.error(f"Error generating trading signals: {e}")
            return {'overall': 'neutral'}

