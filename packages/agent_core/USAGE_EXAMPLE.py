"""
Usage Example: Agent Profiles & Policies
Demonstrates how to use the profile & policy system
"""

import time
from agent_core.profiles import SmartBuyerProfile, DeepResearchProfile, ChatProfile
from agent_core.profiles.profile_manager import get_profile_manager
from agent_core.policy import SafetyPolicy, CostPolicy


# ============================================================================
# Example 1: Basic Profile Usage
# ============================================================================

def example_basic_profile():
    """Get and use a profile configuration"""
    
    # Get Smart Buyer profile
    profile = SmartBuyerProfile()
    config = profile.get_config()
    
    print("=== Smart Buyer Profile ===")
    print(f"Agent Type: {config.agent_type}")
    print(f"Max Steps: {config.max_steps}")
    print(f"Max Tokens: {config.max_tokens}")
    print(f"Timeout: {config.timeout_seconds}s")
    print(f"Allowed Tools: {', '.join(config.allowed_tools[:5])}...")
    print(f"Max Cost: ${config.max_cost_usd}")
    print()


# ============================================================================
# Example 2: Using Profile Manager
# ============================================================================

def example_profile_manager():
    """Use ProfileManager to get configurations"""
    
    manager = get_profile_manager()
    
    # Get different profile configurations
    for agent_type in ["smart_buyer", "deep_research", "chat"]:
        config = manager.get_config(agent_type)
        print(f"=== {config.agent_name} ===")
        print(f"Max Steps: {config.max_steps}")
        print(f"Max Tokens: {config.max_tokens:,}")
        print(f"Target Latency: {config.target_latency_ms}ms")
        print()


# ============================================================================
# Example 3: Policy Validation
# ============================================================================

def example_policy_validation():
    """Validate execution against policies"""
    
    manager = get_profile_manager()
    
    # Context for a shopping query
    context = {
        "query": "So sánh giá iPhone 15 trên Shopee và Lazada",
        "user_id": "user_123",
        "timestamp": time.time(),
        "requested_tools": ["price_compare_tool", "decision_tool"],
        "max_tokens": 30000,
        "model": "gpt-4",
        "estimated_steps": 5,
        "estimated_output_tokens": 1000,
    }
    
    # Validate against Smart Buyer policies
    is_valid, violations = manager.validate_execution("smart_buyer", context)
    
    if is_valid:
        print("✅ Validation passed! Safe to execute.")
    else:
        print("❌ Policy violations detected:")
        for violation in violations:
            print(f"  - {violation}")
    print()


# ============================================================================
# Example 4: Safety Policy
# ============================================================================

def example_safety_policy():
    """Test safety policy enforcement"""
    
    safety = SafetyPolicy(
        content_filters=["adult", "illegal"],
        rate_limit_per_minute=20,
        allowed_tools=["price_compare_tool", "search_web"]
    )
    
    # Test 1: Valid query
    context1 = {
        "query": "Best laptops under $1000",
        "user_id": "user_123",
        "timestamp": time.time(),
        "requested_tools": ["search_web"]
    }
    
    is_valid, violation = safety.validate(context1)
    print(f"Query 1: {'✅ Valid' if is_valid else f'❌ {violation}'}")
    
    # Test 2: Blocked tool
    context2 = {
        "query": "Search for products",
        "user_id": "user_123",
        "timestamp": time.time(),
        "requested_tools": ["admin_tool"]  # Not in allowed list
    }
    
    is_valid, violation = safety.validate(context2)
    print(f"Query 2: {'✅ Valid' if is_valid else f'❌ {violation}'}")
    print()


# ============================================================================
# Example 5: Cost Policy
# ============================================================================

def example_cost_policy():
    """Test cost policy and estimation"""
    
    cost = CostPolicy(
        max_cost_per_request=1.0,
        max_tokens_per_request=100000,
        prefer_cheaper_models=True
    )
    
    # Test context
    context = {
        "model": "gpt-4",
        "input_tokens": 5000,
        "estimated_output_tokens": 2000,
        "max_tokens": 80000,
        "planned_tools": ["search_web", "price_compare_tool"],
        "estimated_steps": 5
    }
    
    # Validate
    is_valid, violation = cost.validate(context)
    print(f"Cost Validation: {'✅ Valid' if is_valid else f'⚠️  {violation}'}")
    
    # Calculate actual cost after execution
    actual_cost = cost.calculate_actual_cost(
        model="gpt-4",
        input_tokens=5000,
        output_tokens=2000,
        tools_used=["search_web", "price_compare_tool"]
    )
    
    print(f"Estimated cost: ${actual_cost:.4f}")
    print()


