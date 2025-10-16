"""
Vector Store for RAG (Retrieval-Augmented Generation)
Uses ChromaDB for storing and retrieving embeddings
"""

import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
from config.settings import Settings
from utils.logger import get_logger

logger = get_logger("main")


class VectorStore:
    """ChromaDB vector store for RAG"""
    
    def __init__(self, persist_directory: str = None):
        if persist_directory is None:
            persist_directory = str(Settings.VECTOR_DB_PATH)
        
        try:
            self.client = chromadb.Client(ChromaSettings(
                persist_directory=persist_directory,
                anonymized_telemetry=False
            ))
            
            # Create collections
            self.news_collection = self._get_or_create_collection("news_articles")
            self.trades_collection = self._get_or_create_collection("trade_outcomes")
            self.patterns_collection = self._get_or_create_collection("market_patterns")
            self.reports_collection = self._get_or_create_collection("economic_reports")
            
            logger.info("Vector store initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
            raise
    
    def _get_or_create_collection(self, name: str):
        """Get or create a collection"""
        try:
            return self.client.get_or_create_collection(name=name)
        except Exception as e:
            logger.error(f"Error creating collection {name}: {e}")
            raise
    
    def add_news_article(
        self,
        article_id: str,
        title: str,
        content: str,
        sentiment: float,
        source: str,
        published_at: str,
        instruments: List[str] = None
    ):
        """
        Add news article to vector store
        
        Args:
            article_id: Unique article identifier
            title: Article title
            content: Article content
            sentiment: Sentiment score (-10 to +10)
            source: News source
            published_at: Publication timestamp
            instruments: Related trading instruments
        """
        try:
            metadata = {
                "title": title,
                "sentiment": sentiment,
                "source": source,
                "published_at": published_at,
                "instruments": json.dumps(instruments or []),
                "type": "news"
            }
            
            self.news_collection.add(
                documents=[content],
                metadatas=[metadata],
                ids=[article_id]
            )
            
            logger.debug(f"Added news article: {title}")
        except Exception as e:
            logger.error(f"Error adding news article: {e}")
    
    def add_trade_outcome(
        self,
        trade_id: str,
        instrument: str,
        action: str,
        entry_price: float,
        exit_price: float,
        pnl: float,
        reasoning: str,
        market_conditions: str,
        outcome: str
    ):
        """
        Add trade outcome to vector store
        
        Args:
            trade_id: Trade identifier
            instrument: Trading instrument
            action: Buy or sell
            entry_price: Entry price
            exit_price: Exit price
            pnl: Profit/loss
            reasoning: Trade reasoning
            market_conditions: Market conditions description
            outcome: win or loss
        """
        try:
            # Create document combining reasoning and conditions
            document = f"Trade Reasoning: {reasoning}\nMarket Conditions: {market_conditions}"
            
            metadata = {
                "trade_id": trade_id,
                "instrument": instrument,
                "action": action,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "pnl": pnl,
                "outcome": outcome,
                "timestamp": datetime.now().isoformat()
            }
            
            self.trades_collection.add(
                documents=[document],
                metadatas=[metadata],
                ids=[trade_id]
            )
            
            logger.debug(f"Added trade outcome: {trade_id}")
        except Exception as e:
            logger.error(f"Error adding trade outcome: {e}")
    
    def add_market_pattern(
        self,
        pattern_id: str,
        instrument: str,
        pattern_description: str,
        timeframe: str,
        indicators: Dict[str, Any],
        outcome: str
    ):
        """
        Add market pattern to vector store
        
        Args:
            pattern_id: Pattern identifier
            instrument: Trading instrument
            pattern_description: Description of the pattern
            timeframe: Timeframe
            indicators: Indicator values
            outcome: Pattern outcome
        """
        try:
            metadata = {
                "pattern_id": pattern_id,
                "instrument": instrument,
                "timeframe": timeframe,
                "indicators": json.dumps(indicators),
                "outcome": outcome,
                "timestamp": datetime.now().isoformat()
            }
            
            self.patterns_collection.add(
                documents=[pattern_description],
                metadatas=[metadata],
                ids=[pattern_id]
            )
            
            logger.debug(f"Added market pattern: {pattern_id}")
        except Exception as e:
            logger.error(f"Error adding market pattern: {e}")
    
    def add_economic_report(
        self,
        report_id: str,
        title: str,
        content: str,
        report_type: str,
        impact: str,
        published_at: str
    ):
        """
        Add economic report to vector store
        
        Args:
            report_id: Report identifier
            title: Report title
            content: Report content
            report_type: Type of report (GDP, employment, etc.)
            impact: Impact level (high, medium, low)
            published_at: Publication timestamp
        """
        try:
            metadata = {
                "title": title,
                "report_type": report_type,
                "impact": impact,
                "published_at": published_at
            }
            
            self.reports_collection.add(
                documents=[content],
                metadatas=[metadata],
                ids=[report_id]
            )
            
            logger.debug(f"Added economic report: {title}")
        except Exception as e:
            logger.error(f"Error adding economic report: {e}")
    
    def query_news(
        self,
        query: str,
        n_results: int = 5,
        instrument: str = None
    ) -> List[Dict[str, Any]]:
        """
        Query news articles
        
        Args:
            query: Query string
            n_results: Number of results to return
            instrument: Filter by instrument
            
        Returns:
            List of relevant news articles
        """
        try:
            where_filter = None
            if instrument:
                where_filter = {"instruments": {"$contains": instrument}}
            
            results = self.news_collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_filter
            )
            
            return self._format_results(results)
        except Exception as e:
            logger.error(f"Error querying news: {e}")
            return []
    
    def query_similar_trades(
        self,
        query: str,
        n_results: int = 5,
        instrument: str = None,
        outcome: str = None
    ) -> List[Dict[str, Any]]:
        """
        Query similar trade outcomes
        
        Args:
            query: Query string (market conditions or reasoning)
            n_results: Number of results to return
            instrument: Filter by instrument
            outcome: Filter by outcome (win/loss)
            
        Returns:
            List of similar trades
        """
        try:
            where_filter = {}
            if instrument:
                where_filter["instrument"] = instrument
            if outcome:
                where_filter["outcome"] = outcome
            
            results = self.trades_collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_filter if where_filter else None
            )
            
            return self._format_results(results)
        except Exception as e:
            logger.error(f"Error querying trades: {e}")
            return []
    
    def query_market_patterns(
        self,
        query: str,
        n_results: int = 5,
        instrument: str = None
    ) -> List[Dict[str, Any]]:
        """
        Query market patterns
        
        Args:
            query: Query string
            n_results: Number of results to return
            instrument: Filter by instrument
            
        Returns:
            List of similar market patterns
        """
        try:
            where_filter = None
            if instrument:
                where_filter = {"instrument": instrument}
            
            results = self.patterns_collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_filter
            )
            
            return self._format_results(results)
        except Exception as e:
            logger.error(f"Error querying patterns: {e}")
            return []
    
    def query_economic_reports(
        self,
        query: str,
        n_results: int = 5,
        report_type: str = None
    ) -> List[Dict[str, Any]]:
        """
        Query economic reports
        
        Args:
            query: Query string
            n_results: Number of results to return
            report_type: Filter by report type
            
        Returns:
            List of relevant economic reports
        """
        try:
            where_filter = None
            if report_type:
                where_filter = {"report_type": report_type}
            
            results = self.reports_collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_filter
            )
            
            return self._format_results(results)
        except Exception as e:
            logger.error(f"Error querying reports: {e}")
            return []
    
    def _format_results(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Format ChromaDB results"""
        formatted = []
        
        if not results or 'ids' not in results:
            return formatted
        
        for i in range(len(results['ids'][0])):
            formatted.append({
                'id': results['ids'][0][i],
                'document': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'distance': results['distances'][0][i] if 'distances' in results else None
            })
        
        return formatted
    
    def clear_collection(self, collection_name: str):
        """Clear all documents from a collection"""
        try:
            self.client.delete_collection(collection_name)
            self._get_or_create_collection(collection_name)
            logger.info(f"Cleared collection: {collection_name}")
        except Exception as e:
            logger.error(f"Error clearing collection: {e}")

