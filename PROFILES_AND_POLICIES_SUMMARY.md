# Agent Profiles & Policies - Implementation Summary

## 🎯 What Was Built

A **config-driven agent system** that makes agents extensible and maintainable through **Profiles** and **Policies**.

## 📦 Structure Created

```
packages/agent_core/agent_core/
├── profiles/                           # Agent configurations
│   ├── __init__.py
│   ├── base_profile.py                # BaseProfile, AgentConfig
│   ├── smart_buyer_profile.py         # E-commerce agent config
│   ├── deep_research_profile.py       # Research agent config
│   ├── chat_profile.py                # Chat agent config
│   └── profile_manager.py             # Profile management
└── policy/                             # Safety & cost policies
    ├── __init__.py
    ├── base_policy.py                 # BasePolicy, PolicyViolation
    ├── safety_policy.py               # Content, rate limits, tools
    └── cost_policy.py                 # Budget, tokens, model costs
```

**Total**: 10 Python files created

## 🌟 Key Concepts

### Profile = Agent Configuration

Each agent type has a **Profile** that defines:

```python
AgentConfig(
    # Identity
    agent_type="smart_buyer",
    agent_name="Smart Buyer Agent",
    
    # Behavior
    system_prompt="You are a shopping assistant...",
    
    # Tools
    allowed_tools=["price_compare_tool", "decision_tool", ...],
    
    # Limits
    max_steps=6,
    max_tokens=50000,
    timeout_seconds=120,
    
    # Quality
    min_confidence=0.6,
    require_sources=True,
    
    # Cost
    max_cost_usd=0.50,
    use_cache=True
)
```

### Policy = Constraint Enforcement

Policies validate and enforce constraints:

```python
# Safety Policy
SafetyPolicy(
    content_filters=["adult", "illegal"],
    rate_limit_per_minute=20,
    allowed_tools=[...]
)

# Cost Policy
CostPolicy(
    max_cost_per_request=1.0,
    max_tokens_per_request=100000,
    prefer_cheaper_models=True
)
```

## 🚀 Three Agent Profiles Implemented

### 1. Smart Buyer Profile

**Purpose**: E-commerce search and purchasing decisions

```python
SmartBuyerProfile(
    max_steps=6,              # Quick shopping queries
    max_tokens=50000,         # Moderate budget
    timeout_seconds=120       # 2 minutes
)
```

**Configuration:**
- **Allowed Tools**: price_compare_tool, decision_tool, search_web, ranking_tool, scoring_tool
- **Scoring Weights**: price (25%), rating (30%), reviews (25%), sales (20%)
- **Min Confidence**: 0.6
- **Require Sources**: Yes
- **Max Cost**: $0.50

**System Prompt**: Instructs agent to search across multiple sites, analyze by multiple criteria, provide warnings and suggestions.

### 2. Deep Research Profile

**Purpose**: In-depth research and analysis

```python
DeepResearchProfile(
    max_steps=15,             # Deep research needs iterations
    max_tokens=200000,        # Large budget
    timeout_seconds=600       # 10 minutes
)
```

**Configuration:**
- **Allowed Tools**: search_web, search_academic, summarize_doc, fact_checker, rag_retriever
- **Min Sources**: 3-10
- **Min Confidence**: 0.8 (high bar)
- **Require Sources**: Yes (always cite)
- **Max Cost**: $2.00

**System Prompt**: Plan → Act → Observe → Reflect → Refine loop, cite all sources, acknowledge uncertainty.

### 3. Chat Profile

**Purpose**: Quick conversational interactions

```python
ChatProfile(
    max_steps=3,              # Simple conversations
    max_tokens=10000,         # Small budget
    timeout_seconds=30        # Fast responses
)
```

**Configuration:**
- **Allowed Tools**: search_web, calculator, datetime, weather (minimal)
- **Min Confidence**: 0.5 (low bar)
- **Require Sources**: No
- **Enable Reflection**: No (speed over depth)
- **Max Cost**: $0.05

**System Prompt**: Friendly assistant, concise responses, no deep analysis.

## 📊 Profile Comparison Table

