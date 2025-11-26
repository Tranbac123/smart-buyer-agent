# Agent Profiles & Policies

## Overview

The **Profile & Policy system** makes agents **config-driven** rather than hard-coded. Each agent type (smart_buyer, deep_research, chat) has a profile that defines:

- **System prompts** - How the agent should behave
- **Tool allowlist** - Which tools can be used
- **Execution limits** - Max steps, tokens, timeout
- **Quality controls** - Confidence thresholds, citation requirements
- **Cost controls** - Budget limits, caching preferences
- **Safety constraints** - Content filters, rate limits

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ProfileManager                            │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Profiles Registry                                  │    │
│  │  • smart_buyer → SmartBuyerProfile                 │    │
│  │  • deep_research → DeepResearchProfile             │    │
│  │  • chat → ChatProfile                              │    │
│  └────────────────────────────────────────────────────┘    │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Policies                                          │    │
│  │  • SafetyPolicy (content, rate limits, tools)      │    │
│  │  • CostPolicy (budget, tokens, model selection)    │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                         ↓
              Orchestrator uses profiles
```

## Structure

```
packages/agent_core/agent_core/
├── profiles/
│   ├── __init__.py
│   ├── base_profile.py              # BaseProfile, AgentConfig
│   ├── smart_buyer_profile.py       # E-commerce agent config
│   ├── deep_research_profile.py     # Research agent config
│   ├── chat_profile.py              # Chat agent config
│   └── profile_manager.py           # Profile management
└── policy/
    ├── __init__.py
    ├── base_policy.py               # BasePolicy, PolicyViolation
    ├── safety_policy.py             # Content filters, rate limits
    └── cost_policy.py               # Budget, token limits
```

## Usage

### 1. Get Profile Configuration

```python
from packages.agent_core.agent_core.profiles import (
    SmartBuyerProfile,
    DeepResearchProfile,
    ChatProfile
)

# Get Smart Buyer configuration
profile = SmartBuyerProfile()
config = profile.get_config()

print(config.agent_type)          # "smart_buyer"
print(config.system_prompt)       # Full system prompt
print(config.allowed_tools)       # ["price_compare_tool", "decision_tool", ...]
print(config.max_steps)           # 6
print(config.max_tokens)          # 50000
print(config.timeout_seconds)     # 120
```

### 2. Use with Orchestrator

```python
from packages.agent_core.agent_core.profiles.profile_manager import get_profile_manager

# Get profile manager
profile_manager = get_profile_manager()

# Get configuration for agent type
config = profile_manager.get_config("smart_buyer")

# Initialize orchestrator with profile config
orchestrator = SmartBuyerOrchestrator(
    llm_client=llm_client,
    memory_service=memory_service,
    tools_registry=tools_registry,
    config=config  # ← Pass profile configuration
)

# Orchestrator now uses:
# - config.system_prompt for LLM
# - config.allowed_tools for tool filtering
# - config.max_steps for loop limit
# - config.max_tokens for budget
```

### 3. Validate Execution

```python
# Validate before execution
context = {
    "query": "So sánh giá iPhone 15",
    "user_id": "user_123",
    "timestamp": time.time(),
    "requested_tools": ["price_compare_tool"],
    "max_tokens": 30000,
}

is_valid, violations = profile_manager.validate_execution(
    agent_type="smart_buyer",
    context=context
)

if not is_valid:
    for violation in violations:
        print(f"Policy violation: {violation}")
else:
    # Proceed with execution
    result = await orchestrator.execute(...)
```

### 4. Custom Profile

```python
from packages.agent_core.agent_core.profiles.base_profile import BaseProfile, AgentConfig

class CustomProfile(BaseProfile):
    def get_config(self) -> AgentConfig:
        return AgentConfig(
            agent_type="custom",
            agent_name="Custom Agent",
            description="My custom agent",
            system_prompt="You are a custom agent...",
            allowed_tools=["search_web", "calculator"],
            max_steps=5,
            max_tokens=20000,
            timeout_seconds=60
        )
    
    def get_system_prompt(self) -> str:
        return "You are a custom agent..."
    
    def get_allowed_tools(self) -> List[str]:
        return ["search_web", "calculator"]

# Register custom profile
profile_manager.register_profile("custom", CustomProfile())
```

## Profile Comparison

### Smart Buyer Profile

```python
SmartBuyerProfile(
    max_steps=6,              # Quick shopping queries
    max_tokens=50000,         # Moderate token budget
    timeout_seconds=120,      # 2 minutes
)

config = {
    "allowed_tools": [
        "price_compare_tool",
        "decision_tool",
        "search_web",
        "ranking_tool",
        "scoring_tool",
        "explainer_tool"
    ],
    "scoring_weights": {
        "price": 0.25,
        "rating": 0.30,
        "review_count": 0.25,
        "sold": 0.20
    },
    "min_confidence": 0.6,
    "require_sources": True,
    "max_cost_usd": 0.50
}
```

**Use Case**: E-commerce search, price comparison, product recommendations

### Deep Research Profile

```python
DeepResearchProfile(
    max_steps=15,             # Deep research needs more iterations
    max_tokens=200000,        # Large token budget
    timeout_seconds=600,      # 10 minutes
)

