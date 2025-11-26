"""
Cost Policy
Enforces cost and resource constraints on agent execution
"""

from typing import Dict, Any, Optional
from .base_policy import BasePolicy, PolicyViolation, PolicyViolationType


class CostPolicy(BasePolicy):
    """
    Enforces cost constraints including:
    - Maximum cost per request
    - Token budget limits
    - Tool usage costs
    - LLM model selection based on budget
    """
    
    # Cost estimates (USD) - approximate OpenAI pricing
    MODEL_COSTS = {
        "gpt-4": {"input": 0.03 / 1000, "output": 0.06 / 1000},      # per token
        "gpt-4-turbo": {"input": 0.01 / 1000, "output": 0.03 / 1000},
        "gpt-3.5-turbo": {"input": 0.0005 / 1000, "output": 0.0015 / 1000},
        "claude-3-opus": {"input": 0.015 / 1000, "output": 0.075 / 1000},
        "claude-3-sonnet": {"input": 0.003 / 1000, "output": 0.015 / 1000},
    }
    
    TOOL_COSTS = {
        "search_web": 0.002,           # per search
        "price_compare_tool": 0.005,   # per comparison
        "search_academic": 0.010,      # per search
        "image_search": 0.005,         # per search
        "fact_checker": 0.003,         # per check
    }
    
    def __init__(
        self,
        max_cost_per_request: float = 1.0,
        max_tokens_per_request: int = 100000,
        max_tool_calls: int = 50,
        enable_caching: bool = True,
        prefer_cheaper_models: bool = False,
        warn_at_percent: float = 0.8
    ):
        """
        Initialize Cost Policy
        
        Args:
            max_cost_per_request: Maximum cost in USD per request
            max_tokens_per_request: Maximum tokens per request
            max_tool_calls: Maximum number of tool calls
            enable_caching: Use caching to reduce costs
            prefer_cheaper_models: Prefer cheaper models when possible
            warn_at_percent: Warn when cost exceeds this % of budget
        """
        self.max_cost_per_request = max_cost_per_request
        self.max_tokens_per_request = max_tokens_per_request
        self.max_tool_calls = max_tool_calls
        self.enable_caching = enable_caching
        self.prefer_cheaper_models = prefer_cheaper_models
        self.warn_at_percent = warn_at_percent
    
    def validate(self, context: Dict[str, Any]) -> tuple[bool, Optional[PolicyViolation]]:
        """Validate context against cost policy"""
        
        # Check token budget
        violation = self._check_token_budget(context)
        if violation:
            return False, violation
        
        # Check estimated cost
        violation = self._check_estimated_cost(context)
        if violation:
            return False, violation
        
        # Check tool call limits
        violation = self._check_tool_limits(context)
        if violation:
            return False, violation
        
        return True, None
    
    def enforce(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Enforce cost constraints"""
        modified = context.copy()
        
        # Enforce token budget
        if "max_tokens" in modified:
            modified["max_tokens"] = min(
                modified["max_tokens"],
                self.max_tokens_per_request
            )
        
        # Enforce tool call limits
        if "max_tool_calls" in modified:
            modified["max_tool_calls"] = min(
                modified["max_tool_calls"],
                self.max_tool_calls
            )
        
        # Enable caching if policy requires it
        if self.enable_caching:
            modified["use_cache"] = True
        
        # Suggest cheaper model if policy prefers it
        if self.prefer_cheaper_models:
            modified["model"] = self._suggest_cheaper_model(
                modified.get("model", "gpt-4")
            )
        
        # Add cost tracking metadata
        modified["cost_policy_applied"] = True
        modified["max_cost_budget"] = self.max_cost_per_request
        modified["cost_tracking_enabled"] = True
        
        return modified
    
    def _check_token_budget(self, context: Dict[str, Any]) -> Optional[PolicyViolation]:
        """Check token budget"""
        requested_tokens = context.get("max_tokens", 0)
        
        if requested_tokens > self.max_tokens_per_request:
            return PolicyViolation(
                violation_type=PolicyViolationType.COST,
                message=f"Requested tokens {requested_tokens} exceeds budget {self.max_tokens_per_request}",
                severity="error",
                details={
                    "requested": requested_tokens,
                    "budget": self.max_tokens_per_request
                }
            )
        
        return None
    
    def _check_estimated_cost(self, context: Dict[str, Any]) -> Optional[PolicyViolation]:
        """Check estimated cost"""
        estimated_cost = self._estimate_cost(context)
        
        if estimated_cost > self.max_cost_per_request:
            return PolicyViolation(
                violation_type=PolicyViolationType.COST,
                message=f"Estimated cost ${estimated_cost:.4f} exceeds budget ${self.max_cost_per_request:.4f}",
                severity="error",
                details={
                    "estimated_cost": estimated_cost,
                    "budget": self.max_cost_per_request
                }
            )
        
        # Warn if approaching budget
        if estimated_cost > self.max_cost_per_request * self.warn_at_percent:
            return PolicyViolation(
                violation_type=PolicyViolationType.COST,
                message=f"Cost ${estimated_cost:.4f} approaching budget ${self.max_cost_per_request:.4f}",
                severity="warning",
                details={
                    "estimated_cost": estimated_cost,
                    "budget": self.max_cost_per_request,
                    "percent": (estimated_cost / self.max_cost_per_request) * 100
                }
            )
        
        return None
    
    def _check_tool_limits(self, context: Dict[str, Any]) -> Optional[PolicyViolation]:
        """Check tool call limits"""
        tool_calls_made = len(context.get("tool_call_history", []))
        
        if tool_calls_made >= self.max_tool_calls:
            return PolicyViolation(
                violation_type=PolicyViolationType.RESOURCE,
                message=f"Tool calls {tool_calls_made} exceeds limit {self.max_tool_calls}",
                severity="error",
                details={
                    "tool_calls": tool_calls_made,
                    "limit": self.max_tool_calls
                }
            )
        
        return None
    
    def _estimate_cost(self, context: Dict[str, Any]) -> float:
        """Estimate cost of execution"""
        total_cost = 0.0
        
        # LLM cost
        model = context.get("model", "gpt-4")
        input_tokens = context.get("input_tokens", 1000)
        output_tokens = context.get("estimated_output_tokens", 500)
        
        if model in self.MODEL_COSTS:
            model_cost = self.MODEL_COSTS[model]
            total_cost += input_tokens * model_cost["input"]
            total_cost += output_tokens * model_cost["output"]
        
        # Tool costs
        planned_tools = context.get("planned_tools", [])
        for tool in planned_tools:
            if tool in self.TOOL_COSTS:
                total_cost += self.TOOL_COSTS[tool]
        
        # Multiply by estimated steps
        estimated_steps = context.get("estimated_steps", 1)
        total_cost *= estimated_steps
        
        return total_cost
    
    def _suggest_cheaper_model(self, current_model: str) -> str:
        """Suggest a cheaper alternative model"""
        # Model hierarchy (expensive to cheap)
        model_hierarchy = [
            "gpt-4",
            "claude-3-opus",
            "gpt-4-turbo",
            "claude-3-sonnet",
            "gpt-3.5-turbo"
        ]
        
        # If current model is not in hierarchy, keep it
        if current_model not in model_hierarchy:
            return current_model
        
        current_idx = model_hierarchy.index(current_model)
        
        # Suggest next cheaper model
        if current_idx < len(model_hierarchy) - 1:
            return model_hierarchy[current_idx + 1]
        
        return current_model
    
    def calculate_actual_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        tools_used: list
    ) -> float:
        """Calculate actual cost after execution"""
        total_cost = 0.0
        
        # LLM cost
        if model in self.MODEL_COSTS:
            model_cost = self.MODEL_COSTS[model]
            total_cost += input_tokens * model_cost["input"]
            total_cost += output_tokens * model_cost["output"]
        
        # Tool costs
        for tool in tools_used:
            if tool in self.TOOL_COSTS:
                total_cost += self.TOOL_COSTS[tool]
        
        return total_cost

