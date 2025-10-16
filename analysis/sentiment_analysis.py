"""
Sentiment Analysis
Analyzes market sentiment from news and social data
"""

from typing import Dict, Any, List
from datetime import datetime
from utils.logger import get_logger
from data_collection.news_collector import NewsCollector

logger = get_logger("main")


class SentimentAnalyzer:
    """Analyzes market sentiment"""
    
    def __init__(self):
        self.news_collector = NewsCollector()
    
    def analyze_news_sentiment(
        self,
        instrument: str = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Analyze news sentiment
        
        Args:
            instrument: Trading instrument to filter news
            hours: Hours to look back
            
        Returns:
            Sentiment analysis
        """
        try:
            # Collect news
            articles = self.news_collector.get_all_news(hours=hours)
            
            if not articles:
                logger.warning("No news articles found for sentiment analysis")
                return self._get_neutral_sentiment()
            
            # Filter by instrument if specified
            if instrument:
                filtered_articles = self._filter_articles_by_instrument(articles, instrument)
                if filtered_articles:
                    articles = filtered_articles
            
            # Analyze sentiment
            sentiment_summary = self.news_collector.analyze_news_sentiment(articles)
            
            # Add additional context
            sentiment_summary['instrument'] = instrument
            sentiment_summary['hours_analyzed'] = hours
            sentiment_summary['timestamp'] = datetime.now().isoformat()
            
            # Determine trading signal
            avg_sentiment = sentiment_summary.get('average_sentiment', 0.0)
            if avg_sentiment > 3:
                sentiment_summary['signal'] = 'bullish'
                sentiment_summary['confidence'] = min(avg_sentiment / 10.0, 1.0)
            elif avg_sentiment < -3:
                sentiment_summary['signal'] = 'bearish'
                sentiment_summary['confidence'] = min(abs(avg_sentiment) / 10.0, 1.0)
            else:
                sentiment_summary['signal'] = 'neutral'
                sentiment_summary['confidence'] = 0.5
            
            logger.info(f"Sentiment analysis for {instrument}: {sentiment_summary['signal']} "
                       f"(score: {avg_sentiment:.2f})")
            
            return sentiment_summary
            
        except Exception as e:
            logger.error(f"Error analyzing news sentiment: {e}")
            return self._get_neutral_sentiment()
    
    def _filter_articles_by_instrument(
        self,
        articles: List[Dict[str, Any]],
        instrument: str
    ) -> List[Dict[str, Any]]:
        """Filter articles relevant to instrument"""
        try:
            # Extract currency codes or keywords from instrument
            keywords = self._get_instrument_keywords(instrument)
            
            filtered = []
            for article in articles:
                title = article.get('title', '').lower()
                description = article.get('description', '').lower()
                summary = article.get('summary', '').lower()
                
                text = f"{title} {description} {summary}"
                
                # Check if any keyword is in the text
                if any(keyword.lower() in text for keyword in keywords):
                    filtered.append(article)
            
            logger.debug(f"Filtered {len(filtered)} articles for {instrument} from {len(articles)} total")
            return filtered
            
        except Exception as e:
            logger.debug(f"Error filtering articles: {e}")
            return articles
    
    def _get_instrument_keywords(self, instrument: str) -> List[str]:
        """Get relevant keywords for instrument"""
        keywords = [instrument]
        
        # Forex pairs
        if len(instrument) == 6 and instrument.isalpha():
            currency1 = instrument[:3]
            currency2 = instrument[3:]
            
            currency_names = {
                'USD': ['dollar', 'usd', 'us dollar'],
                'EUR': ['euro', 'eur', 'european'],
                'GBP': ['pound', 'gbp', 'sterling', 'british'],
                'JPY': ['yen', 'jpy', 'japanese'],
                'AUD': ['aussie', 'aud', 'australian dollar'],
                'CAD': ['cad', 'canadian dollar', 'loonie'],
                'NZD': ['nzd', 'new zealand dollar', 'kiwi'],
                'CHF': ['franc', 'chf', 'swiss'],
            }
            
            keywords.extend(currency_names.get(currency1, [currency1]))
            keywords.extend(currency_names.get(currency2, [currency2]))
        
        # Metals
        elif 'XAU' in instrument:
            keywords.extend(['gold', 'xau', 'precious metals'])
        elif 'XAG' in instrument:
            keywords.extend(['silver', 'xag', 'precious metals'])
        
        # Crypto
        elif 'BTC' in instrument:
            keywords.extend(['bitcoin', 'btc', 'crypto'])
        elif 'ETH' in instrument:
            keywords.extend(['ethereum', 'eth', 'crypto'])
        
        return keywords
    
    def _get_neutral_sentiment(self) -> Dict[str, Any]:
        """Return neutral sentiment"""
        return {
            'average_sentiment': 0.0,
            'positive_count': 0,
            'negative_count': 0,
            'neutral_count': 0,
            'total_articles': 0,
            'sentiment_label': 'neutral',
            'signal': 'neutral',
            'confidence': 0.0,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_market_mood(self) -> Dict[str, Any]:
        """
        Get overall market mood/sentiment
        
        Returns:
            Market mood analysis
        """
        try:
            # Get general market news
            articles = self.news_collector.get_all_news(hours=24)
            
            if not articles:
                return {
                    'mood': 'neutral',
                    'confidence': 0.0,
                    'description': 'No data available'
                }
            
            # Analyze sentiment
            sentiment_summary = self.news_collector.analyze_news_sentiment(articles)
            
            avg_sentiment = sentiment_summary.get('average_sentiment', 0.0)
            
            # Determine mood
            if avg_sentiment > 5:
                mood = 'very_bullish'
                description = 'Market sentiment is very positive'
            elif avg_sentiment > 2:
                mood = 'bullish'
                description = 'Market sentiment is positive'
            elif avg_sentiment < -5:
                mood = 'very_bearish'
                description = 'Market sentiment is very negative'
            elif avg_sentiment < -2:
                mood = 'bearish'
                description = 'Market sentiment is negative'
            else:
                mood = 'neutral'
                description = 'Market sentiment is neutral'
            
            return {
                'mood': mood,
                'sentiment_score': avg_sentiment,
                'confidence': min(abs(avg_sentiment) / 10.0, 1.0),
                'description': description,
                'articles_analyzed': sentiment_summary.get('total_articles', 0),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting market mood: {e}")
            return {
                'mood': 'neutral',
                'confidence': 0.0,
                'description': 'Error analyzing market mood'
            }
    
    def get_sentiment_summary(self, instrument: str) -> Dict[str, Any]:
        """
        Get comprehensive sentiment summary for instrument
        
        Args:
            instrument: Trading instrument
            
        Returns:
            Sentiment summary
        """
        try:
            # News sentiment
            news_sentiment = self.analyze_news_sentiment(instrument, hours=24)
            
            # Market mood
            market_mood = self.get_market_mood()
            
            # Combined analysis
            combined_score = (news_sentiment.get('average_sentiment', 0.0) + 
                            market_mood.get('sentiment_score', 0.0)) / 2
            
            if combined_score > 3:
                overall_signal = 'bullish'
            elif combined_score < -3:
                overall_signal = 'bearish'
            else:
                overall_signal = 'neutral'
            
            return {
                'instrument': instrument,
                'news_sentiment': news_sentiment,
                'market_mood': market_mood,
                'combined_score': combined_score,
                'overall_signal': overall_signal,
                'confidence': min(abs(combined_score) / 10.0, 1.0),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting sentiment summary for {instrument}: {e}")
            return {
                'instrument': instrument,
                'overall_signal': 'neutral',
                'confidence': 0.0
            }

