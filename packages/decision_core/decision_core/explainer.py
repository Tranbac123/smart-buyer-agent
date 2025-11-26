"""
Explainer Module
Sinh reasoning: pros/cons, trade-offs (generate reasoning: pros/cons, trade-offs)
"""

from typing import List, Dict, Any, Optional


class Explainer:
    """Generate explanations for decisions and comparisons"""
    
    def __init__(self, llm_client: Optional[Any] = None):
        """
        Initialize explainer
        
        Args:
            llm_client: Optional LLM client for generating explanations
        """
        self.llm_client = llm_client
    
    def explain_option(
        self,
        option: Dict[str, Any],
        scored_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate pros and cons for a single option
        
        Args:
            option: The option to explain
            scored_data: Optional scoring data from Scoring module
            
        Returns:
            Dictionary with pros, cons, and summary
        """
        pros = self._identify_pros(option, scored_data)
        cons = self._identify_cons(option, scored_data)
        summary = self._generate_summary(option, pros, cons)
        
        return {
            "option": option,
            "pros": pros,
            "cons": cons,
            "summary": summary
        }
    
    def compare_options(
        self,
        options: List[Dict[str, Any]],
        scored_data: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Compare multiple options and explain trade-offs
        
        Args:
            options: List of options to compare
            scored_data: Optional list of scoring data
            
        Returns:
            Dictionary with comparison analysis and trade-offs
        """
        if not options:
            return {"error": "No options to compare"}
        
        if len(options) == 1:
            return self.explain_option(options[0], scored_data[0] if scored_data else None)
        
        # Identify best option for each criterion
        best_by_criterion = self._identify_best_by_criterion(options, scored_data)
        
        # Identify trade-offs
        tradeoffs = self._identify_tradeoffs(options, scored_data)
        
        # Generate recommendation
        recommendation = self._generate_recommendation(options, scored_data, tradeoffs)
        
        return {
            "options_count": len(options),
            "best_by_criterion": best_by_criterion,
            "tradeoffs": tradeoffs,
            "recommendation": recommendation
        }
    
    def _identify_pros(
        self,
        option: Dict[str, Any],
        scored_data: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Identify positive aspects of an option"""
        pros = []
        
        if scored_data and "criterion_scores" in scored_data:
            for criterion_name, score_data in scored_data["criterion_scores"].items():
                if score_data["normalized_value"] >= 0.7:
                    pros.append(f"Strong {criterion_name}: {score_data['raw_value']}")
        
        # Add generic pros based on option properties
        # TODO: Enhance with LLM-based analysis
        
        return pros
    
    def _identify_cons(
        self,
        option: Dict[str, Any],
        scored_data: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Identify negative aspects of an option"""
        cons = []
        
        if scored_data and "criterion_scores" in scored_data:
            for criterion_name, score_data in scored_data["criterion_scores"].items():
                if score_data["normalized_value"] <= 0.3:
                    cons.append(f"Weak {criterion_name}: {score_data['raw_value']}")
        
        # Add generic cons based on option properties
        # TODO: Enhance with LLM-based analysis
        
        return cons
    
    def _generate_summary(
        self,
        option: Dict[str, Any],
        pros: List[str],
        cons: List[str]
    ) -> str:
        """Generate a summary of the option"""
        # TODO: Use LLM to generate natural language summary
        summary = f"Option has {len(pros)} strengths and {len(cons)} weaknesses."
        return summary
    
    def _identify_best_by_criterion(
        self,
        options: List[Dict[str, Any]],
        scored_data: Optional[List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Identify which option is best for each criterion"""
        best_by_criterion = {}
        
        if scored_data and len(scored_data) > 0:
            criteria = scored_data[0].get("criterion_scores", {}).keys()
            
            for criterion in criteria:
                best_option = None
                best_value = float('-inf')
                
                for i, scored in enumerate(scored_data):
                    value = scored["criterion_scores"][criterion]["normalized_value"]
                    if value > best_value:
                        best_value = value
                        best_option = i
                
                if best_option is not None:
                    best_by_criterion[criterion] = {
                        "option_index": best_option,
                        "option": options[best_option],
                        "value": best_value
                    }
        
        return best_by_criterion
    
    def _identify_tradeoffs(
        self,
        options: List[Dict[str, Any]],
        scored_data: Optional[List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """Identify trade-offs between options"""
        tradeoffs = []
        
        # TODO: Implement sophisticated trade-off analysis
        # For example: "Option A has better price but worse quality than Option B"
        
        if scored_data and len(scored_data) >= 2:
            # Simple example: compare top 2 options
            top1 = scored_data[0]
            top2 = scored_data[1]
            
            for criterion in top1.get("criterion_scores", {}).keys():
                score1 = top1["criterion_scores"][criterion]["normalized_value"]
                score2 = top2["criterion_scores"][criterion]["normalized_value"]
                
                if abs(score1 - score2) > 0.2:  # Significant difference
                    better = "Option 1" if score1 > score2 else "Option 2"
                    tradeoffs.append({
                        "criterion": criterion,
                        "better_option": better,
                        "difference": abs(score1 - score2)
                    })
        
        return tradeoffs
    
    def _generate_recommendation(
        self,
        options: List[Dict[str, Any]],
        scored_data: Optional[List[Dict[str, Any]]],
        tradeoffs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate a recommendation based on analysis"""
        # TODO: Use LLM to generate natural language recommendation
        
        if scored_data:
            best_option_idx = 0
            best_score = scored_data[0]["total_score"]
            
            recommendation_text = (
                f"Based on the analysis, Option {best_option_idx + 1} "
                f"has the highest overall score ({best_score:.2f}). "
            )
            
            if tradeoffs:
                recommendation_text += f"However, consider {len(tradeoffs)} trade-offs before deciding."
            
            return {
                "recommended_option_index": best_option_idx,
                "recommended_option": options[best_option_idx],
                "confidence": "medium",  # TODO: Calculate confidence
                "explanation": recommendation_text
            }
        
        return {
            "recommended_option_index": 0,
            "recommended_option": options[0],
            "confidence": "low",
            "explanation": "Insufficient data for detailed recommendation"
        }