config = {
    "allowed_tools": [
        "search_web",
        "search_academic",
        "summarize_doc",
        "fact_checker",
        "rag_retriever"
    ],
    "min_confidence": 0.8,    # High confidence required
    "require_sources": True,
    "enable_reflection": True,
    "max_cost_usd": 2.00
}
```

**Use Case**: In-depth research, analysis, comprehensive reports

### Chat Profile

```python
ChatProfile(
    max_steps=3,              # Simple conversations
    max_tokens=10000,         # Small token budget
    timeout_seconds=30,       # Fast responses
)

config = {
    "allowed_tools": [
        "search_web",         # Minimal tools
        "calculator",
        "datetime"
    ],
    "min_confidence": 0.5,
    "require_sources": False,
    "enable_reflection": False,  # Speed over depth
    "max_cost_usd": 0.05
}
```

**Use Case**: Quick conversations, simple questions

## Policies

### Safety Policy

Enforces safety constraints:

```python
from packages.agent_core.agent_core.policy.safety_policy import SafetyPolicy

safety = SafetyPolicy(
    content_filters=["adult", "illegal", "harmful"],
    blocked_keywords={"hack", "crack", "pirate"},
    rate_limit_per_minute=20,
    max_timeout_seconds=600,
    allowed_tools=["search_web", "price_compare_tool"]
)

# Validate execution
is_valid, violation = safety.validate({
    "query": "How to hack...",
    "user_id": "user_123"
})

if not is_valid:
    print(violation.message)  # "Query contains blocked keyword: hack"
```

**Features:**
- Content filtering (adult, illegal, harmful)
- Keyword blocking
- Rate limiting (per user)
- Timeout enforcement
- Tool allowlist/blocklist

### Cost Policy

Enforces cost and resource constraints:

```python
from packages.agent_core.agent_core.policy.cost_policy import CostPolicy

cost = CostPolicy(
    max_cost_per_request=1.0,      # $1 max per request
    max_tokens_per_request=100000,
    max_tool_calls=50,
    enable_caching=True,
    prefer_cheaper_models=True
)

# Validate execution
is_valid, violation = cost.validate({
    "model": "gpt-4",
    "max_tokens": 150000,  # Exceeds budget!
    "estimated_steps": 10
})

# Calculate actual cost
actual_cost = cost.calculate_actual_cost(
    model="gpt-4",
    input_tokens=5000,
    output_tokens=2000,
    tools_used=["search_web", "price_compare_tool"]
)
print(f"Actual cost: ${actual_cost:.4f}")
```

**Features:**
- Cost estimation before execution
- Token budget enforcement
- Tool call limits
- Model cost tracking (GPT-4, Claude, etc.)
- Caching recommendations
- Cheaper model suggestions

## Integration with Orchestrator

### Before (Hard-coded):

```python
class SmartBuyerOrchestrator:
    async def execute(self, query, session_id):
        # Hard-coded limits
        max_steps = 6
        timeout = 120
        
        # Hard-coded tools
        tools = ["price_compare", "decision"]
        
        # Hard-coded prompt
        prompt = "You are a shopping agent..."
```

### After (Config-driven):

```python
class SmartBuyerOrchestrator:
    def __init__(self, ..., config: AgentConfig):
        self.config = config
        
    async def execute(self, query, session_id):
        # Use config
        max_steps = self.config.max_steps
        timeout = self.config.timeout_seconds
        tools = self.config.allowed_tools
        prompt = self.config.system_prompt
        
        # Validate with policies
        is_valid, violations = self._validate(context)
        if not is_valid:
            return self._handle_violations(violations)
```

## Benefits

✅ **Config-driven**: No hard-coded logic in orchestrators
✅ **Easy to extend**: Add new agent types without touching core
✅ **Centralized control**: All agent behavior in one place
✅ **Policy enforcement**: Safety and cost controls
✅ **Customizable**: Override defaults per use case
✅ **Testable**: Easy to test different configurations

## Example: Adding New Agent Type

```python
# 1. Create profile
class CodeAgentProfile(BaseProfile):
    def get_config(self) -> AgentConfig:
        return AgentConfig(
            agent_type="code_agent",
            agent_name="Code Agent",
            system_prompt="You are a coding assistant...",
            allowed_tools=["code_search", "linter", "test_runner"],
            max_steps=10,
            max_tokens=80000,
            timeout_seconds=180
        )

# 2. Register profile
profile_manager.register_profile("code_agent", CodeAgentProfile())

# 3. Use in orchestrator
config = profile_manager.get_config("code_agent")
orchestrator = CodeAgentOrchestrator(..., config=config)

# That's it! No changes to core engine needed.
```

## Future Enhancements

1. **Dynamic Profiles**: Load from database/config files
2. **User Preferences**: Per-user profile customization
3. **A/B Testing**: Test different profile configurations
4. **Profile Inheritance**: Base profiles with overrides
5. **Real-time Updates**: Hot-reload profiles without restart
6. **Analytics**: Track profile performance metrics

