"""
Fundamental Analysis Agent
Analyzes fundamental economic factors
"""

from typing import Dict, Any
import json
from agents.base_agent import BaseAgent
from analysis.fundamental_analysis import FundamentalAnalyzer


class FundamentalAgent(BaseAgent):
    """Performs fundamental analysis"""
    
    def __init__(self):
        super().__init__("FundamentalAgent")
        self.fundamental_analyzer = FundamentalAnalyzer()
    
    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform fundamental analysis
        
        Args:
            data: Dictionary containing 'instrument'
            
        Returns:
            Fundamental analysis results
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
            
            self.logger.info(f"Performing fundamental analysis on {instrument}")
            
            # Get fundamental summary
            fundamental_summary = self.fundamental_analyzer.get_fundamental_summary(instrument)
            
            # Use LLM for deeper analysis
            llm_analysis = self._analyze_with_llm(instrument, fundamental_summary)
            
            # Determine recommendation
            recommendation = llm_analysis.get('recommendation', fundamental_summary.get('recommendation', 'hold'))
            confidence = llm_analysis.get('confidence', fundamental_summary.get('confidence', 0.5))
            
            # Format result
            result = self.format_analysis_result(
                recommendation=recommendation,
                confidence=confidence,
                reasoning=llm_analysis.get('reasoning', 'Fundamental analysis completed'),
                data={
                    'instrument': instrument,
                    'fundamental_summary': fundamental_summary,
                    'llm_analysis': llm_analysis
                }
            )
            
            # Log decision
            self.log_decision(result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in fundamental analysis: {e}")
            return self.format_analysis_result(
                recommendation='error',
                confidence=0.0,
                reasoning=f"Error during fundamental analysis: {str(e)}",
                data={}
            )
    
    def _analyze_with_llm(
        self,
        instrument: str,
        fundamental_summary: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Use LLM to analyze fundamental data"""
        try:
            # Format fundamental data
            fundamental_str = json.dumps(fundamental_summary, indent=2)
            
            # Create prompt
            messages = [
                self.create_system_message(
                    "an expert fundamental analyst specializing in macroeconomic analysis and currency markets"
                ),
                self.create_user_message(
                    f"Analyze the following fundamental data for {instrument}:\n\n"
                    f"{fundamental_str}\n\n"
                    f"Provide your analysis in the following JSON format:\n"
                    f"{{\n"
                    f'  "recommendation": "buy" | "sell" | "hold",\n'
                    f'  "confidence": 0.0 to 1.0,\n'
                    f'  "reasoning": "detailed explanation based on economic fundamentals",\n'
                    f'  "key_factors": ["list of most important fundamental factors"],\n'
                    f'  "economic_outlook": "brief outlook for the currencies/assets involved",\n'
                    f'  "risks": ["potential risks to consider"]\n'
                    f"}}"
                )
            ]
            
            response = self.call_llm(messages, temperature=0.3)
            
            if response and 'choices' in response:
                content = response['choices'][0]['message']['content']
                analysis = self.extract_json_from_response(content)
                
                if analysis:
                    self.logger.info(f"LLM fundamental analysis: {analysis.get('recommendation')} "
                                   f"(confidence: {analysis.get('confidence')})")
                    return analysis
            
            # Fallback
            return {
                'recommendation': 'hold',
                'confidence': 0.5,
                'reasoning': 'LLM analysis unavailable'
            }
            
        except Exception as e:
            self.logger.error(f"Error in LLM fundamental analysis: {e}")
            return {
                'recommendation': 'hold',
                'confidence': 0.3,
                'reasoning': f'Error in LLM analysis: {str(e)}'
            }

