"""
Reflexion Learning Module
Implements daily learning cycle for continuous improvement
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta
import json
from memory.database import Database
from memory.vector_store import VectorStore
from utils.logger import get_logger
from config.settings import Settings
import requests

logger = get_logger("learning")


class ReflexionLearner:
    """Implements reflexion-based learning"""
    
    def __init__(self):
        self.db = Database()
        self.vector_store = VectorStore()
    
    def perform_daily_reflexion(self) -> Dict[str, Any]:
        """
        Perform daily reflexion on trading performance
        
        Returns:
            Reflexion results with insights
        """
        try:
            logger.info("=== Starting Daily Reflexion Cycle ===")
            
            # Get today's trades
            trades = self.db.get_trades_by_date(datetime.now().date())
            
            if not trades:
                logger.info("No trades today for reflexion")
                return {'insights': [], 'message': 'No trades to analyze'}
            
            # Analyze performance
            performance = self._analyze_performance(trades)
            
            # Identify patterns
            patterns = self._identify_patterns(trades)
            
            # Generate insights using LLM
            insights = self._generate_insights_with_llm(trades, performance, patterns)
            
            # Store insights
            for insight in insights:
                self.db.insert_learning_insight(
                    insight_type='daily_reflexion',
                    content=insight['content'],
                    confidence=insight.get('confidence', 0.7),
                    metadata=json.dumps(insight.get('metadata', {}))
                )
            
            logger.info(f"Daily reflexion complete. Generated {len(insights)} insights.")
            
            return {
                'date': datetime.now().date().isoformat(),
                'trades_analyzed': len(trades),
                'performance': performance,
                'patterns': patterns,
                'insights': insights
            }
            
        except Exception as e:
            logger.error(f"Error in daily reflexion: {e}")
            return {'error': str(e)}
    
    def _analyze_performance(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze trading performance"""
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t.get('profit', 0) > 0)
        losing_trades = sum(1 for t in trades if t.get('profit', 0) < 0)
        
        total_profit = sum(t.get('profit', 0) for t in trades)
        avg_profit = total_profit / total_trades if total_trades > 0 else 0
        
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_profit': total_profit,
            'average_profit': avg_profit
        }
    
    def _identify_patterns(self, trades: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify patterns in trades"""
        patterns = []
        
        # Pattern: Best performing instrument
        instrument_performance = {}
        for trade in trades:
            instrument = trade.get('instrument', 'unknown')
            profit = trade.get('profit', 0)
            
            if instrument not in instrument_performance:
                instrument_performance[instrument] = {'count': 0, 'total_profit': 0}
            
            instrument_performance[instrument]['count'] += 1
            instrument_performance[instrument]['total_profit'] += profit
        
        # Find best instrument
        if instrument_performance:
            best_instrument = max(instrument_performance.items(), key=lambda x: x[1]['total_profit'])
            patterns.append({
                'type': 'best_instrument',
                'instrument': best_instrument[0],
                'profit': best_instrument[1]['total_profit'],
                'trades': best_instrument[1]['count']
            })
        
        # Pattern: Time-based performance
        # (Simplified - would need more data)
        
        return patterns
    
    def _generate_insights_with_llm(
        self,
        trades: List[Dict[str, Any]],
        performance: Dict[str, Any],
        patterns: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate insights using LLM"""
        try:
            # Format data for LLM
            trades_summary = json.dumps(trades[:10], indent=2)  # Limit to 10 trades
            performance_summary = json.dumps(performance, indent=2)
            patterns_summary = json.dumps(patterns, indent=2)
            
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert trading analyst performing reflexion on trading performance. "
                              "Analyze the data and provide actionable insights for improvement."
                },
                {
                    "role": "user",
                    "content": f"Analyze today's trading performance and provide insights:\n\n"
                              f"Performance Summary:\n{performance_summary}\n\n"
                              f"Patterns Identified:\n{patterns_summary}\n\n"
                              f"Sample Trades:\n{trades_summary}\n\n"
                              f"Provide 3-5 key insights in the following JSON format:\n"
                              f"[\n"
                              f"  {{\n"
                              f'    "content": "insight description",\n'
                              f'    "confidence": 0.0 to 1.0,\n'
                              f'    "actionable": "what to do differently",\n'
                              f'    "category": "risk_management" | "strategy" | "timing" | "instrument_selection"\n'
                              f"  }}\n"
                              f"]"
                }
            ]
            
            response = requests.post(
                url=Settings.LLM_BASE_URL,
                headers={
                    "Authorization": f"Bearer {Settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": Settings.LLM_MODEL,
                    "messages": messages,
                    "temperature": 0.3
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                # Try to parse JSON
                try:
                    insights = json.loads(content)
                    if isinstance(insights, list):
                        logger.info(f"Generated {len(insights)} insights from LLM")
                        return insights
                except json.JSONDecodeError:
                    pass
            
            # Fallback insights
            return self._generate_fallback_insights(performance, patterns)
            
        except Exception as e:
            logger.error(f"Error generating LLM insights: {e}")
            return self._generate_fallback_insights(performance, patterns)
    
    def _generate_fallback_insights(
        self,
        performance: Dict[str, Any],
        patterns: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate basic insights without LLM"""
        insights = []
        
        # Win rate insight
        win_rate = performance.get('win_rate', 0)
        if win_rate < 0.5:
            insights.append({
                'content': f"Win rate is {win_rate*100:.1f}%, below 50%. Consider improving entry criteria.",
                'confidence': 0.8,
                'actionable': "Review and tighten entry conditions",
                'category': 'strategy'
            })
        
        # Profit insight
        total_profit = performance.get('total_profit', 0)
        if total_profit < 0:
            insights.append({
                'content': f"Daily loss of ${abs(total_profit):.2f}. Review risk management.",
                'confidence': 0.9,
                'actionable': "Reduce position sizes or pause trading",
                'category': 'risk_management'
            })
        
        return insights