| Aspect | Smart Buyer | Deep Research | Chat |
|--------|-------------|---------------|------|
| **Max Steps** | 6 | 15 | 3 |
| **Max Tokens** | 50,000 | 200,000 | 10,000 |
| **Timeout** | 2 min | 10 min | 30 sec |
| **Target Latency** | 3 sec | 30 sec | 1 sec |
| **Tool Count** | ~12 tools | ~15 tools | ~5 tools |
| **Min Confidence** | 0.6 | 0.8 | 0.5 |
| **Require Sources** | Yes | Yes | No |
| **Max Cost** | $0.50 | $2.00 | $0.05 |
| **Use Case** | Shopping | Research | Chat |

## 🛡️ Policy System

### Safety Policy Features

```python
SafetyPolicy(
    content_filters=["adult", "illegal", "harmful"],
    blocked_keywords={"hack", "crack", "pirate"},
    rate_limit_per_minute=20,
    max_timeout_seconds=600,
    allowed_tools=["tool1", "tool2"],
    blocked_tools=["dangerous_tool"]
)
```

**Validates:**
- ✅ Content filtering (adult, illegal, harmful)
- ✅ Keyword blocking
- ✅ Rate limiting (per user)
- ✅ Timeout constraints
- ✅ Tool allowlist/blocklist

### Cost Policy Features

```python
CostPolicy(
    max_cost_per_request=1.0,
    max_tokens_per_request=100000,
    max_tool_calls=50,
    enable_caching=True,
    prefer_cheaper_models=True
)
```

**Tracks:**
- 💰 Model costs (GPT-4, Claude, GPT-3.5)
- 💰 Tool costs (search, comparison, etc.)
- 💰 Token usage
- 💰 Suggests cheaper alternatives

**Example Costs:**
- GPT-4: $0.03 input / $0.06 output (per 1K tokens)
- GPT-3.5: $0.0005 input / $0.0015 output
- search_web: $0.002 per search
- price_compare_tool: $0.005 per comparison

## 🔧 Usage Patterns

### Pattern 1: Get Profile Config

```python
from agent_core.profiles import SmartBuyerProfile

profile = SmartBuyerProfile()
config = profile.get_config()

# Use config in orchestrator
orchestrator = SmartBuyerOrchestrator(
    llm_client=llm_client,
    config=config
)
```

### Pattern 2: Use Profile Manager

```python
from agent_core.profiles.profile_manager import get_profile_manager

manager = get_profile_manager()
config = manager.get_config("smart_buyer")

# Validate execution
is_valid, violations = manager.validate_execution(
    agent_type="smart_buyer",
    context={...}
)
```

### Pattern 3: Custom Profile

```python
from agent_core.profiles.base_profile import BaseProfile, AgentConfig

class MyProfile(BaseProfile):
    def get_config(self) -> AgentConfig:
        return AgentConfig(
            agent_type="my_agent",
            system_prompt="...",
            allowed_tools=[...],
            max_steps=10
        )

# Register and use
manager.register_profile("my_agent", MyProfile())
config = manager.get_config("my_agent")
```

## 💡 Benefits

### Before (Hard-coded)

```python
class SmartBuyerOrchestrator:
    async def execute(self, query):
        max_steps = 6  # Hard-coded
        tools = ["price_compare"]  # Hard-coded
        prompt = "You are..."  # Hard-coded
        
        # Hard to change, test, or extend
```

### After (Config-driven)

```python
class SmartBuyerOrchestrator:
    def __init__(self, config: AgentConfig):
        self.config = config
        
    async def execute(self, query):
        max_steps = self.config.max_steps
        tools = self.config.allowed_tools
        prompt = self.config.system_prompt
        
        # Easy to change, test, and extend!
```

### Key Advantages

✅ **Separation of Concerns**: Logic separate from configuration
✅ **Easy to Extend**: Add new agents without touching core
✅ **Centralized Control**: All agent behavior in profiles
✅ **Policy Enforcement**: Automatic safety and cost controls
✅ **Testable**: Easy to test different configurations
✅ **Maintainable**: Changes in one place, not scattered
✅ **Customizable**: Override per use case or user

## 🎨 Architecture Integration

