"""
Sentiment Analysis Agent
Analyzes market sentiment from news and social data
"""

from typing import Dict, Any
import json
from agents.base_agent import BaseAgent
from analysis.sentiment_analysis import SentimentAnalyzer
from data_collection.economic_calendar import EconomicCalendar


class SentimentAgent(BaseAgent):
    """Performs sentiment analysis"""
    
    def __init__(self):
        super().__init__("SentimentAgent")
        self.sentiment_analyzer = SentimentAnalyzer()
        self.economic_calendar = EconomicCalendar()
    
    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform sentiment analysis
        
        Args:
            data: Dictionary containing 'instrument'
            
        Returns:
            Sentiment analysis results
        """
        try:
            instrument = data.get('instrument')
            
            if not instrument:
                return self.format_analysis_result(
                    recommendation='error',
                    confidence=0.0,
                    reasoning="No instrument specified",
                    data={}
                )
            
            self.logger.info(f"Performing sentiment analysis on {instrument}")
            
            # Get sentiment summary
            sentiment_summary = self.sentiment_analyzer.get_sentiment_summary(instrument)
            
            # Check economic calendar
            economic_events = self.economic_calendar.get_upcoming_events(hours=24, min_impact="Medium")
            should_pause, upcoming_event = self.economic_calendar.should_pause_trading()
            
            # Use LLM for analysis
            llm_analysis = self._analyze_with_llm(
                instrument,
                sentiment_summary,
                economic_events,
                should_pause
            )
            
            # Determine recommendation
            recommendation = llm_analysis.get('recommendation', sentiment_summary.get('overall_signal', 'hold'))
            confidence = llm_analysis.get('confidence', sentiment_summary.get('confidence', 0.5))
            
            # Adjust for economic events
            if should_pause:
                recommendation = 'hold'
                confidence = 0.3
                self.logger.warning(f"High-impact economic event upcoming: {upcoming_event.get('title')}")
            
            # Format result
            result = self.format_analysis_result(
                recommendation=recommendation,
                confidence=confidence,
                reasoning=llm_analysis.get('reasoning', 'Sentiment analysis completed'),
                data={
                    'instrument': instrument,
                    'sentiment_summary': sentiment_summary,
                    'economic_events': economic_events,
                    'should_pause_trading': should_pause,
                    'upcoming_event': upcoming_event,
                    'llm_analysis': llm_analysis
                }
            )
            
            # Log decision
            self.log_decision(result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in sentiment analysis: {e}")
            return self.format_analysis_result(
                recommendation='error',
                confidence=0.0,
                reasoning=f"Error during sentiment analysis: {str(e)}",
                data={}
            )
    
    def _analyze_with_llm(
        self,
        instrument: str,
        sentiment_summary: Dict[str, Any],
        economic_events: list,
        should_pause: bool
    ) -> Dict[str, Any]:
        """Use LLM to analyze sentiment data"""
        try:
            # Format data
            sentiment_str = json.dumps(sentiment_summary, indent=2)
            events_str = json.dumps(economic_events[:5], indent=2) if economic_events else "No major events"
            
            # Create prompt
            messages = [
                self.create_system_message(
                    "an expert sentiment analyst specializing in market psychology and news analysis"
                ),
                self.create_user_message(
                    f"Analyze the following sentiment data for {instrument}:\n\n"
                    f"Sentiment Summary:\n{sentiment_str}\n\n"
                    f"Upcoming Economic Events:\n{events_str}\n\n"
                    f"Should Pause Trading: {should_pause}\n\n"
                    f"Provide your analysis in the following JSON format:\n"
                    f"{{\n"
                    f'  "recommendation": "buy" | "sell" | "hold",\n'
                    f'  "confidence": 0.0 to 1.0,\n'
                    f'  "reasoning": "detailed explanation based on sentiment and events",\n'
                    f'  "sentiment_impact": "how sentiment affects trading decision",\n'
                    f'  "event_impact": "how upcoming events affect trading decision",\n'
                    f'  "market_mood": "overall market mood assessment"\n'
                    f"}}"
                )
            ]
            
            response = self.call_llm(messages, temperature=0.3)
            
            if response and 'choices' in response:
                content = response['choices'][0]['message']['content']
                analysis = self.extract_json_from_response(content)
                
                if analysis:
                    self.logger.info(f"LLM sentiment analysis: {analysis.get('recommendation')} "
                                   f"(confidence: {analysis.get('confidence')})")
                    return analysis
            
            # Fallback
            return {
                'recommendation': 'hold',
                'confidence': 0.5,
                'reasoning': 'LLM analysis unavailable'
            }
            
        except Exception as e:
            self.logger.error(f"Error in LLM sentiment analysis: {e}")
            return {
                'recommendation': 'hold',
                'confidence': 0.3,
                'reasoning': f'Error in LLM analysis: {str(e)}'
            }

