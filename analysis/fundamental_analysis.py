"""
Fundamental Analysis
Analyzes economic data and fundamental factors
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from utils.logger import get_logger
from data_collection.market_data import MarketDataCollector

logger = get_logger("main")


class FundamentalAnalyzer:
    """Analyzes fundamental economic data"""
    
    def __init__(self):
        self.market_data = MarketDataCollector()
        self.economic_data_cache = {}
    
    def analyze_economic_indicators(
        self,
        country: str = "US"
    ) -> Dict[str, Any]:
        """
        Analyze economic indicators for a country
        
        Args:
            country: Country code
            
        Returns:
            Economic analysis
        """
        try:
            analysis = {
                'country': country,
                'timestamp': datetime.now().isoformat(),
                'indicators': {}
            }
            
            # GDP
            gdp_data = self.market_data.get_economic_indicators("REAL_GDP")
            if gdp_data:
                analysis['indicators']['gdp'] = self._parse_economic_data(gdp_data)
            
            # Inflation
            inflation_data = self.market_data.get_economic_indicators("INFLATION")
            if inflation_data:
                analysis['indicators']['inflation'] = self._parse_economic_data(inflation_data)
            
            # Unemployment
            unemployment_data = self.market_data.get_economic_indicators("UNEMPLOYMENT")
            if unemployment_data:
                analysis['indicators']['unemployment'] = self._parse_economic_data(unemployment_data)
            
            # Interest rates (Federal Funds Rate)
            interest_data = self.market_data.get_economic_indicators("FEDERAL_FUNDS_RATE")
            if interest_data:
                analysis['indicators']['interest_rate'] = self._parse_economic_data(interest_data)
            
            # Determine overall economic health
            analysis['economic_health'] = self._assess_economic_health(analysis['indicators'])
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing economic indicators: {e}")
            return {'country': country, 'indicators': {}, 'economic_health': 'unknown'}
    
    def _parse_economic_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse economic indicator data"""
        try:
            if 'data' in data:
                latest = data['data'][0] if data['data'] else {}
                return {
                    'value': latest.get('value'),
                    'date': latest.get('date'),
                    'trend': self._determine_trend(data['data'][:5]) if len(data['data']) >= 5 else 'stable'
                }
            return {}
        except Exception as e:
            logger.debug(f"Error parsing economic data: {e}")
            return {}
    
    def _determine_trend(self, data_points: List[Dict[str, Any]]) -> str:
        """Determine trend from data points"""
        try:
            values = [float(d.get('value', 0)) for d in data_points if d.get('value')]
            if len(values) < 2:
                return 'stable'
            
            # Simple trend: compare first and last
            if values[0] > values[-1] * 1.02:
                return 'declining'
            elif values[0] < values[-1] * 0.98:
                return 'rising'
            else:
                return 'stable'
        except Exception:
            return 'stable'
    
    def _assess_economic_health(self, indicators: Dict[str, Any]) -> str:
        """
        Assess overall economic health
        
        Args:
            indicators: Dictionary of economic indicators
            
        Returns:
            Economic health assessment (strong, moderate, weak)
        """
        score = 0
        
        # GDP growth is positive
        if 'gdp' in indicators:
            trend = indicators['gdp'].get('trend', '')
            if trend == 'rising':
                score += 2
            elif trend == 'stable':
                score += 1
        
        # Low inflation
        if 'inflation' in indicators:
            value = indicators['inflation'].get('value')
            if value:
                try:
                    inflation_rate = float(value)
                    if 1.5 <= inflation_rate <= 3.0:  # Target range
                        score += 2
                    elif inflation_rate < 1.5 or inflation_rate > 4.0:
                        score -= 1
                except (ValueError, TypeError):
                    pass
        
        # Low unemployment
        if 'unemployment' in indicators:
            trend = indicators['unemployment'].get('trend', '')
            if trend == 'declining':
                score += 2
            elif trend == 'stable':
                score += 1
        
        # Determine health
        if score >= 4:
            return 'strong'
        elif score >= 2:
            return 'moderate'
        else:
            return 'weak'
    
    def analyze_central_bank_policy(self, country: str = "US") -> Dict[str, Any]:
        """
        Analyze central bank policy
        
        Args:
            country: Country code
            
        Returns:
            Policy analysis
        """
        try:
            # Get interest rate data
            interest_data = self.market_data.get_economic_indicators("FEDERAL_FUNDS_RATE")
            
            if not interest_data or 'data' not in interest_data:
                return {'policy_stance': 'unknown'}
            
            data_points = interest_data['data'][:6]  # Last 6 data points
            
            if len(data_points) < 2:
                return {'policy_stance': 'unknown'}
            
            # Analyze rate changes
            rates = [float(d.get('value', 0)) for d in data_points if d.get('value')]
            
            if len(rates) < 2:
                return {'policy_stance': 'unknown'}
            
            latest_rate = rates[0]
            previous_rate = rates[1]
            
            # Determine policy stance
            if latest_rate > previous_rate * 1.01:
                policy_stance = 'hawkish'  # Raising rates
                impact = 'currency_strengthening'
            elif latest_rate < previous_rate * 0.99:
                policy_stance = 'dovish'  # Lowering rates
                impact = 'currency_weakening'
            else:
                policy_stance = 'neutral'
                impact = 'stable'
            
            return {
                'country': country,
                'current_rate': latest_rate,
                'previous_rate': previous_rate,
                'policy_stance': policy_stance,
                'market_impact': impact,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing central bank policy: {e}")
            return {'policy_stance': 'unknown'}
    
    def get_currency_strength(self, currency: str) -> Dict[str, Any]:
        """
        Assess currency strength based on fundamentals
        
        Args:
            currency: Currency code (USD, EUR, etc.)
            
        Returns:
            Currency strength assessment
        """
        try:
            # Map currency to country
            currency_country_map = {
                'USD': 'US',
                'EUR': 'EU',
                'GBP': 'UK',
                'JPY': 'JP',
                'AUD': 'AU',
                'CAD': 'CA',
                'NZD': 'NZ'
            }
            
            country = currency_country_map.get(currency, 'US')
            
            # Get economic indicators
            economic_analysis = self.analyze_economic_indicators(country)
            policy_analysis = self.analyze_central_bank_policy(country)
            
            # Assess strength
            strength_score = 0
            
            # Economic health
            health = economic_analysis.get('economic_health', 'unknown')
            if health == 'strong':
                strength_score += 3
            elif health == 'moderate':
                strength_score += 1
            
            # Policy stance
            stance = policy_analysis.get('policy_stance', 'unknown')
            if stance == 'hawkish':
                strength_score += 2
            elif stance == 'dovish':
                strength_score -= 2
            
            # Determine overall strength
            if strength_score >= 4:
                strength = 'strong'
            elif strength_score >= 2:
                strength = 'moderate'
            elif strength_score <= -2:
                strength = 'weak'
            else:
                strength = 'neutral'
            
            return {
                'currency': currency,
                'strength': strength,
                'strength_score': strength_score,
                'economic_health': health,
                'policy_stance': stance,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error assessing currency strength for {currency}: {e}")
            return {'currency': currency, 'strength': 'unknown'}
    
    def compare_currencies(self, currency1: str, currency2: str) -> Dict[str, Any]:
        """
        Compare two currencies fundamentally
        
        Args:
            currency1: First currency
            currency2: Second currency
            
        Returns:
            Comparison analysis
        """
        try:
            strength1 = self.get_currency_strength(currency1)
            strength2 = self.get_currency_strength(currency2)
            
            score1 = strength1.get('strength_score', 0)
            score2 = strength2.get('strength_score', 0)
            
            if score1 > score2:
                recommendation = f"{currency1} is fundamentally stronger than {currency2}"
                suggested_direction = 'buy'  # Buy currency1/currency2
            elif score2 > score1:
                recommendation = f"{currency2} is fundamentally stronger than {currency1}"
                suggested_direction = 'sell'  # Sell currency1/currency2
            else:
                recommendation = f"{currency1} and {currency2} are fundamentally balanced"
                suggested_direction = 'neutral'
            
            return {
                'pair': f"{currency1}/{currency2}",
                'currency1_strength': strength1,
                'currency2_strength': strength2,
                'recommendation': recommendation,
                'suggested_direction': suggested_direction,
                'confidence': abs(score1 - score2) / 10.0  # Normalize to 0-1
            }
            
        except Exception as e:
            logger.error(f"Error comparing currencies {currency1}/{currency2}: {e}")
            return {'pair': f"{currency1}/{currency2}", 'suggested_direction': 'neutral'}
    
    def get_fundamental_summary(self, instrument: str) -> Dict[str, Any]:
        """
        Get fundamental analysis summary for an instrument
        
        Args:
            instrument: Trading instrument (e.g., EURUSD)
            
        Returns:
            Fundamental analysis summary
        """
        try:
            # Parse instrument to get currencies
            if len(instrument) == 6 and instrument.isalpha():
                currency1 = instrument[:3]
                currency2 = instrument[3:]
                
                # Compare currencies
                comparison = self.compare_currencies(currency1, currency2)
                
                return {
                    'instrument': instrument,
                    'analysis_type': 'fundamental',
                    'comparison': comparison,
                    'recommendation': comparison.get('suggested_direction', 'neutral'),
                    'confidence': comparison.get('confidence', 0.5),
                    'timestamp': datetime.now().isoformat()
                }
            else:
                # For non-forex instruments, return basic analysis
                return {
                    'instrument': instrument,
                    'analysis_type': 'fundamental',
                    'recommendation': 'neutral',
                    'confidence': 0.5,
                    'note': 'Fundamental analysis limited for non-forex instruments',
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting fundamental summary for {instrument}: {e}")
            return {
                'instrument': instrument,
                'recommendation': 'neutral',
                'confidence': 0.0
            }

