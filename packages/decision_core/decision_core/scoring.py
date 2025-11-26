"""
Scoring Module
Đánh giá phương án theo tiêu chí (evaluate options by criteria)
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class Criterion:
    """Represents a decision criterion"""
    name: str
    weight: float  # 0.0 to 1.0
    maximize: bool = True  # True = higher is better, False = lower is better
    description: Optional[str] = None


class Scoring:
    """Score and evaluate options based on multiple criteria"""
    
    def __init__(self, criteria: Optional[List[Criterion]] = None):
        """
        Initialize scoring system
        
        Args:
            criteria: List of criteria to use for scoring
        """
        self.criteria = criteria or []
        self._validate_criteria()
    
    def _validate_criteria(self):
        """Validate that criteria weights sum to approximately 1.0"""
        if not self.criteria:
            return
        
        total_weight = sum(c.weight for c in self.criteria)
        if not (0.99 <= total_weight <= 1.01):
            # Normalize weights if they don't sum to 1.0
            for criterion in self.criteria:
                criterion.weight = criterion.weight / total_weight
    
    def score_option(
        self,
        option: Dict[str, Any],
        normalize: bool = True
    ) -> Dict[str, Any]:
        """
        Score a single option against all criteria
        
        Args:
            option: Option to score (must have values for each criterion)
            normalize: Whether to normalize criterion values to 0-1 range
            
        Returns:
            Dictionary with scores and final weighted score
        """
        criterion_scores = {}
        total_score = 0.0
        
        for criterion in self.criteria:
            value = option.get(criterion.name, 0)
            
            # Normalize value if needed
            if normalize:
                value = self._normalize_value(value, criterion)
            
            # Invert if we want to minimize (lower is better)
            if not criterion.maximize:
                value = 1.0 - value
            
            # Calculate weighted score
            weighted_score = value * criterion.weight
            criterion_scores[criterion.name] = {
                "raw_value": option.get(criterion.name, 0),
                "normalized_value": value,
                "weight": criterion.weight,
                "weighted_score": weighted_score
            }
            total_score += weighted_score
        
        return {
            "option": option,
            "criterion_scores": criterion_scores,
            "total_score": total_score
        }
    
    def score_options(
        self,
        options: List[Dict[str, Any]],
        normalize: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Score multiple options and rank them
        
        Args:
            options: List of options to score
            normalize: Whether to normalize criterion values
            
        Returns:
            List of scored options, sorted by total score (descending)
        """
        scored_options = []
        
        for option in options:
            scored = self.score_option(option, normalize=normalize)
            scored_options.append(scored)
        
        # Sort by total score (descending)
        scored_options.sort(key=lambda x: x["total_score"], reverse=True)
        
        # Add rank
        for i, scored in enumerate(scored_options):
            scored["rank"] = i + 1
        
        return scored_options
    
    def _normalize_value(self, value: float, criterion: Criterion) -> float:
        """Normalize a value to 0-1 range"""
        # TODO: Implement proper normalization based on criterion
        # This is a simple placeholder
        if value < 0:
            return 0.0
        if value > 1:
            return min(value / 100.0, 1.0)
        return value
    
    def add_criterion(self, criterion: Criterion):
        """Add a new criterion to the scoring system"""
        self.criteria.append(criterion)
        self._validate_criteria()
    
    def remove_criterion(self, name: str):
        """Remove a criterion by name"""
        self.criteria = [c for c in self.criteria if c.name != name]
        self._validate_criteria()

