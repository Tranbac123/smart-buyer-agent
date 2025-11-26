"""
Smart Buyer Orchestrator
Orchestrates the Smart Buyer flow using:
- agent_core (planner, executor, observer, reflector, refiner)
- search_core (query understanding, price comparison, ranking)
- decision_core (scoring, explainer)
- tools (price_compare_tool)
"""

from typing import Dict, Any, Optional, List
from .base_orchestrator import BaseOrchestrator


class SmartBuyerOrchestrator(BaseOrchestrator):
    """
    Orchestrates Smart Buyer flow
    
    Pipeline:
    1. Plan: Understand user intent (compare A vs B? or find best?)
    2. Act: Search products using price_compare_tool
    3. Observe: Analyze search results
    4. Score: Rank by relevance (not just price)
    5. Explain: Generate pros/cons, warnings, suggestions
    6. Refine: Iterate if needed
    """
    
    def __init__(
        self,
        llm_client: Any,
        memory_service: Any,
        tools_registry: Any
    ):
        """
        Initialize Smart Buyer Orchestrator
        
        Args:
            llm_client: LLM client
            memory_service: Memory service
            tools_registry: Tools registry
        """
        super().__init__(llm_client, memory_service, tools_registry)
        
        # Initialize search_core components
        self._init_search_components()
        
        # Initialize decision_core components
        self._init_decision_components()
        
        # Initialize agent_core components
        self._init_agent_components()
    
    def _init_search_components(self):
        """Initialize search_core components"""
        try:
            from packages.search_core.search_core.query_understanding import QueryUnderstanding
            from packages.search_core.search_core.ranking import Ranking
            from packages.search_core.search_core.ecommerce.price_compare import PriceCompare
            
            self.query_understanding = QueryUnderstanding()
            self.ranking = Ranking(
                text_weight=0.3,  # Less weight on text matching
                business_weight=0.7  # More weight on business metrics
            )
            self.price_compare = PriceCompare()
        except ImportError as e:
            print(f"Warning: Could not import search_core: {e}")
            self.query_understanding = None
            self.ranking = None
            self.price_compare = None
    
    def _init_decision_components(self):
        """Initialize decision_core components"""
        try:
            from packages.decision_core.decision_core.scoring import Scoring, Criterion
            from packages.decision_core.decision_core.explainer import Explainer
            
            # Define criteria for product evaluation
            criteria = [
                Criterion(
                    name="price",
                    weight=0.25,
                    maximize=False,
                    description="Lower price is better"
                ),
                Criterion(
                    name="rating",
                    weight=0.30,
                    maximize=True,
                    description="Higher rating indicates quality"
                ),
                Criterion(
                    name="review_count",
                    weight=0.25,
                    maximize=True,
                    description="More reviews indicate reliability"
                ),
                Criterion(
                    name="sold",
                    weight=0.20,
                    maximize=True,
                    description="More sales indicate popularity"
                ),
            ]
            
            self.scoring = Scoring(criteria)
            self.explainer = Explainer(self.llm_client)
        except ImportError as e:
            print(f"Warning: Could not import decision_core: {e}")
            self.scoring = None
            self.explainer = None
    
    def _init_agent_components(self):
        """Initialize agent_core components"""
        # TODO: Import agent_core components when available
        # from packages.agent_core.planner import Planner
        # from packages.agent_core.executor import Executor
        # from packages.agent_core.observer import Observer
        # from packages.agent_core.reflector import Reflector
        # from packages.agent_core.refiner import Refiner
        
        # For now, use placeholder
        self.planner = None
        self.executor = None
        self.observer = None
        self.reflector = None
        self.refiner = None
    
    async def execute(
        self,
        query: str,
        session_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute Smart Buyer orchestration
        
        Args:
            query: User query (e.g., "So sánh giá iPhone 15 trên Shopee và Lazada")
            session_id: Session identifier
            context: Optional context
            
        Returns:
            Complete Smart Buyer result with recommendations
        """
        # Initialize execution state
        state = {
            "query": query,
            "session_id": session_id,
            "steps": [],
            "current_step": 0
        }
        
        # Step 1: PLAN - Understand user intent using agent_core.planner
        plan = await self._plan(query, context, state)
        state["plan"] = plan
        state["steps"].append({"phase": "plan", "output": plan})
        
        # Step 2: ACT - Execute search using tools
        search_results = await self._act(plan, state)
        state["search_results"] = search_results
        state["steps"].append({"phase": "act", "output": search_results})
        
        # Step 3: OBSERVE - Analyze results
        observation = await self._observe(search_results, state)
        state["observation"] = observation
        state["steps"].append({"phase": "observe", "output": observation})
        
        # Step 4: SCORE - Rank by relevance using decision_core
        scored_results = await self._score(search_results, plan, state)
        state["scored_results"] = scored_results
        state["steps"].append({"phase": "score", "output": scored_results})
        
        # Step 5: EXPLAIN - Generate explanation using LLM + decision_core
        explanation = await self._explain(scored_results, plan, state)
        state["explanation"] = explanation
        state["steps"].append({"phase": "explain", "output": explanation})
        
        # Step 6: REFINE - Check if we need another iteration
        refinement = await self._refine(state)
        state["steps"].append({"phase": "refine", "output": refinement})
        
        # Generate final response
        final_response = await self._generate_final_response(state)
        
        # Save to memory
        await self._save_memory(session_id, state)
        
        return {
            "response": final_response,
            "type": "smart_buyer",
            "state": state,
            "top_recommendations": scored_results[:3] if scored_results else [],
            "explanation": explanation,
            "metadata": {
                "query_intent": plan.get("intent"),
                "total_products": len(search_results.get("results", [])),
                "steps_taken": len(state["steps"])
            }
        }
    
    async def _plan(
        self,
        query: str,
        context: Optional[Dict[str, Any]],
        state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        PLAN phase: Understand user intent
        - Does user want to compare A vs B?
        - Or just find "best in category"?
        """
        # Use query_understanding from search_core
        if self.query_understanding:
            parsed_query = self.query_understanding.parse_query(query)
        else:
            parsed_query = {
                "normalized_query": query.lower(),
                "intent": "search",
                "entities": {},
                "filters": {}
            }
        
        # TODO: Use agent_core.planner for more sophisticated planning
        # if self.planner:
        #     plan = await self.planner.create_plan(query, parsed_query)
        
        # Determine search strategy
        intent = parsed_query.get("intent")
        
        plan = {
            "intent": intent,
            "query_info": parsed_query,
            "search_strategy": self._determine_search_strategy(parsed_query),
            "comparison_mode": intent == "compare",
            "sites_to_search": context.get("sites") if context else ["shopee", "lazada", "tiki"],
            "max_results": context.get("max_results", 20) if context else 20
        }
        
        return plan
    
    def _determine_search_strategy(self, parsed_query: Dict[str, Any]) -> str:
        """Determine search strategy based on parsed query"""
        intent = parsed_query.get("intent")
        
        if intent == "compare":
            return "compare_specific_products"
        elif intent == "filter":
            return "filter_by_criteria"
        elif intent == "recommend":
            return "find_best_overall"
        else:
            return "general_search"
    
    async def _act(
        self,
        plan: Dict[str, Any],
        state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        ACT phase: Execute search using price_compare_tool
        Calls search_core.ecommerce.price_compare
        """
        query = state["query"]
        sites = plan.get("sites_to_search", ["shopee", "lazada", "tiki"])
        
        # Use price_compare from search_core
        if self.price_compare:
            results = self.price_compare.compare_prices(
                product_name=query,
                sites=sites
            )
        else:
            # Fallback
            results = {
                "query": query,
                "total_results": 0,
                "results": [],
                "best_price": None,
                "summary": {}
            }
        
        # TODO: Use agent_core.executor for more sophisticated execution
        # if self.executor:
        #     results = await self.executor.execute_action("price_compare", params)
        
        return results
    
    async def _observe(
        self,
        search_results: Dict[str, Any],
        state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        OBSERVE phase: Analyze search results
        """
        results = search_results.get("results", [])
        
        observation = {
            "total_found": len(results),
            "has_results": len(results) > 0,
            "price_range": search_results.get("summary", {}).get("price_range", 0),
            "sites_found": list(set(r.get("site") for r in results if r.get("site"))),
            "quality_metrics": self._analyze_quality(results)
        }
        
        # TODO: Use agent_core.observer for deeper analysis
        # if self.observer:
        #     observation = await self.observer.analyze(search_results, state)
        
        return observation
    
    def _analyze_quality(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze quality metrics of results"""
        if not results:
            return {"avg_rating": 0, "avg_reviews": 0}
        
        ratings = [r.get("rating", 0) for r in results if r.get("rating")]
        reviews = [r.get("review_count", 0) for r in results if r.get("review_count")]
        
        return {
            "avg_rating": sum(ratings) / len(ratings) if ratings else 0,
            "avg_reviews": sum(reviews) / len(reviews) if reviews else 0,
            "high_quality_count": len([r for r in ratings if r >= 4.0])
        }
    
    async def _score(
        self,
        search_results: Dict[str, Any],
        plan: Dict[str, Any],
        state: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        SCORE phase: Rank by relevance using decision_core.scoring
        Sort by relevance (not just price)
        """
        results = search_results.get("results", [])
        
        if not results:
            return []
        
        # First, rank using search_core.ranking (BM25 + business scores)
        if self.ranking:
            query = state["query"]
            ranked_results = self.ranking.rank_results(
                results,
                query,
                use_bm25=True,
                use_embeddings=False
            )
        else:
            ranked_results = results
        
        # Then, score using decision_core.scoring (multi-criteria)
        if self.scoring:
            scored_results = self.scoring.score_options(
                ranked_results,
                normalize=True
            )
        else:
            # Fallback: wrap in score format
            scored_results = [
                {"option": r, "total_score": 0.5}
                for r in ranked_results
            ]
        
        # Sort by total score
        scored_results.sort(key=lambda x: x.get("total_score", 0), reverse=True)
        
        return scored_results
    
    async def _explain(
        self,
        scored_results: List[Dict[str, Any]],
        plan: Dict[str, Any],
        state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        EXPLAIN phase: Generate explanation using LLM + decision_core.explainer
        - Reasons for choosing top 1-3 options
        - Pros/cons for each
        - Warnings (e.g., low review count, suspicious price)
        - Suggestions
        """
        if not scored_results:
            return {
                "recommendation": "No products found",
                "top_options": [],
                "warnings": [],
                "suggestions": ["Try different keywords", "Expand search to more sites"]
            }
        
        # Get top 3 options
        top_3 = scored_results[:3]
        
        # Use decision_core.explainer for comparison
        if self.explainer:
            options = [s.get("option", s) for s in top_3]
            comparison = self.explainer.compare_options(options, top_3)
        else:
            comparison = {"recommendation": {}, "tradeoffs": []}
        
        # Generate detailed explanation for each option
        explanations = []
        for i, scored in enumerate(top_3):
            option = scored.get("option", {})
            
            if self.explainer:
                explanation = self.explainer.explain_option(option, scored)
            else:
                explanation = {
                    "pros": [f"Option {i+1}"],
                    "cons": [],
                    "summary": "Product found"
                }
            
            explanations.append({
                "rank": i + 1,
                "product": option,
                "score": scored.get("total_score", 0),
                "pros": explanation.get("pros", []),
                "cons": explanation.get("cons", []),
                "summary": explanation.get("summary", "")
            })
        
        # Identify warnings
        warnings = self._identify_warnings(top_3)
        
        # Generate suggestions
        suggestions = self._generate_suggestions(scored_results, state)
        
        # Use LLM to generate natural language explanation
        natural_explanation = await self._generate_llm_explanation(
            explanations, comparison, warnings, suggestions
        )
        
        return {
            "recommendation": comparison.get("recommendation", {}),
            "top_options": explanations,
            "comparison": comparison,
            "warnings": warnings,
            "suggestions": suggestions,
            "natural_language": natural_explanation
        }
    
    def _identify_warnings(self, top_options: List[Dict[str, Any]]) -> List[str]:
        """Identify potential warnings for top options"""
        warnings = []
        
        for scored in top_options:
            option = scored.get("option", {})
            
            # Low review count warning
            review_count = option.get("review_count", 0)
            if review_count < 10:
                warnings.append(
                    f"⚠️ {option.get('name', 'Product')} has only {review_count} reviews - limited feedback"
                )
            
            # Suspiciously low price
            price = option.get("price", 0)
            rating = option.get("rating", 0)
            if price < 100000 and rating > 4.5:  # Example threshold
                warnings.append(
                    f"⚠️ {option.get('name', 'Product')} has unusually low price - verify authenticity"
                )
            
            # Low rating but high in results
            if rating < 3.5:
                warnings.append(
                    f"⚠️ {option.get('name', 'Product')} has low rating ({rating}/5)"
                )
        
        return warnings
    
    def _generate_suggestions(
        self,
        scored_results: List[Dict[str, Any]],
        state: Dict[str, Any]
    ) -> List[str]:
        """Generate helpful suggestions"""
        suggestions = []
        
        if len(scored_results) < 5:
            suggestions.append("💡 Try broader search terms to find more options")
        
        # Check price variance
        prices = [s.get("option", {}).get("price", 0) for s in scored_results[:5]]
        if prices:
            price_variance = max(prices) - min(prices)
            if price_variance > min(prices) * 0.5:  # More than 50% variance
                suggestions.append(
                    "💡 Large price difference detected - consider waiting for sales"
                )
        
        # Check if all from one site
        sites = [s.get("option", {}).get("site") for s in scored_results]
        unique_sites = set(sites)
        if len(unique_sites) == 1:
            suggestions.append(
                f"💡 All results from {list(unique_sites)[0]} - try other platforms"
            )
        
        return suggestions
    
    async def _generate_llm_explanation(
        self,
        explanations: List[Dict[str, Any]],
        comparison: Dict[str, Any],
        warnings: List[str],
        suggestions: List[str]
    ) -> str:
        """Generate natural language explanation using LLM"""
        # TODO: Use LLM to generate natural explanation
        # This is a placeholder
        
        if not explanations:
            return "No products found matching your criteria."
        
        best = explanations[0]
        text = f"**Top Recommendation:**\n\n"
        text += f"🏆 {best['product'].get('name', 'Product')}\n"
        text += f"• Score: {best['score']:.2f}/1.0\n"
        text += f"• Price: {best['product'].get('price', 0):,.0f} VNĐ\n"
        text += f"• Rating: {best['product'].get('rating', 0)}/5 "
        text += f"({best['product'].get('review_count', 0)} reviews)\n\n"
        
        if best['pros']:
            text += "**Pros:**\n"
            for pro in best['pros'][:3]:
                text += f"✓ {pro}\n"
        
        if warnings:
            text += f"\n**Warnings:**\n"
            for warning in warnings[:2]:
                text += f"{warning}\n"
        
        if suggestions:
            text += f"\n**Suggestions:**\n"
            for suggestion in suggestions[:2]:
                text += f"{suggestion}\n"
        
        return text
    
    async def _refine(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        REFINE phase: Check if we need another iteration
        """
        # TODO: Use agent_core.reflector and refiner
        # if self.reflector:
        #     reflection = await self.reflector.reflect(state)
        #     if reflection.should_refine:
        #         return await self.refiner.refine_plan(state)
        
        # For now, simple check
        results_count = len(state.get("search_results", {}).get("results", []))
        
        refinement = {
            "should_refine": False,
            "reason": "Sufficient results found",
            "confidence": 0.8
        }
        
        if results_count < 3:
            refinement["should_refine"] = False  # Could be True for retry
            refinement["reason"] = "Low result count, but proceeding"
            refinement["confidence"] = 0.5
        
        return refinement
    
    async def _generate_final_response(self, state: Dict[str, Any]) -> str:
        """Generate final user-facing response"""
        explanation = state.get("explanation", {})
        natural_explanation = explanation.get("natural_language", "")
        
        if natural_explanation:
            return natural_explanation
        
        # Fallback
        return f"Search completed for: {state['query']}"

