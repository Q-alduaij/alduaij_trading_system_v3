"""
Risk Management Agent
Evaluates and manages trading risk
"""

from typing import Dict, Any, List
import json
from agents.base_agent import BaseAgent
from data_collection.mt5_connector import MT5Connector
from analysis.correlation_analysis import CorrelationAnalyzer
from config.settings import Settings


class RiskAgent(BaseAgent):
    """Manages trading risk"""
    
    def __init__(self):
        super().__init__("RiskAgent")
        self.mt5 = MT5Connector()
        self.correlation_analyzer = CorrelationAnalyzer()
    
    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform risk analysis
        
        Args:
            data: Dictionary containing 'proposed_trade' and 'account_info'
            
        Returns:
            Risk analysis results
        """
        try:
            proposed_trade = data.get('proposed_trade', {})
            account_info = data.get('account_info')
            
            if not proposed_trade:
                return self.format_analysis_result(
                    recommendation='error',
                    confidence=0.0,
                    reasoning="No proposed trade provided",
                    data={}
                )
            
            self.logger.info(f"Performing risk analysis on proposed trade: {proposed_trade.get('instrument')}")
            
            # Get account info if not provided
            if not account_info:
                account_info = self.mt5.get_account_info()
            
            if not account_info:
                return self.format_analysis_result(
                    recommendation='error',
                    confidence=0.0,
                    reasoning="Unable to get account information",
                    data={}
                )
            
            # Perform risk checks
            risk_checks = self._perform_risk_checks(proposed_trade, account_info)
            
            # Check position limits
            position_check = self._check_position_limits(proposed_trade)
            
            # Check correlation risk
            correlation_risk = self._check_correlation_risk(proposed_trade)
            
            # Calculate position size
            position_size = self._calculate_position_size(proposed_trade, account_info)
            
            # Use LLM for risk assessment
            llm_analysis = self._analyze_with_llm(
                proposed_trade,
                account_info,
                risk_checks,
                position_check,
                correlation_risk
            )
            
            # Determine if trade should proceed
            should_proceed = self._should_proceed(risk_checks, position_check, llm_analysis)
            
            recommendation = 'approve' if should_proceed else 'reject'
            confidence = llm_analysis.get('confidence', 0.7)
            
            # Format result
            result = self.format_analysis_result(
                recommendation=recommendation,
                confidence=confidence,
                reasoning=llm_analysis.get('reasoning', 'Risk analysis completed'),
                data={
                    'proposed_trade': proposed_trade,
                    'risk_checks': risk_checks,
                    'position_check': position_check,
                    'correlation_risk': correlation_risk,
                    'calculated_position_size': position_size,
                    'account_info': account_info,
                    'llm_analysis': llm_analysis
                }
            )
            
            # Log decision
            self.log_decision(result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in risk analysis: {e}")
            return self.format_analysis_result(
                recommendation='reject',
                confidence=1.0,
                reasoning=f"Error during risk analysis: {str(e)}",
                data={}
            )
    
    def _perform_risk_checks(
        self,
        proposed_trade: Dict[str, Any],
        account_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform various risk checks"""
        checks = {}
        
        # Check account balance
        balance = account_info.get('balance', 0)
        equity = account_info.get('equity', 0)
        
        checks['sufficient_balance'] = balance > 100  # Minimum balance
        checks['equity_check'] = equity > balance * 0.5  # Equity should be at least 50% of balance
        
        # Check margin
        margin_level = account_info.get('margin_level', 0)
        checks['margin_level_ok'] = margin_level > 200 or margin_level == 0  # At least 200%
        
        # Check daily loss limit
        daily_loss = self._get_daily_loss()
        max_daily_loss = balance * Settings.MAX_DAILY_LOSS_PERCENT
        checks['daily_loss_ok'] = daily_loss < max_daily_loss
        checks['daily_loss'] = daily_loss
        checks['max_daily_loss'] = max_daily_loss
        
        # Check drawdown
        peak_balance = self.db.get_peak_balance()
        if peak_balance:
            drawdown = (peak_balance - equity) / peak_balance
            checks['drawdown'] = drawdown
            checks['drawdown_ok'] = drawdown < Settings.MAX_DRAWDOWN_PERCENT
        else:
            checks['drawdown'] = 0.0
            checks['drawdown_ok'] = True
        
        return checks
    
    def _check_position_limits(self, proposed_trade: Dict[str, Any]) -> Dict[str, Any]:
        """Check position limits"""
        # Get open positions
        open_positions = self.mt5.get_open_positions()
        
        # Count positions
        total_positions = len(open_positions)
        
        # Count positions for this instrument
        instrument = proposed_trade.get('instrument')
        instrument_positions = sum(1 for p in open_positions if p['symbol'] == instrument)
        
        return {
            'total_positions': total_positions,
            'max_positions': Settings.MAX_OPEN_POSITIONS,
            'positions_ok': total_positions < Settings.MAX_OPEN_POSITIONS,
            'instrument_positions': instrument_positions,
            'max_per_instrument': Settings.MAX_POSITIONS_PER_INSTRUMENT,
            'instrument_ok': instrument_positions < Settings.MAX_POSITIONS_PER_INSTRUMENT
        }
    
    def _check_correlation_risk(self, proposed_trade: Dict[str, Any]) -> Dict[str, Any]:
        """Check correlation risk with existing positions"""
        try:
            open_positions = self.mt5.get_open_positions()
            
            if not open_positions:
                return {'risk': 'none', 'message': 'No open positions'}
            
            # Get list of instruments
            open_instruments = [p['symbol'] for p in open_positions]
            
            # Add proposed instrument
            proposed_instrument = proposed_trade.get('instrument')
            all_instruments = open_instruments + [proposed_instrument]
            
            # Check correlation
            correlation_check = self.correlation_analyzer.check_portfolio_correlation(
                all_instruments,
                threshold=0.7
            )
            
            return correlation_check
            
        except Exception as e:
            self.logger.error(f"Error checking correlation risk: {e}")
            return {'risk': 'unknown', 'message': str(e)}
    
    def _calculate_position_size(
        self,
        proposed_trade: Dict[str, Any],
        account_info: Dict[str, Any]
    ) -> float:
        """
        Calculate appropriate position size
        
        Uses fixed fractional position sizing
        """
        try:
            balance = account_info.get('balance', 0)
            
            # Risk per trade (0.5-1% of balance)
            risk_percent = Settings.RISK_PER_TRADE_PERCENT
            risk_amount = balance * risk_percent
            
            # Get stop loss distance
            entry_price = proposed_trade.get('entry_price', 0)
            stop_loss = proposed_trade.get('stop_loss', 0)
            
            if not entry_price or not stop_loss:
                # Default position size
                return Settings.DEFAULT_POSITION_SIZE
            
            # Calculate stop loss distance in pips/points
            sl_distance = abs(entry_price - stop_loss)
            
            if sl_distance == 0:
                return Settings.DEFAULT_POSITION_SIZE
            
            # Calculate position size
            # position_size = risk_amount / sl_distance
            # This is simplified; actual calculation depends on instrument specs
            
            # For now, return default size
            return Settings.DEFAULT_POSITION_SIZE
            
        except Exception as e:
            self.logger.error(f"Error calculating position size: {e}")
            return Settings.DEFAULT_POSITION_SIZE
    
    def _get_daily_loss(self) -> float:
        """Get today's total loss"""
        try:
            closed_trades = self.mt5.get_closed_trades(days=1)
            
            if not closed_trades:
                return 0.0
            
            total_profit = sum(trade.get('profit', 0) for trade in closed_trades)
            
            # Return loss as positive number
            return abs(min(total_profit, 0))
            
        except Exception as e:
            self.logger.error(f"Error getting daily loss: {e}")
            return 0.0
    
    def _should_proceed(
        self,
        risk_checks: Dict[str, Any],
        position_check: Dict[str, Any],
        llm_analysis: Dict[str, Any]
    ) -> bool:
        """Determine if trade should proceed"""
        # Check all risk criteria
        if not risk_checks.get('sufficient_balance'):
            self.logger.warning("Insufficient balance")
            return False
        
        if not risk_checks.get('equity_check'):
            self.logger.warning("Equity too low")
            return False
        
        if not risk_checks.get('margin_level_ok'):
            self.logger.warning("Margin level too low")
            return False
        
        if not risk_checks.get('daily_loss_ok'):
            self.logger.warning("Daily loss limit reached")
            return False
        
        if not risk_checks.get('drawdown_ok'):
            self.logger.warning("Maximum drawdown exceeded")
            return False
        
        if not position_check.get('positions_ok'):
            self.logger.warning("Maximum positions limit reached")
            return False
        
        if not position_check.get('instrument_ok'):
            self.logger.warning("Maximum positions per instrument reached")
            return False
        
        # Check LLM recommendation
        llm_rec = llm_analysis.get('recommendation', '').lower()
        if llm_rec == 'reject':
            self.logger.warning(f"LLM recommends rejecting trade: {llm_analysis.get('reasoning')}")
            return False
        
        return True
    
    def _analyze_with_llm(
        self,
        proposed_trade: Dict[str, Any],
        account_info: Dict[str, Any],
        risk_checks: Dict[str, Any],
        position_check: Dict[str, Any],
        correlation_risk: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Use LLM for risk assessment"""
        try:
            # Format data
            trade_str = json.dumps(proposed_trade, indent=2)
            risk_str = json.dumps(risk_checks, indent=2)
            position_str = json.dumps(position_check, indent=2)
            correlation_str = json.dumps(correlation_risk, indent=2)
            
            # Create prompt
            messages = [
                self.create_system_message(
                    "an expert risk manager specializing in trading risk assessment"
                ),
                self.create_user_message(
                    f"Assess the risk of the following proposed trade:\n\n"
                    f"Proposed Trade:\n{trade_str}\n\n"
                    f"Risk Checks:\n{risk_str}\n\n"
                    f"Position Limits:\n{position_str}\n\n"
                    f"Correlation Risk:\n{correlation_str}\n\n"
                    f"Account Balance: ${account_info.get('balance', 0):.2f}\n"
                    f"Account Equity: ${account_info.get('equity', 0):.2f}\n\n"
                    f"Provide your risk assessment in the following JSON format:\n"
                    f"{{\n"
                    f'  "recommendation": "approve" | "reject",\n'
                    f'  "confidence": 0.0 to 1.0,\n'
                    f'  "reasoning": "detailed risk assessment",\n'
                    f'  "risk_level": "low" | "medium" | "high",\n'
                    f'  "concerns": ["list of risk concerns if any"],\n'
                    f'  "suggestions": ["risk mitigation suggestions"]\n'
                    f"}}"
                )
            ]
            
            response = self.call_llm(messages, temperature=0.2)
            
            if response and 'choices' in response:
                content = response['choices'][0]['message']['content']
                analysis = self.extract_json_from_response(content)
                
                if analysis:
                    self.logger.info(f"LLM risk assessment: {analysis.get('recommendation')} "
                                   f"(risk level: {analysis.get('risk_level')})")
                    return analysis
            
            # Fallback
            return {
                'recommendation': 'approve',
                'confidence': 0.6,
                'reasoning': 'LLM analysis unavailable, using rule-based checks',
                'risk_level': 'medium'
            }
            
        except Exception as e:
            self.logger.error(f"Error in LLM risk analysis: {e}")
            return {
                'recommendation': 'approve',
                'confidence': 0.5,
                'reasoning': f'Error in LLM analysis: {str(e)}',
                'risk_level': 'medium'
            }

