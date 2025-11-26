# Clean Architecture: 4 Layers for AI Agent Systems

**What belongs in each layer?**

Applied specifically to your AI Agent system architecture:
```
Flow → Node → Tool → LLMClient → Memory
```

---

## Table of Contents

1. [Layer 1: Delivery (Presentation)](#layer-1-delivery-presentation)
2. [Layer 2: Application (Use Cases)](#layer-2-application-use-cases)
3. [Layer 3: Domain (Business Logic)](#layer-3-domain-business-logic)
4. [Layer 4: Infrastructure (External I/O)](#layer-4-infrastructure-external-io)
5. [Quick Reference Table](#quick-reference-table)
6. [Dependency Rules](#dependency-rules)
7. [Examples from Your System](#examples-from-your-system)

---

## Layer 1: Delivery (Presentation)

**The outermost layer** - handles HTTP/API communication only

### ✅ **What This Layer Contains:**

- **FastAPI Routers** - HTTP route definitions
- **Endpoints** - GET/POST handlers
- **Request/Response Schemas** - Pydantic models
- **Middleware** - CORS, logging, authentication
- **Exception Handlers** - HTTP error responses
- **Dependency Injection** - `Depends(get_service)`, `Depends(get_llm_client)`

### ❌ **What This Layer Does NOT Contain:**

- ❌ Business logic
- ❌ Flow logic
- ❌ Node logic
- ❌ Tool logic
- ❌ LLM logic
- ❌ Database logic
- ❌ Search logic

### 📌 **Responsibilities:**

1. **Receive** requests (HTTP, WebSocket, gRPC)
2. **Validate** input data
3. **Call** Application layer
4. **Return** responses

### 🎯 **In Your System:**

```python
# apps/api/src/api/routes/smart_buyer.py
@router.post("/smart-buyer", response_model=SmartBuyerResponse)
async def smart_buyer(
    req: SmartBuyerRequest,  # ← Delivery: Request schema
    svc: OrchestratorService = Depends(OrchestratorService),  # ← DI
    tools=Depends(get_tool_registry),
    llm=Depends(get_llm),
):
    # Call Application layer
    result = await svc.run_smart_buyer(
        query=req.query,
        top_k=req.top_k,
        tools=tools,
        llm=llm,
        request_id=rid
    )
    
    # Return formatted response
    return SmartBuyerResponse(**result)  # ← Delivery: Response schema
```

**Files in This Layer:**
```
apps/api/src/api/
├── routes/
│   ├── smart_buyer.py       # HTTP endpoints
│   ├── health.py            # Health checks
│   └── chat.py              # Chat endpoints
├── schemas/
│   ├── smart_buyer.py       # Request/Response models
│   └── chat.py              # Chat models
├── middlewares/
│   ├── cors.py              # CORS handling
│   ├── logging.py           # Request logging
│   └── ratelimit.py         # Rate limiting
├── errors/
│   ├── handlers.py          # Exception handlers
│   └── schemas.py           # Error response schemas
└── http_gateway.py          # Route mounting
```

---

## Layer 2: Application (Use Cases)

**The orchestration layer** - decides what runs when and in what order

### ✅ **What This Layer Contains:**

- **Flows** - `SmartBuyerFlow`, `DeepSearchFlow`, `ChatFlow`
- **Service Layer** - `smart_buyer_service.py`, `orchestrator_service.py`
- **Use Case Logic** - End-to-end workflows
- **Orchestration** - Call nodes in sequence or parallel
- **Planner Selection** - `build_initial_plan()`
- **Node Execution Mapping** - Convert plan to nodes
- **Workflow Manager** - Control execution lifecycle

### ❌ **What This Layer Does NOT Contain:**

- ❌ I/O operations
- ❌ Direct LLM calls
- ❌ Direct database calls
- ❌ OpenSearch calls
- ❌ External API calls
- ❌ Core business logic (scoring rules, decision algorithms)

### 📌 **Responsibilities:**

1. **Orchestrate** the complete workflow from A → Z
2. **Call** Domain Layer for business logic
3. **Use** Infrastructure through interfaces (never direct)
4. **Coordinate** timing, sequencing, and error handling

### 🎯 **In Your System:**

```python
# apps/api/src/router/flows/smart_buyer_flow.py
class SmartBuyerFlow:
    """
    Application Layer - Orchestrates the workflow
    """
    
    async def run(self, state: AgentState, ctx: Dict) -> Dict:
        # Build execution plan
        if not self._built:
            await self.build(state)
        
        # Execute nodes sequentially
        for idx, node in enumerate(self.nodes):
            if state.done:
                break
            
            # Call Domain Layer (node logic)
            state = await node.run(state, ctx)
            
            # Check budget (orchestration concern)
            if self._budget_exceeded(state):
                state.mark_done({...})
                break
        
        return state.output
```

```python
# apps/api/src/services/orchestrator_service.py
class OrchestratorService:
    """
    Application Layer - Service coordination
    """
    
    async def run_smart_buyer(self, *, query, tools, llm, ...):
        # Build state (orchestration)
        state = AgentState(query=query, ...)
        
        # Create flow (orchestration)
        flow = SmartBuyerFlow(tools=tools, llm=llm)
        
        # Execute with timeout (orchestration)
        result = await asyncio.wait_for(
            flow.run(state, ctx),
            timeout=20.0
        )
        
        return result
```

**Files in This Layer:**
```
apps/api/src/
├── router/
│   ├── router_service.py         # Intent routing
│   └── flows/
│       ├── smart_buyer_flow.py   # Smart buyer workflow
│       ├── deep_research_flow.py # Research workflow
│       └── chat_flow.py          # Chat workflow
└── services/
    └── orchestrator_service.py   # Service coordination
```

---

## Layer 3: Domain (Core Business Logic)

**The most important layer** - the heart of your Agent system.  
**"The reason your system exists."**

### ✅ **What This Layer Contains:**

- **Node Logic** - `PriceCompareNode`, `DecisionNode`, `ExplainNode`, `FinalizeNode`
- **AgentState** - State management (facts, logs, memory)
- **Profiles** - `SmartBuyerProfile`, `DeepResearchProfile`
- **Policies** - `CostPolicy`, `SafetyPolicy`
- **Planner Logic** - Build execution plans and strategies
- **Business Rules** - Decision rules, scoring algorithms
- **Value Objects** - Domain entities
- **Domain Services** - Core business operations

### ❌ **What This Layer Does NOT Contain:**

- ❌ HTTP/REST concerns
- ❌ FastAPI dependencies
- ❌ Request/Response schemas
- ❌ Direct LLM API calls
- ❌ Database queries
- ❌ File system access
- ❌ Tool adapters (infrastructure concern)
- ❌ Search engine implementations

### 📌 **Responsibilities:**

1. **Execute reasoning** - The actual AI logic
2. **Make decisions** - `DecisionNode` scoring & ranking
3. **Apply business rules** - Criteria evaluation, constraints
4. **Transform state** - Update `AgentState` based on logic

### 🎯 **In Your System:**

```python
# packages/agent_core/agent_core/nodes/decision.py
class DecisionNode(BaseNode):
    """
    Domain Layer - Core decision logic
    No HTTP, no DB, pure business reasoning
    """
    
    async def _run(self, state: AgentState, ctx: Dict) -> AgentState:
        # Read from state (domain data)
        offers = state.facts.get("offers", [])
        criteria = state.facts.get("criteria", [])
        
        if not offers:
            # Business rule: No offers → empty scoring
            state.facts["scoring"] = _default_scoring()
            return state
        
        # Call tool (via interface, not direct)
        result = await self.tools.call("decision_score", {
            "options": offers,
            "criteria": criteria
        })
        
        # Apply business logic
        scoring = result.get("scoring", {})
        explanation = result.get("explanation", {})
        
        # Update state (domain concern)
        state.facts["scoring"] = scoring
        state.facts["explanation"] = explanation
        
        return state
```

```python
# packages/agent_core/agent_core/models.py
class AgentState(BaseModel):
    """
    Domain Layer - Core state model
    """
    session_id: str
    query: str
    facts: Dict[str, Any]       # Domain data
    logs: List[StepLog]         # Execution history
    budget_tokens: int          # Business constraint
    spent_tokens: int           # Business tracking
    done: bool                  # Domain flag
    output: Optional[Dict]      # Domain result
```

```python
# packages/agent_core/agent_core/profiles/smart_buyer_profile.py
class SmartBuyerProfile(BaseProfile):
    """
    Domain Layer - Business profile configuration
    """
    name = "Smart Buyer"
    goal = "Help user choose best product based on budget & criteria"
    allowed_tools = ["price_compare", "decision_score"]
    max_steps = 8
    budget_tokens = 5000
```

**Files in This Layer:**
```
packages/agent_core/
├── models.py                    # AgentState, StepLog
├── nodes/
│   ├── base.py                  # Base node logic
│   ├── price_compare.py         # Search coordination
│   ├── decision.py              # Decision logic
│   ├── explain.py               # Explanation logic
│   └── finalize.py              # Result assembly
├── profiles/
│   ├── smart_buyer_profile.py   # Business configuration
│   └── base_profile.py          # Profile abstraction
├── policy/
│   ├── cost_policy.py           # Cost rules
│   └── safety_policy.py         # Safety rules
└── planner.py                   # Plan generation logic

packages/decision_core/
├── scoring.py                   # Multi-criteria scoring
└── explainer.py                 # Trade-off analysis
```

---

## Layer 4: Infrastructure (External I/O)

**The I/O layer** - handles all external system communication

### ✅ **What This Layer Contains:**

- **LLM Clients** - OpenAI, Anthropic, Gemini adapters
- **Search Engines** - `PriceCompareEngine`, site scrapers
- **Memory Stores** - SQLite, Redis, PostgreSQL adapters
- **Tool Adapters** - `PriceCompareTool`, `DecisionTool` (I/O parts)
- **HTTP Clients** - `httpx`, `aiohttp` wrappers
- **OpenSearch Adapters** - Vector DB connections
- **Scraper Engines** - Web scraping implementations
- **Cache Adapters** - Redis, memory cache

### ❌ **What This Layer Does NOT Contain:**

- ❌ Flow logic
- ❌ Node reasoning logic
- ❌ Business rules
- ❌ Pydantic schemas (those are Delivery)
- ❌ FastAPI routers (those are Delivery)

### 📌 **Responsibilities:**

1. **Perform I/O operations**
2. **Call external APIs** - OpenAI, Anthropic, Groq
3. **Access databases** - PostgreSQL, Redis, cache
4. **Scrape/search** - E-commerce sites, web search
5. **Return raw data** to Application/Domain layers

### 🎯 **In Your System:**

```python
# packages/llm_client/llm_client/openai_client.py
class OpenAIClient(ILLMClient):
    """
    Infrastructure Layer - External LLM API
    """
    
    def __init__(self, api_key: str, config: LLMClientConfig):
        # Direct dependency on external service
        self._client = AsyncOpenAI(api_key=api_key)
        self.config = config
    
    async def complete(self, *, system: str, user: str, format: str?) -> str:
        # I/O: Call external OpenAI API
        response = await self._client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ]
        )
        
        # Return raw data
        return response.choices[0].message.content or ""
```

```python
# packages/search_core/ecommerce/price_compare.py
class PriceCompareEngine:
    """
    Infrastructure Layer - External search/scraping
    """
    
    async def compare(self, *, query, top_k, sites) -> Dict:
        # I/O: Fan out to external sites
        async def _fetch_site(site):
            adapter = get_site_adapter(site)
            # I/O: HTTP calls to e-commerce sites
            return await adapter.search(query, limit=top_k)
        
        results = await asyncio.gather(*[
            _fetch_site(s) for s in sites
        ])
        
        # Return raw data (normalized)
        return {"offers": results, "metadata": {...}}
```

```python
# packages/memory_core/memory_core/pg_memory.py
class PostgreSQLMemory(IMemory):
    """
    Infrastructure Layer - Database I/O
    """
    
    async def save(self, session_id: str, data: Dict):
        # I/O: Write to PostgreSQL
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO memories (session_id, data) VALUES ($1, $2)",
                session_id, json.dumps(data)
            )
```

**Files in This Layer:**
```
packages/
├── llm_client/
│   ├── openai_client.py         # OpenAI API adapter
│   ├── anthropic_client.py      # Anthropic API adapter
│   └── local_client.py          # Dev/test stub
├── search_core/
│   └── ecommerce/
│       ├── price_compare.py     # Search engine
│       └── sites/
│           ├── shopee.py        # Shopee scraper
│           ├── lazada.py        # Lazada scraper
│           └── tiki.py          # Tiki scraper
├── memory_core/
│   ├── in_memory.py             # RAM storage
│   ├── pg_memory.py             # PostgreSQL storage
│   └── redis_memory.py          # Redis storage
├── tools/
│   ├── price_compare_tool.py    # Tool adapter (I/O part)
│   └── decision_tool.py         # Tool adapter (I/O part)
└── rag/
    ├── indexer.py               # Vector DB indexing
    └── retriever.py             # Vector DB retrieval
```

---

## Quick Summary (Easy to Remember)

```
Delivery        = Receive requests
Application     = Orchestrate workflows
Domain          = Reasoning & business logic
Infrastructure  = Call external world (I/O)
```

---

## Quick Reference Table

### Component-to-Layer Mapping

| Component | Layer | File Path |
|-----------|-------|-----------|
| **Router** | Delivery | `apps/api/src/api/routes/` |
| **Pydantic Schema** | Delivery | `apps/api/src/api/schemas/` |
| **Middleware** | Delivery | `apps/api/src/api/middlewares/` |
| **Flow** (SmartBuyerFlow) | Application | `apps/api/src/router/flows/` |
| **Service** (OrchestratorService) | Application | `apps/api/src/services/` |
| **Planner** | Domain | `packages/agent_core/planner.py` |
| **Nodes** (DecisionNode, etc.) | Domain | `packages/agent_core/nodes/` |
| **Profiles** | Domain | `packages/agent_core/profiles/` |
| **AgentState** | Domain | `packages/agent_core/models.py` |
| **Business Rules** | Domain | `packages/decision_core/` |
| **Tool Adapter** | Infrastructure | `packages/tools/tools/` |
| **Search Engine** | Infrastructure | `packages/search_core/ecommerce/` |
| **LLM Client** | Infrastructure | `packages/llm_client/` |
| **Memory Store** | Infrastructure | `packages/memory_core/` |
| **DB / Redis / OpenSearch** | Infrastructure | `packages/*/` adapters |

---

## Dependency Rules

### The Dependency Rule (CRITICAL)

**Dependencies can only point inward:**

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: Delivery                                           │
│   ↓ can depend on                                           │
├─────────────────────────────────────────────────────────────┤
│ Layer 2: Application                                        │
│   ↓ can depend on                                           │
├─────────────────────────────────────────────────────────────┤
│ Layer 3: Domain                                             │
│   ↓ can depend on (through interfaces)                      │
├─────────────────────────────────────────────────────────────┤
│ Layer 4: Infrastructure                                     │
│   (implements interfaces from Domain)                       │
└─────────────────────────────────────────────────────────────┘
```

### ✅ **Valid Dependencies:**

```python
# ✅ Delivery → Application
from services.orchestrator_service import OrchestratorService

# ✅ Application → Domain
from agent_core.nodes.decision import DecisionNode

# ✅ Domain → Infrastructure (through interface)
class DecisionNode:
    def __init__(self, tools: IToolRegistry):  # Interface
        self.tools = tools
```

### ❌ **Invalid Dependencies:**

```python
# ❌ Domain → Delivery
from api.routes.smart_buyer import SmartBuyerRequest  # NO!

# ❌ Infrastructure → Domain
from agent_core.models import AgentState  # NO!
# (Infrastructure should only implement interfaces)

# ❌ Domain → Concrete Infrastructure
from llm_client.openai_client import OpenAIClient  # NO!
# Use interface: ILLMClient instead
```

### **Dependency Inversion Principle**

```python
# ✅ Good: Domain depends on interface
class DecisionNode(BaseNode):
    def __init__(self, tools: IToolRegistry):  # ← Interface
        self.tools = tools

# Infrastructure implements interface
class ToolRegistry(IToolRegistry):
    async def call(self, name: str, payload: dict):
        ...

# Delivery injects concrete implementation
@router.post("/smart-buyer")
async def smart_buyer(
    tools=Depends(get_tool_registry)  # ← Concrete injected here
):
    node = DecisionNode(tools=tools)
```

---

## Examples from Your System

### Example 1: Complete Request Flow Through Layers

```python
# LAYER 1: Delivery
@router.post("/smart-buyer")  # ← HTTP endpoint
async def smart_buyer(req: SmartBuyerRequest):  # ← Pydantic validation
    # Inject dependencies
    svc = OrchestratorService()
    tools = get_tool_registry()
    llm = get_llm()
    
    # Call Application layer
    result = await svc.run_smart_buyer(...)
    
    # Return HTTP response
    return SmartBuyerResponse(**result)

# --------------------------------

# LAYER 2: Application
class OrchestratorService:
    async def run_smart_buyer(self, *, query, tools, llm):
        # Build state
        state = AgentState(query=query)
        
        # Create and execute flow
        flow = SmartBuyerFlow(tools=tools, llm=llm)
        result = await flow.run(state, ctx)
        
        return result

class SmartBuyerFlow:
    async def run(self, state, ctx):
        # Orchestrate nodes
        for node in self.nodes:
            state = await node.run(state, ctx)
        return state.output

# --------------------------------

# LAYER 3: Domain
class DecisionNode(BaseNode):
    async def _run(self, state, ctx):
        offers = state.facts["offers"]
        
        # Call tool through interface
        result = await self.tools.call("decision_score", {
            "options": offers,
            "criteria": state.facts.get("criteria")
        })
        
        # Apply business logic
        state.facts["scoring"] = result["scoring"]
        return state

# --------------------------------

# LAYER 4: Infrastructure
class PriceCompareTool:
    async def call(self, payload):
        # I/O: Call search engine
        result = await self.engine.compare(
            query=payload["query"],
            sites=["shopee", "lazada"]
        )
        return result

class PriceCompareEngine:
    async def compare(self, *, query, sites):
        # I/O: HTTP calls to external sites
        async def _fetch(site):
            adapter = get_site_adapter(site)
            return await adapter.search(query)  # ← External I/O
        
        results = await asyncio.gather(*[_fetch(s) for s in sites])
        return {"offers": results}
```

---

### Example 2: Why Layering Matters

#### **Without Clean Architecture:**
```python
# ❌ BAD: Everything mixed together
@router.post("/smart-buyer")
async def smart_buyer(req):
    # HTTP + Business logic + I/O all in one place
    openai_client = OpenAI(api_key="...")  # I/O
    
    offers = []
    for site in ["shopee", "lazada"]:
        response = requests.get(f"https://{site}.vn/search?q={req.query}")  # I/O
        offers.extend(response.json())
    
    # Business logic mixed with endpoint
    scores = []
    for offer in offers:
        score = offer["price"] * 0.5 + offer["rating"] * 0.5
        scores.append(score)
    
    best = max(scores)
    
    # More business logic
    explanation = f"Best option is {best}"
    
    return {"offers": offers, "explanation": explanation}

# Problems:
# - Can't test business logic separately
# - Can't swap LLM provider
# - Can't reuse logic in other flows
# - Hard to mock external calls
# - No separation of concerns
```

#### **With Clean Architecture:**
```python
# ✅ GOOD: Separated layers

# LAYER 1: Delivery (HTTP only)
@router.post("/smart-buyer")
async def smart_buyer(req: SmartBuyerRequest, svc=Depends(get_service)):
    result = await svc.run_smart_buyer(req.query, req.top_k)
    return SmartBuyerResponse(**result)

# LAYER 2: Application (Orchestration)
class OrchestratorService:
    async def run_smart_buyer(self, query, top_k):
        state = AgentState(query=query)
        flow = SmartBuyerFlow(tools=self.tools, llm=self.llm)
        return await flow.run(state, {"top_k": top_k})

# LAYER 3: Domain (Business logic)
class DecisionNode(BaseNode):
    async def _run(self, state, ctx):
        offers = state.facts["offers"]
        scoring = self._calculate_scores(offers)  # Pure business logic
        state.facts["scoring"] = scoring
        return state

# LAYER 4: Infrastructure (I/O)
class PriceCompareTool:
    async def call(self, payload):
        return await self.engine.compare(query=payload["query"])

# Benefits:
# ✅ Each layer testable independently
# ✅ Easy to swap implementations
# ✅ Business logic reusable
# ✅ Clear separation of concerns
# ✅ Easy to mock external dependencies
```

---

## Architectural Diagrams

### Data Flow Through Layers

```
┌───────────────────────────────────────────────────────────┐
│                    LAYER 1: Delivery                      │
│  HTTP Request → Validation → Dependency Injection         │
└─────────────────────────┬─────────────────────────────────┘
                          │ Calls
                          ▼
┌───────────────────────────────────────────────────────────┐
│                  LAYER 2: Application                     │
│  Build State → Create Flow → Execute Nodes → Normalize   │
└─────────────────────────┬─────────────────────────────────┘
                          │ Uses
                          ▼
┌───────────────────────────────────────────────────────────┐
│                    LAYER 3: Domain                        │
│  Node Logic → Business Rules → State Transformation      │
└─────────────────────────┬─────────────────────────────────┘
                          │ Calls (via interfaces)
                          ▼
┌───────────────────────────────────────────────────────────┐
│                LAYER 4: Infrastructure                    │
│  LLM API → Search Engine → Database → Cache              │
└───────────────────────────────────────────────────────────┘
```

### Dependency Flow

```
┌────────────────────────────────────────────────────────────┐
│  Outer Layers depend on Inner Layers                       │
│  Inner Layers DON'T know about Outer Layers               │
└────────────────────────────────────────────────────────────┘

    Delivery
       ↓ depends on
    Application
       ↓ depends on
    Domain  ←──────┐
       ↓ interface │ implements
    Infrastructure ─┘
```

---

## Benefits of This Architecture

### 1. **Testability**
```python
# Test Domain layer without I/O
def test_decision_node():
    mock_tools = MockToolRegistry()
    node = DecisionNode(tools=mock_tools)
    state = AgentState(query="test")
    result = await node._run(state, {})
    assert result.facts["scoring"] is not None
```

### 2. **Flexibility**
```python
# Swap OpenAI for Anthropic - no domain changes
# Just change in dependency provider (Delivery layer)
def get_llm():
    return AnthropicClient()  # Changed here only
```

### 3. **Maintainability**
```python
# Each layer has clear responsibility
# Easy to find and fix bugs
# - HTTP issue? → Check Delivery
# - Workflow issue? → Check Application
# - Logic issue? → Check Domain
# - API issue? → Check Infrastructure
```

### 4. **Scalability**
```python
# Can replace infrastructure without touching business logic
# - SQLite → PostgreSQL (no domain changes)
# - Mock adapters → Real scrapers (no flow changes)
# - Single server → Microservices (layer boundaries preserved)
```

---

## Common Mistakes to Avoid

### ❌ **Mistake 1: Business Logic in Delivery**
```python
# BAD: Scoring logic in HTTP handler
@router.post("/smart-buyer")
async def smart_buyer(req):
    offers = await fetch_offers()
    
    # ❌ Business logic in Delivery layer!
    scores = []
    for offer in offers:
        score = offer["price"] * 0.4 + offer["rating"] * 0.6
        scores.append(score)
    
    return {"scores": scores}
```

### ❌ **Mistake 2: HTTP Calls in Domain**
```python
# BAD: Node making direct HTTP calls
class PriceCompareNode(BaseNode):
    async def _run(self, state, ctx):
        # ❌ Direct HTTP in Domain layer!
        response = await httpx.get("https://shopee.vn/api/search")
        offers = response.json()
        state.facts["offers"] = offers
        return state
```

### ❌ **Mistake 3: Domain Logic in Infrastructure**
```python
# BAD: Business rules in tool
class PriceCompareTool:
    async def call(self, payload):
        offers = await self.engine.compare(...)
        
        # ❌ Business logic in Infrastructure!
        # This should be in Domain layer
        best = max(offers, key=lambda x: x["rating"])
        
        return {"offers": offers, "best": best}
```

### ✅ **Correct Way:**
```python
# Delivery: HTTP only
@router.post("/smart-buyer")
async def smart_buyer(req, svc=Depends(get_service)):
    return await svc.run_smart_buyer(req.query)

# Application: Orchestration
class OrchestratorService:
    async def run_smart_buyer(self, query):
        flow = SmartBuyerFlow(...)
        return await flow.run(state, ctx)

# Domain: Business logic
class DecisionNode(BaseNode):
    async def _run(self, state, ctx):
        offers = state.facts["offers"]
        best = self._find_best(offers)  # ← Business logic here
        return state

# Infrastructure: I/O only
class PriceCompareTool:
    async def call(self, payload):
        return await self.engine.compare(...)  # ← Just I/O
```

---

## Visual Layer Boundaries

```
┌──────────────────────────────────────────────────────────────┐
│                    Your AI Agent System                       │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Delivery: FastAPI Routes, Schemas, Middleware      │    │
│  │ Files: apps/api/src/api/                           │    │
│  └─────────────────────┬──────────────────────────────┘    │
│                        │ calls                              │
│  ┌─────────────────────▼──────────────────────────────┐    │
│  │ Application: Flows, Services, Orchestration        │    │
│  │ Files: apps/api/src/router/, services/             │    │
│  └─────────────────────┬──────────────────────────────┘    │
│                        │ uses                               │
│  ┌─────────────────────▼──────────────────────────────┐    │
│  │ Domain: Nodes, State, Profiles, Business Rules     │    │
│  │ Files: packages/agent_core/, decision_core/        │    │
│  └─────────────────────┬──────────────────────────────┘    │
│                        │ calls (via interfaces)             │
│  ┌─────────────────────▼──────────────────────────────┐    │
│  │ Infrastructure: LLM, Tools, Search, Memory, DB     │    │
│  │ Files: packages/llm_client/, search_core/, tools/  │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Summary

### Why Clean Architecture for AI Agents?

| Benefit | Impact |
|---------|--------|
| **Separation of Concerns** | Each layer has single responsibility |
| **Testability** | Mock outer layers, test inner logic |
| **Flexibility** | Swap implementations without breaking system |
| **Maintainability** | Clear boundaries make debugging easier |
| **Scalability** | Add features without touching core |
| **Team Collaboration** | Different teams can work on different layers |

### The Golden Rules

1. **Dependencies point inward only**
2. **Inner layers don't know about outer layers**
3. **Domain layer is pure business logic**
4. **Infrastructure implements interfaces from Domain**
5. **Delivery layer is thin - just HTTP/validation**

### Layer Checklist

When adding new code, ask:

- [ ] Does this handle HTTP? → **Delivery**
- [ ] Does this orchestrate multiple steps? → **Application**
- [ ] Does this contain business rules? → **Domain**
- [ ] Does this call external services? → **Infrastructure**

---

## Related Documentation

- **Architecture**: `ARCHITECTURE.md` - Overall system design
- **Data Flow**: `DATAFLOW.md` - Request data transformations
- **Behavior**: `BEHAVIOR_ARCHITECTURE.md` - Runtime behaviors
- **Core Concepts**: `12_concepts.md` - Fundamental principles
- **Run Guide**: `RUN_GUIDE.md` - Setup and operations

---

**Last Updated**: November 21, 2025  
**For**: Production-Grade AI Agent Architecture  
**Pattern**: Clean Architecture (4-Layer Model)

---

## 5-Second Layer Classification Rules

**To identify which layer a file belongs to, follow these 5 golden rules.**

Applied directly to your project structure, this will clearly show:
- ✅ Which files belong to **Delivery Layer**
- ✅ Which files belong to **Application Layer**
- ✅ Which files belong to **Domain Layer**
- ✅ Which files belong to **Infrastructure Layer**
- ⚠️ Which files are in the wrong location

---

### ✅ **5-SECOND RULES TO DETERMINE LAYER FOR ANY FILE**

#### **Rule 1**: File contains **orchestration/flow logic** → **Application Layer**

**Examples:**
- `smart_buyer_service.py`
- `orchestrator_service.py`
- `tool_service.py`
- `*_flow.py`

**Why**: Coordinates between components but doesn't contain business rules

---

#### **Rule 2**: File contains **business logic** (Node, Profile, Planner, AgentState) → **Domain Layer**

**Examples:**
- `agent_core/nodes/...` (PriceCompareNode, DecisionNode)
- `agent_core/models.py` (AgentState)
- `agent_core/planner.py` (Plan generation)
- `agent_core/profiles/...` (SmartBuyerProfile)
- `decision_core/scoring.py` (Multi-criteria algorithms)

**Why**: Pure business reasoning, no external dependencies

---

#### **Rule 3**: File makes **external calls** (API, DB, LLM, Search) → **Infrastructure Layer**

**Examples:**
- `llm_client/...` (OpenAI, Anthropic APIs)
- `search_core/...` (Search engines, scrapers)
- `memory_core/...` (Database, Redis)
- `tools/...` (External tool adapters)
- `nini_search/*.py` (Search implementations)

**Why**: Performs I/O operations

---

#### **Rule 4**: File is **HTTP/FastAPI related** → **Delivery Layer**

**Examples:**
- `/apps/api/src/main.py` (FastAPI app)
- `/apps/api/src/routes/...` (HTTP endpoints)
- `middleware/...` (CORS, auth, logging)
- `schemas/...` (Request/Response models)
- API endpoints

**Why**: Handles HTTP protocol concerns

---

#### **Rule 5**: File name contains **adapter, client, or engine** → **99% Infrastructure**

**Keywords to look for:**
- `*_client.py` → Infrastructure (external service client)
- `*_adapter.py` → Infrastructure (external system adapter)
- `*_engine.py` → Infrastructure (processing engine with I/O)

**Why**: These patterns typically indicate external system interaction

---
## Applied to Your Project Structure

### Analysis of Each Folder

---

#### **1. `/apps/api/src/` → DELIVERY LAYER**

**Category**: Presentation Layer

**Contains:**
- Routers
- Main API entry point
- FastAPI dependency injection
- API-level coordination

**File Classification:**
```
apps/
  api/
    src/
      api/
        routes/
          smart_buyer.py         ✔ Delivery (HTTP endpoint)
          health.py              ✔ Delivery (HTTP endpoint)
        schemas/
          smart_buyer.py         ✔ Delivery (Request/Response)
        middlewares/
          cors.py                ✔ Delivery (HTTP middleware)
          logging.py             ✔ Delivery (HTTP middleware)
        http_gateway.py          ✔ Delivery (Route mounting)
      
      services/
        orchestrator_service.py  ⚠️ Application (correct layer)
        smart_buyer_service.py   ⚠️ Application (correct layer)
        tool_service.py          ⚠️ Application (correct layer)
      
      router/
        router_service.py        ⚠️ Application (correct layer)
        flows/
          smart_buyer_flow.py    ⚠️ Application (correct layer)
      
      main.py                    ✔ Delivery (FastAPI app initialization)
```

**📌 Note:**  
Services and flows technically belong to **Application Layer**, but placing them in `/apps/api/src/services/` and `/router/` is acceptable for small monorepos. The important thing is they don't mix with HTTP concerns.

---

#### **2. `/packages/agent_core/` → DOMAIN LAYER**

**The heart of your AI Agent system** - contains all business logic

**Folder Structure:**
```
packages/agent_core/agent_core/
    nodes/
        base.py                ✔ Domain (Node abstraction)
        price_compare.py       ✔ Domain (Business coordination)
        decision.py            ✔ Domain (Decision logic)
        explain.py             ✔ Domain (Explanation logic)
        finalize.py            ✔ Domain (Result assembly)
    
    policy/
        base_policy.py         ✔ Domain (Policy rules)
        cost_policy.py         ✔ Domain (Budget rules)
        safety_policy.py       ✔ Domain (Safety rules)
    
    profiles/
        smart_buyer_profile.py ✔ Domain (Business configuration)
        base_profile.py        ✔ Domain (Profile abstraction)
    
    runtime/
        executor.py            ✔ Domain (Execution logic)
        observer.py            ✔ Domain (Observation logic)
        reflector.py           ✔ Domain (Reflection logic)
        refiner.py             ✔ Domain (Refinement logic)
    
    interfaces.py              ✔ Domain (Abstractions)
    models.py                  ✔ Domain (AgentState, StepLog)
    planner.py                 ✔ Domain (Planning logic)
```

**➡ Everything here belongs to Domain Layer**

---

#### **3. `/packages/search_core/` → INFRASTRUCTURE LAYER**

**Category**: Search engine = I/O + external API

```
packages/search_core/
    ecommerce/
        price_compare.py       ✔ Infrastructure (Engine with I/O)
        sites/
            shopee.py          ✔ Infrastructure (External scraping)
            lazada.py          ✔ Infrastructure (External scraping)
            tiki.py            ✔ Infrastructure (External scraping)
    query_understanding.py     ✔ Infrastructure (NLP processing)
    ranking.py                 ✔ Infrastructure (Search ranking)
```

---

#### **4. `/packages/llm_client/` → INFRASTRUCTURE LAYER**

**Category**: LLM = external services (OpenAI, Anthropic, etc.)

```
packages/llm_client/
    openai_client.py           ✔ Infrastructure (External API)
    anthropic_client.py        ✔ Infrastructure (External API)
    local_client.py            ✔ Infrastructure (Mock/stub)
    base.py                    ✔ Infrastructure (Interface)
```

---

#### **5. `/packages/memory_core/` → INFRASTRUCTURE LAYER**

**Category**: Memory store = Database, persistent I/O

```
packages/memory_core/
    in_memory.py               ✔ Infrastructure (RAM storage)
    pg_memory.py               ✔ Infrastructure (PostgreSQL I/O)
    redis_memory.py            ✔ Infrastructure (Redis I/O)
    base.py                    ✔ Infrastructure (Interface)
```

---

#### **6. `/packages/tools/` → INFRASTRUCTURE LAYER**

**Category**: Tools = adapters calling search, payment, scraping, etc.

```
packages/tools/
    registry.py                ✔ Infrastructure (Tool coordinator)
    price_compare_tool.py      ✔ Infrastructure (I/O adapter)
    decision_tool.py           ⚠️ Mixed (has some domain logic)
    http_request.py            ✔ Infrastructure (HTTP I/O)
    search_web.py              ✔ Infrastructure (Web search I/O)
```

---

#### **7. `/packages/decision_core/` + `/rag/` + `/shared/`**

**Classification depends on content:**

**decision_core:**
```
packages/decision_core/
    scoring.py                 ✔ Domain (Business algorithm)
    explainer.py               ✔ Domain (Business reasoning)
    config.py                  ✔ Domain (Business configuration)
```
**Why Domain?** Pure mathematical/logical algorithms, no I/O

**rag:**
```
packages/rag/
    indexer.py                 ✔ Infrastructure (Vector DB I/O)
    retriever.py               ✔ Infrastructure (Vector DB I/O)
```
**Why Infrastructure?** Performs database operations

**shared:**
```
packages/shared/
    config.py                  ✔ Infrastructure (Configuration)
    errors.py                  ✔ Domain (Business exceptions)
    logging.py                 ✔ Infrastructure (Logging utilities)
    types.py                   ✔ Domain (Value objects)
```
**Why Mixed?** Contains both domain concepts and infrastructure utilities

---

## Quick Layer Summary for Your Project

| Layer | Folders | Key Indicator |
|-------|---------|---------------|
| **Delivery** | `apps/api/src/api/` (routes, schemas, middlewares) | HTTP, FastAPI, Pydantic schemas |
| **Application** | `apps/api/src/services/`, `apps/api/src/router/flows/` | Orchestration, flows, use cases |
| **Domain** | `packages/agent_core/`, `packages/decision_core/` | Business logic, reasoning, rules |
| **Infrastructure** | `llm_client/`, `memory_core/`, `search_core/`, `tools/`, `rag/` | I/O, external APIs, databases |

---

## 🔥 BONUS: 5-Second Self-Check

**Answer YES/NO to these questions:**

### **Question 1**: Does this file interact with API/DB/LLM?
```
→ YES → Infrastructure
→ NO → Continue to next question
```

**Examples:**
- ✅ `openai_client.py` → Calls OpenAI API → **Infrastructure**
- ✅ `pg_memory.py` → Calls PostgreSQL → **Infrastructure**
- ✅ `price_compare_tool.py` → Calls search engine → **Infrastructure**

---

### **Question 2**: Does this file orchestrate logic (not pure business)?
```
→ YES → Application
→ NO → Continue to next question
```

**Examples:**
- ✅ `smart_buyer_flow.py` → Orchestrates nodes → **Application**
- ✅ `orchestrator_service.py` → Coordinates flow → **Application**
- ❌ `decision.py` → Business logic → **Not Application**

---

### **Question 3**: Is this file core business logic?
```
→ YES → Domain
→ NO → Continue to next question
```

**Examples:**
- ✅ `decision_node.py` → Scoring logic → **Domain**
- ✅ `smart_buyer_profile.py` → Business rules → **Domain**
- ✅ `planner.py` → Planning logic → **Domain**
- ❌ `smart_buyer_service.py` → Orchestration → **Not Domain**

---

### **Question 4**: Is this file related to HTTP/FastAPI?
```
→ YES → Delivery
→ NO → Check if miscategorized
```

**Examples:**
- ✅ `smart_buyer.py` (routes) → HTTP endpoint → **Delivery**
- ✅ `cors.py` (middleware) → HTTP concern → **Delivery**
- ✅ `SmartBuyerRequest` (schema) → HTTP model → **Delivery**

---

## Decision Tree (Visual)

```
                Start
                  │
                  ▼
          Does it handle HTTP?
          /                \
        YES                 NO
         │                  │
         ▼                  ▼
    DELIVERY      Does it call external systems?
                  /                    \
                YES                     NO
                 │                      │
                 ▼                      ▼
          INFRASTRUCTURE    Does it orchestrate?
                           /              \
                         YES               NO
                          │                │
                          ▼                ▼
                    APPLICATION        DOMAIN
```

---

## Complete Project Layer Map

### Your Actual Directory Structure

```
quantumx-ai/
├── apps/
│   └── api/
│       └── src/
│           ├── api/                    # DELIVERY
│           │   ├── routes/             # HTTP endpoints
│           │   ├── schemas/            # Request/Response models
│           │   ├── middlewares/        # HTTP middleware
│           │   ├── errors/             # HTTP error handlers
│           │   └── http_gateway.py     # Route mounting
│           │
│           ├── services/               # APPLICATION
│           │   ├── orchestrator_service.py
│           │   └── smart_buyer_service.py
│           │
│           ├── router/                 # APPLICATION
│           │   ├── router_service.py   # Intent routing
│           │   └── flows/
│           │       ├── smart_buyer_flow.py
│           │       ├── deep_research_flow.py
│           │       └── chat_flow.py
│           │
│           ├── config/                 # INFRASTRUCTURE
│           │   └── settings.py         # Configuration
│           │
│           ├── dependencies/           # DELIVERY
│           │   ├── llm_provider.py     # DI provider
│           │   ├── tools_provider.py   # DI provider
│           │   └── memory_provider.py  # DI provider
│           │
│           └── main.py                 # DELIVERY
│
└── packages/
    ├── agent_core/                     # DOMAIN
    │   ├── nodes/                      # Business logic
    │   ├── profiles/                   # Business rules
    │   ├── policy/                     # Business constraints
    │   ├── runtime/                    # Execution logic
    │   ├── models.py                   # Core models
    │   ├── planner.py                  # Planning logic
    │   └── interfaces.py               # Abstractions
    │
    ├── decision_core/                  # DOMAIN
    │   ├── scoring.py                  # Business algorithms
    │   ├── explainer.py                # Business reasoning
    │   └── config.py                   # Business config
    │
    ├── llm_client/                     # INFRASTRUCTURE
    │   ├── openai_client.py            # External API
    │   ├── anthropic_client.py         # External API
    │   └── local_client.py             # Mock
    │
    ├── search_core/                    # INFRASTRUCTURE
    │   ├── ecommerce/
    │   │   ├── price_compare.py        # Search engine
    │   │   └── sites/                  # Site scrapers
    │   ├── query_understanding.py      # NLP processing
    │   └── ranking.py                  # Search ranking
    │
    ├── memory_core/                    # INFRASTRUCTURE
    │   ├── in_memory.py                # RAM storage
    │   ├── pg_memory.py                # DB storage
    │   └── redis_memory.py             # Cache storage
    │
    ├── tools/                          # INFRASTRUCTURE
    │   ├── registry.py                 # Tool coordinator
    │   ├── price_compare_tool.py       # I/O adapter
    │   ├── decision_tool.py            # I/O adapter
    │   └── http_request.py             # HTTP utility
    │
    ├── rag/                            # INFRASTRUCTURE
    │   ├── indexer.py                  # Vector DB I/O
    │   └── retriever.py                # Vector DB I/O
    │
    └── shared/                         # MIXED
        ├── config.py                   # Infrastructure
        ├── errors.py                   # Domain
        ├── logging.py                  # Infrastructure
        └── types.py                    # Domain
```

---

## Validation Checklist

Use this to audit your project:

### For Each File, Ask:

1. **[ ]** Does it import `fastapi`, `Request`, `Response`?  
   → If YES → Should be in **Delivery**

2. **[ ]** Does it import `httpx`, `requests`, `openai`, `anthropic`?  
   → If YES → Should be in **Infrastructure**

3. **[ ]** Does it import and use `AgentState`, `BaseNode`?  
   → If YES → Probably **Domain**

4. **[ ]** Does it call `flow.run()` or orchestrate nodes?  
   → If YES → Should be in **Application**

5. **[ ]** Does it have `.env` config, database connections, or API clients?  
   → If YES → Should be in **Infrastructure**

---

## Conclusion

### Summary Table

| Layer | What Goes Here | Your Folders |
|-------|----------------|--------------|
| **Delivery** | HTTP, validation, DI | `apps/api/src/api/`, `main.py`, `dependencies/` |
| **Application** | Flows, services, orchestration | `services/`, `router/flows/` |
| **Domain** | Nodes, profiles, business rules | `packages/agent_core/`, `decision_core/` |
| **Infrastructure** | LLM, DB, search, tools | `llm_client/`, `search_core/`, `memory_core/`, `tools/`, `rag/` |

### The Golden Question

**"Where does this file belong?"**

Ask yourself:
1. HTTP stuff? → **Delivery**
2. Workflow coordination? → **Application**
3. Business rules? → **Domain**
4. External calls? → **Infrastructure**

---

**Your architecture follows Clean Architecture principles correctly!** ✅

---

**Last Updated**: November 21, 2025  
**Reference**: Robert C. Martin's Clean Architecture  
**Applied To**: AI Agent Multi-Step Reasoning Systems