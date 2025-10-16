"""
Correlation Analysis
Analyzes correlations between trading instruments
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple
from utils.logger import get_logger

logger = get_logger("main")


class CorrelationAnalyzer:
    """Analyzes correlations between instruments"""
    
    def __init__(self):
        self.correlation_matrix = None
        self.last_update = None
    
    def calculate_correlation(
        self,
        data1: pd.DataFrame,
        data2: pd.DataFrame
    ) -> float:
        """
        Calculate correlation between two price series
        
        Args:
            data1: First price dataframe
            data2: Second price dataframe
            
        Returns:
            Correlation coefficient (-1 to 1)
        """
        try:
            # Align dataframes by index
            df1 = data1[['close']].copy()
            df2 = data2[['close']].copy()
            
            # Merge on index
            merged = pd.merge(df1, df2, left_index=True, right_index=True, how='inner')
            
            if len(merged) < 30:
                logger.warning("Insufficient data for correlation calculation")
                return 0.0
            
            # Calculate correlation
            correlation = merged.iloc[:, 0].corr(merged.iloc[:, 1])
            
            return float(correlation)
            
        except Exception as e:
            logger.error(f"Error calculating correlation: {e}")
            return 0.0
    
    def build_correlation_matrix(
        self,
        instruments_data: Dict[str, pd.DataFrame]
    ) -> pd.DataFrame:
        """
        Build correlation matrix for multiple instruments
        
        Args:
            instruments_data: Dictionary of {instrument: price_dataframe}
            
        Returns:
            Correlation matrix as DataFrame
        """
        try:
            instruments = list(instruments_data.keys())
            n = len(instruments)
            
            # Initialize matrix
            matrix = np.zeros((n, n))
            
            # Calculate correlations
            for i in range(n):
                for j in range(n):
                    if i == j:
                        matrix[i][j] = 1.0
                    elif i < j:
                        corr = self.calculate_correlation(
                            instruments_data[instruments[i]],
                            instruments_data[instruments[j]]
                        )
                        matrix[i][j] = corr
                        matrix[j][i] = corr  # Symmetric
            
            # Create DataFrame
            self.correlation_matrix = pd.DataFrame(
                matrix,
                index=instruments,
                columns=instruments
            )
            
            logger.info(f"Built correlation matrix for {n} instruments")
            return self.correlation_matrix
            
        except Exception as e:
            logger.error(f"Error building correlation matrix: {e}")
            return pd.DataFrame()
    
    def get_correlated_pairs(
        self,
        threshold: float = 0.7,
        instruments_data: Dict[str, pd.DataFrame] = None
    ) -> List[Tuple[str, str, float]]:
        """
        Get pairs of instruments with high correlation
        
        Args:
            threshold: Correlation threshold (0.7 = 70%)
            instruments_data: Optional data to rebuild matrix
            
        Returns:
            List of (instrument1, instrument2, correlation) tuples
        """
        try:
            # Build matrix if needed
            if instruments_data:
                self.build_correlation_matrix(instruments_data)
            
            if self.correlation_matrix is None or self.correlation_matrix.empty:
                logger.warning("No correlation matrix available")
                return []
            
            correlated_pairs = []
            instruments = list(self.correlation_matrix.index)
            
            for i in range(len(instruments)):
                for j in range(i + 1, len(instruments)):
                    corr = self.correlation_matrix.iloc[i, j]
                    
                    # Check if correlation exceeds threshold (positive or negative)
                    if abs(corr) >= threshold:
                        correlated_pairs.append((
                            instruments[i],
                            instruments[j],
                            float(corr)
                        ))
            
            # Sort by absolute correlation
            correlated_pairs.sort(key=lambda x: abs(x[2]), reverse=True)
            
            logger.info(f"Found {len(correlated_pairs)} correlated pairs above threshold {threshold}")
            return correlated_pairs
            
        except Exception as e:
            logger.error(f"Error getting correlated pairs: {e}")
            return []
    
    def check_portfolio_correlation(
        self,
        open_positions: List[str],
        threshold: float = 0.7
    ) -> Dict[str, Any]:
        """
        Check correlation in current portfolio
        
        Args:
            open_positions: List of instruments with open positions
            threshold: Correlation threshold for warning
            
        Returns:
            Correlation analysis of portfolio
        """
        try:
            if not open_positions or len(open_positions) < 2:
                return {
                    'warning': False,
                    'message': 'Insufficient positions for correlation analysis',
                    'correlated_pairs': []
                }
            
            if self.correlation_matrix is None:
                return {
                    'warning': False,
                    'message': 'Correlation matrix not available',
                    'correlated_pairs': []
                }
            
            # Check correlations between open positions
            correlated_pairs = []
            
            for i in range(len(open_positions)):
                for j in range(i + 1, len(open_positions)):
                    inst1 = open_positions[i]
                    inst2 = open_positions[j]
                    
                    # Get correlation from matrix
                    try:
                        corr = self.correlation_matrix.loc[inst1, inst2]
                        
                        if abs(corr) >= threshold:
                            correlated_pairs.append({
                                'instrument1': inst1,
                                'instrument2': inst2,
                                'correlation': float(corr),
                                'type': 'positive' if corr > 0 else 'negative'
                            })
                    except KeyError:
                        logger.debug(f"Correlation not available for {inst1}/{inst2}")
                        continue
            
            # Determine if warning is needed
            warning = len(correlated_pairs) > 0
            
            if warning:
                message = f"Warning: {len(correlated_pairs)} correlated pairs in portfolio"
            else:
                message = "Portfolio correlation is acceptable"
            
            return {
                'warning': warning,
                'message': message,
                'correlated_pairs': correlated_pairs,
                'total_positions': len(open_positions)
            }
            
        except Exception as e:
            logger.error(f"Error checking portfolio correlation: {e}")
            return {
                'warning': False,
                'message': 'Error analyzing portfolio correlation',
                'correlated_pairs': []
            }
    
    def suggest_hedging_opportunities(
        self,
        open_positions: List[Dict[str, Any]],
        instruments_data: Dict[str, pd.DataFrame]
    ) -> List[Dict[str, Any]]:
        """
        Suggest hedging opportunities based on correlations
        
        Args:
            open_positions: List of open position dictionaries
            instruments_data: Price data for instruments
            
        Returns:
            List of hedging suggestions
        """
        try:
            if not open_positions:
                return []
            
            # Build/update correlation matrix
            if instruments_data:
                self.build_correlation_matrix(instruments_data)
            
            if self.correlation_matrix is None:
                return []
            
            suggestions = []
            
            for position in open_positions:
                instrument = position.get('symbol')
                direction = position.get('type', 'buy')
                
                if not instrument:
                    continue
                
                # Find negatively correlated instruments
                try:
                    correlations = self.correlation_matrix[instrument]
                    
                    # Find instruments with strong negative correlation
                    for other_inst, corr in correlations.items():
                        if other_inst == instrument:
                            continue
                        
                        # Strong negative correlation
                        if corr < -0.6:
                            # Check if we already have a position in this instrument
                            has_position = any(p.get('symbol') == other_inst for p in open_positions)
                            
                            if not has_position:
                                suggestions.append({
                                    'original_position': instrument,
                                    'original_direction': direction,
                                    'hedge_instrument': other_inst,
                                    'hedge_direction': direction,  # Same direction due to negative correlation
                                    'correlation': float(corr),
                                    'reason': f"Hedge {instrument} with {other_inst} (correlation: {corr:.2f})"
                                })
                
                except KeyError:
                    logger.debug(f"Correlation data not available for {instrument}")
                    continue
            
            logger.info(f"Generated {len(suggestions)} hedging suggestions")
            return suggestions
            
        except Exception as e:
            logger.error(f"Error suggesting hedging opportunities: {e}")
            return []
    
    def get_correlation_summary(self) -> Dict[str, Any]:
        """
        Get summary of correlation analysis
        
        Returns:
            Correlation summary
        """
        try:
            if self.correlation_matrix is None or self.correlation_matrix.empty:
                return {
                    'available': False,
                    'message': 'Correlation matrix not available'
                }
            
            # Get highly correlated pairs
            high_corr_pairs = self.get_correlated_pairs(threshold=0.7)
            
            # Get negatively correlated pairs
            neg_corr_pairs = [(i1, i2, c) for i1, i2, c in self.get_correlated_pairs(threshold=0.0) if c < -0.6]
            
            return {
                'available': True,
                'instruments_analyzed': len(self.correlation_matrix),
                'high_correlation_pairs': len(high_corr_pairs),
                'negative_correlation_pairs': len(neg_corr_pairs),
                'top_correlated': high_corr_pairs[:5] if high_corr_pairs else [],
                'top_negatively_correlated': neg_corr_pairs[:5] if neg_corr_pairs else []
            }
            
        except Exception as e:
            logger.error(f"Error getting correlation summary: {e}")
            return {
                'available': False,
                'message': 'Error generating correlation summary'
            }

