"""
News Collector
Collects news from multiple sources and performs sentiment analysis
"""

import requests
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from config.settings import Settings
from utils.logger import get_logger
from utils.helpers import retry_on_failure

logger = get_logger("api")


class NewsCollector:
    """Collects news and sentiment data from multiple sources"""
    
    def __init__(self):
        self.newsapi_key = Settings.NEWSAPI_KEY
        self.alpha_vantage_key = Settings.ALPHA_VANTAGE_API_KEY
        self.finnhub_key = Settings.FINNHUB_API_KEY
        self.polygon_key = Settings.POLYGON_API_KEY
    
    @retry_on_failure(max_retries=2, delay=1.0)
    def get_news_newsapi(
        self,
        query: str = "forex OR trading OR economy",
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get news from NewsAPI
        
        Args:
            query: Search query
            hours: Hours to look back
            
        Returns:
            List of news articles
        """
        try:
            from_date = (datetime.now() - timedelta(hours=hours)).isoformat()
            
            url = "https://newsapi.org/v2/everything"
            params = {
                "q": query,
                "from": from_date,
                "sortBy": "publishedAt",
                "language": "en",
                "apiKey": self.newsapi_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            articles = []
            
            if data.get('status') == 'ok' and 'articles' in data:
                for article in data['articles']:
                    articles.append({
                        'title': article.get('title'),
                        'description': article.get('description'),
                        'content': article.get('content'),
                        'url': article.get('url'),
                        'source': article.get('source', {}).get('name'),
                        'published_at': article.get('publishedAt'),
                        'api_source': 'newsapi'
                    })
            
            logger.info(f"Retrieved {len(articles)} articles from NewsAPI")
            return articles
            
        except Exception as e:
            logger.error(f"NewsAPI error: {e}")
            return []
    
    @retry_on_failure(max_retries=2, delay=1.0)
    def get_news_alpha_vantage(self, tickers: str = None) -> List[Dict[str, Any]]:
        """
        Get news from Alpha Vantage
        
        Args:
            tickers: Comma-separated list of tickers
            
        Returns:
            List of news articles
        """
        try:
            url = "https://www.alphavantage.co/query"
            params = {
                "function": "NEWS_SENTIMENT",
                "apikey": self.alpha_vantage_key
            }
            
            if tickers:
                params["tickers"] = tickers
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            articles = []
            
            if 'feed' in data:
                for item in data['feed']:
                    # Calculate average sentiment
                    sentiment_score = 0.0
                    if 'overall_sentiment_score' in item:
                        sentiment_score = float(item['overall_sentiment_score'])
                    
                    articles.append({
                        'title': item.get('title'),
                        'summary': item.get('summary'),
                        'url': item.get('url'),
                        'source': item.get('source'),
                        'published_at': item.get('time_published'),
                        'sentiment_score': sentiment_score,
                        'sentiment_label': item.get('overall_sentiment_label'),
                        'api_source': 'alpha_vantage'
                    })
            
            logger.info(f"Retrieved {len(articles)} articles from Alpha Vantage")
            return articles
            
        except Exception as e:
            logger.error(f"Alpha Vantage news error: {e}")
            return []
    
    @retry_on_failure(max_retries=2, delay=1.0)
    def get_news_finnhub(self, category: str = "forex") -> List[Dict[str, Any]]:
        """
        Get news from Finnhub
        
        Args:
            category: News category (forex, general, etc.)
            
        Returns:
            List of news articles
        """
        try:
            url = "https://finnhub.io/api/v1/news"
            params = {
                "category": category,
                "token": self.finnhub_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            articles = []
            
            for item in data:
                articles.append({
                    'title': item.get('headline'),
                    'summary': item.get('summary'),
                    'url': item.get('url'),
                    'source': item.get('source'),
                    'published_at': datetime.fromtimestamp(item.get('datetime', 0)).isoformat(),
                    'image': item.get('image'),
                    'api_source': 'finnhub'
                })
            
            logger.info(f"Retrieved {len(articles)} articles from Finnhub")
            return articles
            
        except Exception as e:
            logger.error(f"Finnhub news error: {e}")
            return []
    
    @retry_on_failure(max_retries=2, delay=1.0)
    def get_news_polygon(self, ticker: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get news from Polygon
        
        Args:
            ticker: Stock ticker (optional)
            limit: Number of articles
            
        Returns:
            List of news articles
        """
        try:
            url = "https://api.polygon.io/v2/reference/news"
            params = {
                "apiKey": self.polygon_key,
                "limit": limit
            }
            
            if ticker:
                params["ticker"] = ticker
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            articles = []
            
            if 'results' in data:
                for item in data['results']:
                    articles.append({
                        'title': item.get('title'),
                        'description': item.get('description'),
                        'url': item.get('article_url'),
                        'source': item.get('publisher', {}).get('name'),
                        'published_at': item.get('published_utc'),
                        'image': item.get('image_url'),
                        'api_source': 'polygon'
                    })
            
            logger.info(f"Retrieved {len(articles)} articles from Polygon")
            return articles
            
        except Exception as e:
            logger.error(f"Polygon news error: {e}")
            return []
    
    def get_all_news(
        self,
        hours: int = 24,
        instruments: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get news from all sources
        
        Args:
            hours: Hours to look back
            instruments: List of instruments to filter by
            
        Returns:
            Combined list of news articles
        """
        all_articles = []
        
        # NewsAPI
        try:
            articles = self.get_news_newsapi(hours=hours)
            all_articles.extend(articles)
        except Exception as e:
            logger.error(f"Error getting NewsAPI articles: {e}")
        
        # Alpha Vantage
        try:
            articles = self.get_news_alpha_vantage()
            all_articles.extend(articles)
        except Exception as e:
            logger.error(f"Error getting Alpha Vantage articles: {e}")
        
        # Finnhub
        try:
            articles = self.get_news_finnhub()
            all_articles.extend(articles)
        except Exception as e:
            logger.error(f"Error getting Finnhub articles: {e}")
        
        # Polygon
        try:
            articles = self.get_news_polygon()
            all_articles.extend(articles)
        except Exception as e:
            logger.error(f"Error getting Polygon articles: {e}")
        
        # Remove duplicates based on title
        seen_titles = set()
        unique_articles = []
        for article in all_articles:
            title = article.get('title', '')
            if title and title not in seen_titles:
                seen_titles.add(title)
                unique_articles.append(article)
        
        logger.info(f"Retrieved total of {len(unique_articles)} unique articles from all sources")
        return unique_articles
    
    def calculate_simple_sentiment(self, text: str) -> float:
        """
        Calculate simple sentiment score based on keywords
        
        Args:
            text: Text to analyze
            
        Returns:
            Sentiment score (-10 to +10)
        """
        if not text:
            return 0.0
        
        text_lower = text.lower()
        
        # Positive keywords
        positive_words = [
            'bullish', 'gain', 'rise', 'surge', 'rally', 'growth', 'profit',
            'strong', 'positive', 'optimistic', 'upgrade', 'beat', 'exceed',
            'recovery', 'boom', 'success', 'win', 'high', 'increase'
        ]
        
        # Negative keywords
        negative_words = [
            'bearish', 'loss', 'fall', 'drop', 'decline', 'crash', 'recession',
            'weak', 'negative', 'pessimistic', 'downgrade', 'miss', 'below',
            'crisis', 'risk', 'concern', 'worry', 'low', 'decrease', 'fail'
        ]
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        # Calculate score (-10 to +10)
        score = (positive_count - negative_count) * 2
        score = max(-10, min(10, score))  # Clamp to range
        
        return float(score)
    
    def analyze_news_sentiment(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze overall sentiment from news articles
        
        Args:
            articles: List of news articles
            
        Returns:
            Sentiment analysis summary
        """
        if not articles:
            return {
                'average_sentiment': 0.0,
                'positive_count': 0,
                'negative_count': 0,
                'neutral_count': 0,
                'total_articles': 0
            }
        
        sentiments = []
        positive_count = 0
        negative_count = 0
        neutral_count = 0
        
        for article in articles:
            # Use pre-calculated sentiment if available
            if 'sentiment_score' in article:
                sentiment = article['sentiment_score'] * 10  # Scale to -10 to +10
            else:
                # Calculate sentiment from text
                text = f"{article.get('title', '')} {article.get('description', '')} {article.get('summary', '')}"
                sentiment = self.calculate_simple_sentiment(text)
                article['sentiment_score'] = sentiment
            
            sentiments.append(sentiment)
            
            if sentiment > 2:
                positive_count += 1
            elif sentiment < -2:
                negative_count += 1
            else:
                neutral_count += 1
        
        average_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0.0
        
        return {
            'average_sentiment': average_sentiment,
            'positive_count': positive_count,
            'negative_count': negative_count,
            'neutral_count': neutral_count,
            'total_articles': len(articles),
            'sentiment_label': 'positive' if average_sentiment > 2 else 'negative' if average_sentiment < -2 else 'neutral'
        }