# ============================================================================
# Example 6: Integration with Orchestrator
# ============================================================================

def example_orchestrator_integration():
    """How to use profiles in orchestrator"""
    
    from typing import Any, Dict, Optional
    
    class SmartBuyerOrchestrator:
        """Example orchestrator using profiles"""
        
        def __init__(self, llm_client: Any, config: Any):
            self.llm_client = llm_client
            self.config = config
            
        async def execute(self, query: str, session_id: str, context: Optional[Dict] = None):
            """Execute with profile configuration"""
            
            # Use profile configuration
            print(f"Executing with profile: {self.config.agent_name}")
            print(f"System Prompt: {self.config.system_prompt[:100]}...")
            print(f"Max Steps: {self.config.max_steps}")
            print(f"Allowed Tools: {self.config.allowed_tools}")
            
            # Validate context
            validation_context = {
                "query": query,
                "session_id": session_id,
                "timestamp": time.time(),
                "requested_tools": self.config.allowed_tools[:3],
                "max_tokens": self.config.max_tokens,
            }
            
            manager = get_profile_manager()
            is_valid, violations = manager.validate_execution(
                self.config.agent_type,
                validation_context
            )
            
            if not is_valid:
                return {"error": "Policy violations", "violations": violations}
            
            # Execute with profile constraints
            # ... (actual execution logic)
            
            return {"status": "success", "message": "Executed with profile config"}
    
    # Initialize with profile
    manager = get_profile_manager()
    config = manager.get_config("smart_buyer")
    
    print("=== Orchestrator Integration ===")
    # orchestrator = SmartBuyerOrchestrator(llm_client, config)
    # result = await orchestrator.execute(query, session_id)
    print("Orchestrator would use profile config for:")
    print("- System prompts")
    print("- Tool filtering")
    print("- Execution limits")
    print("- Cost controls")
    print()


# ============================================================================
# Example 7: Custom Profile
# ============================================================================

def example_custom_profile():
    """Create and register a custom profile"""
    
    from agent_core.profiles.base_profile import BaseProfile, AgentConfig
    from typing import List
    
    class EcommerceAnalystProfile(BaseProfile):
        """Custom profile for e-commerce analysis"""
        
        def get_config(self) -> AgentConfig:
            return AgentConfig(
                agent_type="ecommerce_analyst",
                agent_name="E-commerce Analyst",
                description="Analyzes e-commerce trends and competition",
                system_prompt="You are an e-commerce analyst...",
                allowed_tools=[
                    "price_compare_tool",
                    "market_research",
                    "competitor_analysis",
                    "trend_analyzer"
                ],
                max_steps=12,
                max_tokens=100000,
                timeout_seconds=300,
                min_confidence=0.75,
                max_cost_usd=1.50
            )
        
        def get_system_prompt(self) -> str:
            return "You are an expert e-commerce analyst..."
        
        def get_allowed_tools(self) -> List[str]:
            return ["price_compare_tool", "market_research", "competitor_analysis"]
    
    # Register custom profile
    manager = get_profile_manager()
    manager.register_profile("ecommerce_analyst", EcommerceAnalystProfile())
    
    # Use custom profile
    config = manager.get_config("ecommerce_analyst")
    print("=== Custom Profile ===")
    print(f"Agent: {config.agent_name}")
    print(f"Tools: {', '.join(config.allowed_tools)}")
    print()


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("Agent Profiles & Policies - Usage Examples")
    print("=" * 70)
    print()
    
    example_basic_profile()
    example_profile_manager()
    example_policy_validation()
    example_safety_policy()
    example_cost_policy()
    example_orchestrator_integration()
    example_custom_profile()
    
    print("=" * 70)
    print("All examples completed!")
    print("=" * 70)

