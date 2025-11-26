"""
Query Understanding Module
Parse/normalize query, detect intent: compare, filter, etc.
"""

from typing import Dict, List, Optional, Any
from enum import Enum


class QueryIntent(Enum):
    """Types of query intents"""
    SEARCH = "search"
    COMPARE = "compare"
    FILTER = "filter"
    RECOMMEND = "recommend"
    UNKNOWN = "unknown"


class QueryUnderstanding:
    """Parse and understand user queries"""
    
    def __init__(self):
        self.intent_keywords = {
            QueryIntent.COMPARE: ["so sánh", "compare", "khác nhau", "difference", "vs"],
            QueryIntent.FILTER: ["lọc", "filter", "từ", "đến", "trong khoảng", "range"],
            QueryIntent.RECOMMEND: ["gợi ý", "recommend", "nên", "should", "tốt nhất", "best"],
        }
    
    def parse_query(self, query: str) -> Dict[str, Any]:
        """
        Parse and normalize user query
        
        Args:
            query: Raw user query string
            
        Returns:
            Dict containing parsed query information:
            - normalized_query: Cleaned query string
            - intent: Detected query intent
            - entities: Extracted entities (price, brand, etc.)
            - filters: Extracted filters
        """
        normalized = self._normalize_query(query)
        intent = self._detect_intent(normalized)
        entities = self._extract_entities(normalized)
        filters = self._extract_filters(normalized)
        
        return {
            "original_query": query,
            "normalized_query": normalized,
            "intent": intent,
            "entities": entities,
            "filters": filters
        }
    
    def _normalize_query(self, query: str) -> str:
        """Clean and normalize query string"""
        # TODO: Implement normalization (lowercase, remove special chars, etc.)
        return query.strip().lower()
    
    def _detect_intent(self, query: str) -> QueryIntent:
        """Detect the intent of the query"""
        for intent, keywords in self.intent_keywords.items():
            if any(keyword in query for keyword in keywords):
                return intent
        return QueryIntent.SEARCH
    
    def _extract_entities(self, query: str) -> Dict[str, Any]:
        """Extract named entities from query"""
        # TODO: Implement entity extraction (brands, products, etc.)
        return {}
    
    def _extract_filters(self, query: str) -> Dict[str, Any]:
        """Extract filters from query (price range, ratings, etc.)"""
        # TODO: Implement filter extraction
        return {}

