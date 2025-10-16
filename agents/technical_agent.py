"""
Technical Analysis Agent
Performs technical analysis using indicators
"""

from typing import Dict, Any
import json
from agents.base_agent import BaseAgent
from analysis.technical_indicators import TechnicalAnalyzer
from data_collection.mt5_connector import MT5Connector


class TechnicalAgent(BaseAgent):
    """Performs technical analysis on instruments"""
    
    def __init__(self):
        super().__init__("TechnicalAgent")
        self.technical_analyzer = TechnicalAnalyzer()
        self.mt5 = MT5Connector()
    
    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform technical analysis
        
        Args:
            data: Dictionary containing 'instrument' and optionally 'timeframe'
            
        Returns:
            Technical analysis results
        """
        try:
            instrument = data.get('instrument')
            timeframe = data.get('timeframe', 'H1')
            
            if not instrument:
                return self.format_analysis_result(
                    recommendation='error',
                    confidence=0.0,
                    reasoning="No instrument specified",
                    data={}
                )
            
            self.logger.info(f"Performing technical analysis on {instrument} ({timeframe})")
            
            # Get historical data
            historical_data = self.mt5.get_historical_data(instrument, timeframe, 500)
            
            if historical_data is None or len(historical_data) < 50:
                return self.format_analysis_result(
                    recommendation='insufficient_data',
                    confidence=0.0,
                    reasoning="Insufficient historical data for technical analysis",
                    data={'instrument': instrument}
                )
            
            # Calculate all indicators
            indicators = self.technical_analyzer.calculate_all_indicators(historical_data)
            
            if not indicators:
                return self.format_analysis_result(
                    recommendation='error',
                    confidence=0.0,
                    reasoning="Failed to calculate technical indicators",
                    data={'instrument': instrument}
                )
            
            # Get trading signals
            signals = self.technical_analyzer.get_trading_signals(indicators)
            
            # Use LLM for detailed analysis
            llm_analysis = self._analyze_with_llm(instrument, indicators, signals)
            
            # Determine recommendation
            recommendation, confidence = self._determine_recommendation(signals, llm_analysis)
            
            # Format result
            result = self.format_analysis_result(
                recommendation=recommendation,
                confidence=confidence,
                reasoning=llm_analysis.get('reasoning', 'Technical analysis completed'),
                data={
                    'instrument': instrument,
                    'timeframe': timeframe,
                    'indicators': indicators,
                    'signals': signals,
                    'llm_analysis': llm_analysis
                }
            )
            
            # Log decision
            self.log_decision(result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in technical analysis: {e}")
            return self.format_analysis_result(
                recommendation='error',
                confidence=0.0,
                reasoning=f"Error during technical analysis: {str(e)}",
                data={}
            )
    
    def _analyze_with_llm(
        self,
        instrument: str,
        indicators: Dict[str, Any],
        signals: Dict[str, str]
    ) -> Dict[str, Any]:
        """Use LLM to analyze technical indicators"""
        try:
            # Prepare indicators summary
            indicators_summary = self._format_indicators_for_llm(indicators)
            signals_summary = json.dumps(signals, indent=2)
            
            # Create prompt
            messages = [
                self.create_system_message(
                    "an expert technical analyst specializing in forex and CFD trading"
                ),
                self.create_user_message(
                    f"Analyze the following technical indicators for {instrument}:\n\n"
                    f"Indicators:\n{indicators_summary}\n\n"
                    f"Signals:\n{signals_summary}\n\n"
                    f"Provide your analysis in the following JSON format:\n"
                    f"{{\n"
                    f'  "recommendation": "buy" | "sell" | "hold",\n'
                    f'  "confidence": 0.0 to 1.0,\n'
                    f'  "reasoning": "detailed explanation",\n'
                    f'  "key_indicators": ["list of most important indicators"],\n'
                    f'  "entry_suggestion": "suggested entry strategy",\n'
                    f'  "stop_loss_suggestion": "suggested stop loss level",\n'
                    f'  "take_profit_suggestion": "suggested take profit level"\n'
                    f"}}"
                )
            ]
            
            response = self.call_llm(messages, temperature=0.3)
            
            if response and 'choices' in response:
                content = response['choices'][0]['message']['content']
                analysis = self.extract_json_from_response(content)
                
                if analysis:
                    self.logger.info(f"LLM technical analysis: {analysis.get('recommendation')} "
                                   f"(confidence: {analysis.get('confidence')})")
                    return analysis
            
            # Fallback if LLM fails
            return {
                'recommendation': signals.get('overall', 'hold'),
                'confidence': 0.5,
                'reasoning': 'LLM analysis unavailable, using signal-based recommendation',
                'key_indicators': list(signals.keys())
            }
            
        except Exception as e:
            self.logger.error(f"Error in LLM technical analysis: {e}")
            return {
                'recommendation': 'hold',
                'confidence': 0.3,
                'reasoning': f'Error in LLM analysis: {str(e)}'
            }
    
    def _format_indicators_for_llm(self, indicators: Dict[str, Any]) -> str:
        """Format indicators for LLM consumption"""
        lines = []
        
        # RSI
        if 'rsi' in indicators:
            rsi = indicators['rsi']
            lines.append(f"RSI: {rsi['value']:.2f} ({rsi['signal']})")
        
        # MACD
        if 'macd' in indicators:
            macd = indicators['macd']
            lines.append(f"MACD: {macd['macd']:.5f}, Signal: {macd['signal']:.5f}, "
                        f"Histogram: {macd['histogram']:.5f} ({macd['trend']})")
        
        # Moving Averages
        if 'moving_averages' in indicators:
            ma = indicators['moving_averages']
            lines.append(f"Moving Averages Trend: {ma.get('trend', 'N/A')}")
            if 'sma_20' in ma:
                lines.append(f"  SMA20: {ma['sma_20']:.5f}")
            if 'sma_50' in ma:
                lines.append(f"  SMA50: {ma['sma_50']:.5f}")
        
        # Bollinger Bands
        if 'bollinger_bands' in indicators:
            bb = indicators['bollinger_bands']
            lines.append(f"Bollinger Bands: Position={bb['position']}, "
                        f"Upper={bb['upper']:.5f}, Lower={bb['lower']:.5f}")
        
        # Stochastic
        if 'stochastic' in indicators:
            stoch = indicators['stochastic']
            lines.append(f"Stochastic: K={stoch['k']:.2f}, D={stoch['d']:.2f} ({stoch['signal']})")
        
        # ATR
        if 'atr' in indicators:
            atr = indicators['atr']
            lines.append(f"ATR: {atr['value']:.5f}")
        
        # Support/Resistance
        if 'support_resistance' in indicators:
            sr = indicators['support_resistance']
            if sr.get('resistance'):
                lines.append(f"Resistance Levels: {', '.join([f'{r:.5f}' for r in sr['resistance'][:3]])}")
            if sr.get('support'):
                lines.append(f"Support Levels: {', '.join([f'{s:.5f}' for s in sr['support'][:3]])}")
        
        return "\n".join(lines)
    
    def _determine_recommendation(
        self,
        signals: Dict[str, str],
        llm_analysis: Dict[str, Any]
    ) -> tuple[str, float]:
        """Determine final recommendation and confidence"""
        # Prefer LLM recommendation if available and confident
        llm_rec = llm_analysis.get('recommendation', '').lower()
        llm_conf = llm_analysis.get('confidence', 0.0)
        
        if llm_rec in ['buy', 'sell', 'hold'] and llm_conf >= 0.6:
            return llm_rec, llm_conf
        
        # Fall back to signal-based recommendation
        overall_signal = signals.get('overall', 'neutral').lower()
        
        if 'bullish' in overall_signal:
            return 'buy', 0.6
        elif 'bearish' in overall_signal:
            return 'sell', 0.6
        else:
            return 'hold', 0.5