```
┌─────────────────────────────────────────────────────────────┐
│                    Request Flow                              │
└─────────────────────────────────────────────────────────────┘

User Query → Router (detect intent)
    ↓
Router.select_flow(Intent.SMART_BUYER)
    ↓
SmartBuyerFlow
    ↓
┌─────────────────────────────────────────────────────────────┐
│            SmartBuyerOrchestrator.__init__()                 │
│                                                              │
│  1. Get profile config:                                      │
│     manager = get_profile_manager()                          │
│     config = manager.get_config("smart_buyer")               │
│                                                              │
│  2. Use config:                                              │
│     self.config = config                                     │
│     self.max_steps = config.max_steps                        │
│     self.allowed_tools = config.allowed_tools                │
│     self.system_prompt = config.system_prompt                │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│            SmartBuyerOrchestrator.execute()                  │
│                                                              │
│  1. Validate policies:                                       │
│     is_valid, violations = manager.validate_execution(...)   │
│                                                              │
│  2. Execute with config constraints:                         │
│     - Use system_prompt for LLM                              │
│     - Filter tools by allowed_tools                          │
│     - Limit steps by max_steps                               │
│     - Track cost vs max_cost_usd                             │
└─────────────────────────────────────────────────────────────┘
    ↓
Response
```

## 📝 Example Integration

### Orchestrator with Profile

```python
from agent_core.profiles.profile_manager import get_profile_manager

class SmartBuyerOrchestrator:
    def __init__(self, llm_client, memory_service, tools_registry):
        # Get profile configuration
        manager = get_profile_manager()
        self.config = manager.get_config("smart_buyer")
        
        # Store dependencies
        self.llm_client = llm_client
        self.memory_service = memory_service
        self.tools_registry = tools_registry
    
    async def execute(self, query, session_id, context=None):
        # Validate with policies
        validation_context = {
            "query": query,
            "user_id": context.get("user_id"),
            "timestamp": time.time(),
            "requested_tools": self.config.allowed_tools,
            "max_tokens": self.config.max_tokens,
        }
        
        manager = get_profile_manager()
        is_valid, violations = manager.validate_execution(
            self.config.agent_type,
            validation_context
        )
        
        if not is_valid:
            return self._handle_violations(violations)
        
        # Execute with profile configuration
        for step in range(self.config.max_steps):
            # Use config.system_prompt
            # Filter by config.allowed_tools
            # Track against config.max_cost_usd
            pass
        
        return result
```

## 🔮 Future Enhancements

1. **Dynamic Profiles**: Load from database/config files
2. **User Preferences**: Per-user customization
3. **A/B Testing**: Test different configurations
4. **Profile Inheritance**: Base + overrides
5. **Real-time Updates**: Hot-reload without restart
6. **Analytics**: Track performance metrics
7. **Auto-tuning**: Learn optimal configurations

## 📚 Files Created

```
✅ profiles/__init__.py
✅ profiles/base_profile.py            (BaseProfile, AgentConfig)
✅ profiles/smart_buyer_profile.py     (SmartBuyerProfile)
✅ profiles/deep_research_profile.py   (DeepResearchProfile)
✅ profiles/chat_profile.py            (ChatProfile)
✅ profiles/profile_manager.py         (ProfileManager)

✅ policy/__init__.py
✅ policy/base_policy.py               (BasePolicy, PolicyViolation)
✅ policy/safety_policy.py             (SafetyPolicy)
✅ policy/cost_policy.py               (CostPolicy)

✅ README_PROFILES.md                  (Comprehensive documentation)
✅ USAGE_EXAMPLE.py                    (Working examples)
```

## ✨ Summary

You now have a **production-ready profile & policy system** that:

🎯 **Makes agents config-driven** - No more hard-coded logic
🔧 **Easy to extend** - Add new agents without touching core
🛡️ **Enforces safety** - Content filters, rate limits, tool restrictions
💰 **Controls costs** - Budget limits, token tracking, model optimization
📊 **Three complete profiles** - Smart Buyer, Deep Research, Chat
🎨 **Clean architecture** - Separation of concerns, testable, maintainable

**This transforms your agent system from hard-coded to highly configurable!** 🚀

