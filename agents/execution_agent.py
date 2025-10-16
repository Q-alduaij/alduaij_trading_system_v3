"""
Execution Agent
Executes trades on MT5 platform
"""

from typing import Dict, Any
import MetaTrader5 as mt5
from agents.base_agent import BaseAgent
from data_collection.mt5_connector import MT5Connector
from config.settings import Settings


class ExecutionAgent(BaseAgent):
    """Executes trading decisions"""
    
    def __init__(self):
        super().__init__("ExecutionAgent")
        self.mt5 = MT5Connector()
    
    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a trade
        
        Args:
            data: Dictionary containing 'trade_decision' with all trade parameters
            
        Returns:
            Execution results
        """
        try:
            trade_decision = data.get('trade_decision', {})
            
            if not trade_decision:
                return self.format_analysis_result(
                    recommendation='error',
                    confidence=0.0,
                    reasoning="No trade decision provided",
                    data={}
                )
            
            # Check if paper trading mode
            if Settings.PAPER_TRADING:
                return self._execute_paper_trade(trade_decision)
            else:
                return self._execute_live_trade(trade_decision)
                
        except Exception as e:
            self.logger.error(f"Error in trade execution: {e}")
            return self.format_analysis_result(
                recommendation='error',
                confidence=0.0,
                reasoning=f"Error during trade execution: {str(e)}",
                data={}
            )
    
    def _execute_live_trade(self, trade_decision: Dict[str, Any]) -> Dict[str, Any]:
        """Execute trade on live MT5 account"""
        try:
            if not self.mt5.ensure_connection():
                return self.format_analysis_result(
                    recommendation='failed',
                    confidence=0.0,
                    reasoning="MT5 connection failed",
                    data={}
                )
            
            instrument = trade_decision.get('instrument')
            action = trade_decision.get('action', 'buy').lower()
            volume = trade_decision.get('volume', Settings.DEFAULT_POSITION_SIZE)
            stop_loss = trade_decision.get('stop_loss')
            take_profit = trade_decision.get('take_profit')
            
            # Get symbol info
            symbol_info = self.mt5.get_symbol_info(instrument)
            if not symbol_info:
                return self.format_analysis_result(
                    recommendation='failed',
                    confidence=0.0,
                    reasoning=f"Symbol {instrument} not found",
                    data={}
                )
            
            # Prepare trade request
            order_type = mt5.ORDER_TYPE_BUY if action == 'buy' else mt5.ORDER_TYPE_SELL
            price = symbol_info['ask'] if action == 'buy' else symbol_info['bid']
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": instrument,
                "volume": volume,
                "type": order_type,
                "price": price,
                "deviation": 20,
                "magic": 234000,
                "comment": "Lolo Trading Agent",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            if stop_loss:
                request["sl"] = stop_loss
            if take_profit:
                request["tp"] = take_profit
            
            # Send order
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                self.logger.error(f"Trade execution failed: {result.comment}")
                return self.format_analysis_result(
                    recommendation='failed',
                    confidence=0.0,
                    reasoning=f"Trade execution failed: {result.comment}",
                    data={'result': result._asdict() if result else {}}
                )
            
            # Trade successful
            self.logger.info(f"Trade executed successfully: {instrument} {action} {volume} lots")
            
            # Store trade in database
            self.db.insert_trade(
                instrument=instrument,
                action=action,
                volume=volume,
                entry_price=result.price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                ticket=result.order,
                status='open'
            )
            
            return self.format_analysis_result(
                recommendation='executed',
                confidence=1.0,
                reasoning=f"Trade executed successfully",
                data={
                    'ticket': result.order,
                    'instrument': instrument,
                    'action': action,
                    'volume': volume,
                    'price': result.price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error executing live trade: {e}")
            return self.format_analysis_result(
                recommendation='error',
                confidence=0.0,
                reasoning=f"Error: {str(e)}",
                data={}
            )
    
    def _execute_paper_trade(self, trade_decision: Dict[str, Any]) -> Dict[str, Any]:
        """Execute paper trade (simulation)"""
        try:
            instrument = trade_decision.get('instrument')
            action = trade_decision.get('action', 'buy').lower()
            volume = trade_decision.get('volume', Settings.DEFAULT_POSITION_SIZE)
            stop_loss = trade_decision.get('stop_loss')
            take_profit = trade_decision.get('take_profit')
            
            # Get current price
            symbol_info = self.mt5.get_symbol_info(instrument)
            if not symbol_info:
                price = 0.0
            else:
                price = symbol_info['ask'] if action == 'buy' else symbol_info['bid']
            
            # Generate paper ticket
            import random
            ticket = random.randint(100000, 999999)
            
            # Store paper trade
            self.db.insert_trade(
                instrument=instrument,
                action=action,
                volume=volume,
                entry_price=price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                ticket=ticket,
                status='open_paper'
            )
            
            self.logger.info(f"[PAPER] Trade executed: {instrument} {action} {volume} lots at {price}")
            
            return self.format_analysis_result(
                recommendation='executed_paper',
                confidence=1.0,
                reasoning=f"Paper trade executed successfully",
                data={
                    'ticket': ticket,
                    'instrument': instrument,
                    'action': action,
                    'volume': volume,
                    'price': price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'paper_trade': True
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error executing paper trade: {e}")
            return self.format_analysis_result(
                recommendation='error',
                confidence=0.0,
                reasoning=f"Error: {str(e)}",
                data={}
            )

