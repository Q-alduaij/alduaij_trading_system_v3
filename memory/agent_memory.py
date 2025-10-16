"""
Agent Memory Management
Manages memory for individual agents
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import json
from memory.database import Database
from utils.logger import get_logger

logger = get_logger("agents")


class AgentMemory:
    """Memory manager for AI agents"""
    
    def __init__(self, agent_name: str, db: Database = None):
        self.agent_name = agent_name
        self.db = db or Database()
        self.short_term_memory: List[Dict[str, Any]] = []
        self.max_short_term_items = 50
    
    def store_short_term(self, memory_type: str, content: Any):
        """
        Store information in short-term memory (in-memory only)
        
        Args:
            memory_type: Type of memory (observation, decision, etc.)
            content: Content to store
        """
        memory_item = {
            'type': memory_type,
            'content': content,
            'timestamp': datetime.now().isoformat()
        }
        
        self.short_term_memory.append(memory_item)
        
        # Limit short-term memory size
        if len(self.short_term_memory) > self.max_short_term_items:
            self.short_term_memory = self.short_term_memory[-self.max_short_term_items:]
    
    def store_long_term(self, memory_type: str, content: Any, metadata: Dict[str, Any] = None):
        """
        Store information in long-term memory (database)
        
        Args:
            memory_type: Type of memory
            content: Content to store
            metadata: Additional metadata
        """
        content_str = json.dumps(content) if not isinstance(content, str) else content
        metadata_str = json.dumps(metadata) if metadata else None
        
        self.db.insert_agent_memory(
            agent_name=self.agent_name,
            memory_type=memory_type,
            content=content_str,
            metadata=metadata_str
        )
        
        logger.debug(f"[{self.agent_name}] Stored long-term memory: {memory_type}")
    
    def recall_short_term(self, memory_type: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Recall from short-term memory
        
        Args:
            memory_type: Filter by memory type
            limit: Maximum number of items to return
            
        Returns:
            List of memory items
        """
        memories = self.short_term_memory
        
        if memory_type:
            memories = [m for m in memories if m['type'] == memory_type]
        
        return memories[-limit:]
    
    def recall_long_term(self, memory_type: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Recall from long-term memory (database)
        
        Args:
            memory_type: Filter by memory type
            limit: Maximum number of items to return
            
        Returns:
            List of memory items
        """
        memories = self.db.get_agent_memory(
            agent_name=self.agent_name,
            memory_type=memory_type,
            limit=limit
        )
        
        # Parse JSON content
        for memory in memories:
            try:
                memory['content'] = json.loads(memory['content'])
            except (json.JSONDecodeError, TypeError):
                pass  # Keep as string if not valid JSON
            
            if memory.get('metadata'):
                try:
                    memory['metadata'] = json.loads(memory['metadata'])
                except (json.JSONDecodeError, TypeError):
                    pass
        
        return memories
    
    def store_decision(self, decision: Dict[str, Any]):
        """Store a decision made by the agent"""
        self.store_short_term('decision', decision)
        self.store_long_term('decision', decision)
    
    def store_observation(self, observation: Dict[str, Any]):
        """Store an observation"""
        self.store_short_term('observation', observation)
    
    def store_insight(self, insight: str, metadata: Dict[str, Any] = None):
        """Store an insight or learning"""
        self.store_long_term('insight', insight, metadata)
        logger.info(f"[{self.agent_name}] New insight: {insight}")
    
    def get_recent_decisions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent decisions"""
        return self.recall_long_term('decision', limit)
    
    def get_insights(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get stored insights"""
        return self.recall_long_term('insight', limit)
    
    def clear_short_term(self):
        """Clear short-term memory"""
        self.short_term_memory = []
        logger.debug(f"[{self.agent_name}] Cleared short-term memory")
    
    def get_memory_summary(self) -> Dict[str, Any]:
        """Get summary of agent's memory"""
        return {
            'agent_name': self.agent_name,
            'short_term_items': len(self.short_term_memory),
            'recent_decisions': len(self.get_recent_decisions(10)),
            'total_insights': len(self.get_insights(1000))
        }

