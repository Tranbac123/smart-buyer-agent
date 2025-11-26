"""
Ranking Module
BM25/embedding score + business score (price, rating, etc.)
"""

from typing import List, Dict, Any, Optional
import math


class Ranking:
    """Rank search results using multiple scoring methods"""
    
    def __init__(
        self,
        text_weight: float = 0.4,
        business_weight: float = 0.6,
        k1: float = 1.5,
        b: float = 0.75
    ):
        """
        Initialize ranking system
        
        Args:
            text_weight: Weight for text-based scores (BM25/embeddings)
            business_weight: Weight for business scores (price, rating, etc.)
            k1: BM25 parameter k1
            b: BM25 parameter b
        """
        self.text_weight = text_weight
        self.business_weight = business_weight
        self.k1 = k1
        self.b = b
        
    def rank_results(
        self,
        results: List[Dict[str, Any]],
        query: str,
        use_bm25: bool = True,
        use_embeddings: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Rank search results
        
        Args:
            results: List of search results to rank
            query: User query
            use_bm25: Whether to use BM25 scoring
            use_embeddings: Whether to use embedding-based scoring
            
        Returns:
            Ranked list of results
        """
        scored_results = []
        
        for result in results:
            text_score = 0.0
            
            if use_bm25:
                text_score += self._calculate_bm25_score(query, result)
            
            if use_embeddings:
                text_score += self._calculate_embedding_score(query, result)
            
            business_score = self._calculate_business_score(result)
            
            final_score = (
                self.text_weight * text_score +
                self.business_weight * business_score
            )
            
            result["scores"] = {
                "text_score": text_score,
                "business_score": business_score,
                "final_score": final_score
            }
            scored_results.append(result)
        
        # Sort by final score (descending)
        scored_results.sort(key=lambda x: x["scores"]["final_score"], reverse=True)
        
        return scored_results
    
    def _calculate_bm25_score(self, query: str, document: Dict[str, Any]) -> float:
        """Calculate BM25 score for a document"""
        # TODO: Implement proper BM25 scoring
        # This is a placeholder implementation
        doc_text = str(document.get("title", "")) + " " + str(document.get("description", ""))
        query_terms = query.lower().split()
        
        score = 0.0
        for term in query_terms:
            if term in doc_text.lower():
                score += 1.0
        
        return score
    
    def _calculate_embedding_score(self, query: str, document: Dict[str, Any]) -> float:
        """Calculate embedding similarity score"""
        # TODO: Implement embedding-based scoring
        # Placeholder: return 0 for now
        return 0.0
    
    def _calculate_business_score(self, document: Dict[str, Any]) -> float:
        """Calculate business score based on price, rating, reviews, etc."""
        score = 0.0
        
        # Rating score (0-5 stars normalized to 0-1)
        rating = document.get("rating", 0)
        score += (rating / 5.0) * 0.4
        
        # Review count score (more reviews = better, with diminishing returns)
        review_count = document.get("review_count", 0)
        review_score = min(math.log10(review_count + 1) / 4, 1.0)
        score += review_score * 0.3
        
        # Price score (inverse - lower price = better, normalized)
        price = document.get("price", 0)
        if price > 0:
            # Assuming reasonable price range, adjust based on category
            max_price = document.get("max_price_in_category", price * 2)
            price_score = 1.0 - (price / max_price)
            score += price_score * 0.3
        
        return score

