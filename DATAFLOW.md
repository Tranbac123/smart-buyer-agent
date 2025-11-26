# Data Flow Architecture

## High-Level Request Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              Client / Frontend                               │
└───────────────┬──────────────────────────────────────────────────────────────┘
                │ 1) POST /v1/smart-buyer
                │    SmartBuyerRequest
                │    - query: str
                │    - top_k: conint(1..20)
                │    - prefs: PreferencesIn?
                │    - criteria: [CriterionIn]?
                ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                           Orchestrator / Planner                             │
│  - Validate SmartBuyerRequest                                                │
│  - Normalize criteria & preferences (apply defaults)                         │
└───────────────┬──────────────────────────────────────────────────────────────┘
                │ 2) Retrieve(query, prefs, top_k)
                ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                            Price Compare Node                                │
│  Input: query, prefs, top_k                                                  │
│  Output: offers: List[OfferOut]                                              │
│    OfferOut = {site, title, price, url, currency, rating?, shop_name?, tags?}│
└───────────────┬──────────────────────────────────────────────────────────────┘
                │ 3) Score(offers, criteria, prefs)
                ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                              Decision Node                                   │
│  - Normalize features based on prefs/criteria                                │
│  - Calculate score for each option                                           │
│  Output: ScoringOut                                                          │
│    - best: str?           (best option_id)                                   │
│    - confidence: float    (0..1)                                             │
│    - option_scores: [OptionScoreOut]                                         │
│        OptionScoreOut = {option_id, total_score, rank}                       │
└───────────────┬──────────────────────────────────────────────────────────────┘
                │ 4) Explain(offers, scoring, criteria, prefs)
                ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                               Explain Node                                   │
│  Output: ExplanationOut                                                      │
│   - winner: str?                 (name/summary of best option)               │
│   - confidence: float            (inherited or refined from scoring)         │
│   - best_by_criterion: {criterion_name: option_id/label}                     │
│   - tradeoffs: [str]             (trade-offs between options)                │
│   - per_option: [ {option_id, reasoning per criterion...} ]                  │
│   - summary: str                 (natural language summary for user)         │
└───────────────┬──────────────────────────────────────────────────────────────┘
                │ 5) Assemble response
                ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                              SmartBuyerResponse                              │
│  - request_id: str                                                           │
│  - query: str                                                                │
│  - latency_ms: int                                                           │
│  - offers: List[OfferOut]                                                    │
│  - scoring: ScoringOut                                                       │
│  - explanation: ExplanationOut                                               │
│  - metadata: Dict[str, Any]                                                  │
└──────────────────────────────────────────────────────────────────────────────┘
```


---

## System Overview

**Complete Flow**: 
```
Client → FastAPI API → Service → Orchestrator → Smart-Buyer Agent + Tools → Decision → HTTP Response
```

**Architecture Layers** (separated for clarity):

---

## Layer 1: API Layer (FastAPI Endpoint)

### Route Handler

```python
@router.post("/smart-buyer")
async def smart_buyer(req: SmartBuyerRequest):
    result = await service.run_smart_buyer(
        query=req.query,
        top_k=req.top_k,
        prefs=req.prefs.model_dump() if req.prefs else None,
        criteria=[c.model_dump() for c in req.criteria] if req.criteria else None,
        tools=tools,
        llm=llm,
        http=http,
        request_id=rid,
    )
    return result
```

### Responsibilities

1. **Receive JSON from client**
2. **Validate input** using `SmartBuyerRequest` (Pydantic):
   - Validate field types
   - Normalize data structures
3. **Map input to service layer**:
   - `query`: User search query
   - `top_k`: Number of results to return
   - `prefs`: User preferences (budget, required tags, etc.)
   - `criteria`: Decision criteria (price, quality, warranty, etc.)
4. **Inject infrastructure dependencies**:
   - `llm`: LLM client (OpenAI / Anthropic / local)
   - `http`: HTTP client for external requests
   - `tools`: Tool registry (PriceCompareTool, DecisionTool, etc.)
   - `request_id`: For tracking and logging

---

## Layer 2: Service Layer (run_smart_buyer)

The service layer is the **application service** - it handles business logic without HTTP concerns.

### Implementation

```python
class SmartBuyerService:
    async def run_smart_buyer(...):
        ctx = {
            "query": query,
            "top_k": top_k,
            "prefs": prefs,
            "criteria": criteria,
            "request_id": request_id,
            ...
        }

        # Call orchestrator
        result = await orchestrator.run_smart_buyer_flow(
            ctx=ctx,
            tools=tools,
            llm=llm,
            http=http,
        )
        return result
```

### Responsibilities

1. **Package everything** into initial context for orchestrator
2. **Delegate decision-making** to orchestrator + agent:
   - Doesn't decide which tools to use
   - Doesn't create LLM prompts
   - Pure coordination layer

---

## Layer 3: Orchestrator (LangGraph-Style Workflow Engine)

The orchestrator is the **coordination layer** that manages the multi-step reasoning pipeline.

### Inputs

- `ctx`: Context dictionary (query, prefs, criteria, request_id)
- `tools`: Tool registry
- `llm`: LLM client
- `http`: HTTP client (optional)

### Creates Shared State

```python
state = AgentState(
    query=query,
    facts={
        "prefs": prefs,
        "criteria": criteria,
        # Will be populated by nodes:
        # "offers": [...],
        # "scoring": {...},
        # "explanation": {...}
    },
    budget_tokens=5000,
    spent_tokens=0,
    done=False
)
```

### Multi-Step Pipeline (Graph Execution)

#### **Step 1: Prepare**
- Normalize query, preferences, criteria
- Create initial prompt context for agent

#### **Step 2: Plan (LLM-Driven)**
Agent analyzes:
- Query intent (compare specific products? find best in category?)
- Required information
- Available tools and data sources

Decision points:
- Does the query need search/price comparison?
- How many results are needed?
- Which sites to prioritize (Shopee, Lazada, Tiki)?

**Output**: Execution plan (list of steps + tools to call)

#### **Step 3: Execute Tools**
Orchestrator reads the plan and:
- Calls corresponding tools (price_compare, info_lookup, etc.)
- Collects offers, raw_results, evidence
- Stores in `state.facts["offers"]`

#### **Step 4: Score & Decide**
Calls `DecisionTool` / Smart-Buyer logic to:
- Calculate score for each option based on criteria
- Find the winner
- Explain trade-offs

**Output**: 
```python
state.facts["scoring"] = {
    "best": "option_id",
    "confidence": 0.85,
    "option_scores": [...]
}
```

#### **Step 5: Compose Response (LLM)**
Uses LLM to rewrite results into natural explanation:
- Why option A is recommended
- When to choose option B instead
- Drawbacks and warnings to consider

**Output**:
```python
state.facts["explanation"] = {
    "summary": "Natural language explanation...",
    "tradeoffs": [...],
    "warnings": [...]
}
```

#### **Step 6: Finalize**
Normalize output to standard schema:

```python
{
  "offers": [...],
  "scoring": {...},
  "explanation": {...},
  "metadata": {...}
}
```

---

## Layer 4: Smart-Buyer Agent (Profile-Based Configuration)

The agent is **not separate code**, but rather a **profile configuration** for the orchestrator.

### Agent Profile (`smart_buyer_profile.py`)

```python
SmartBuyerProfile:
    name: "Smart Buyer"
    goal: "Help user choose the best product based on budget & criteria"
    allowed_tools: ["price_compare", "decision_score"]
    style: "Careful, explain trade-offs clearly"
    output_schema: {offers, scoring, explanation}
    max_steps: 8
    budget_tokens: 5000
```

### Agent Responsibilities

1. **Read inputs**: query + prefs + criteria
2. **Plan tool usage**: Which tools to use, in what order
3. **Make decisions** based on tool results (evidence-based, not invented)
4. **Generate explanations** with clear reasoning

---

## Layer 5: Tools (PriceCompareTool + DecisionTool)

### 5.1 PriceCompareTool

Adapter to the domain engine `PriceCompareEngine` in `search_core.ecommerce.price_compare`.

#### Input
```python
{
    "query": str,
    "top_k": int,
    "prefs": dict,
    "sites": list[str]?  # Optional site filter
}
```

#### Processing
1. **Make HTTP calls** to e-commerce sites, OR
2. **Query search engine** (if already built)
3. **Normalize responses** across different site schemas
4. **Deduplicate** similar products
5. **Sort** by relevance/price

#### Output (Normalized)
```python
{
  "offers": [
    {
      "id": "...",
      "title": "...",
      "price": ...,
      "url": "...",
      "site": "shopee",
      "rating": 4.7,
      "shipping": {...},
      "in_stock": true,
      "seller_rating": 4.8,
      ...
    },
    ...
  ],
  "metadata": {
    "queried_sites": ["shopee", "lazada"],
    "latency_ms": 234,
    "errors": {}
  }
}
```

**→ Returns offers** to be stored in `state.facts["offers"]` for decision node.

---

### 5.2 DecisionTool / Smart-Buyer Scoring

#### Input
```python
{
    "options": offers,           # From PriceCompareTool
    "criteria": [                # Decision criteria
        {"name": "price", "weight": 0.4, "maximize": false},
        {"name": "rating", "weight": 0.3, "maximize": true},
        {"name": "reviews", "weight": 0.3, "maximize": true}
    ],
    "prefs": {                   # User preferences
        "budget": 20000000,
        "required_tags": ["official"],
        ...
    }
}
```

#### Processing Logic
1. **Normalize attributes** (price, rating, shipping, brand, tags)
2. **Calculate multi-criteria score** for each option:
   ```
   total_score = Σ(weight_i × normalized_value_i)
   ```
3. **Rank options** by total score
4. **Identify winner** and confidence
5. **Generate trade-off analysis**

#### Output
```python
{
  "best": "offer_id_123",
  "confidence": 0.82,
  "option_scores": [
    {"option_id": "...", "total_score": 0.82, "rank": 1},
    {"option_id": "...", "total_score": 0.73, "rank": 2},
    ...
  ],
  "explanation": {
    "winner": "iPhone 15 128GB from Shopee",
    "best_by_criterion": {
        "price": "offer_id_456",      # Cheapest
        "rating": "offer_id_123",     # Highest rated
        "overall": "offer_id_123"     # Best overall
    },
    "tradeoffs": [
        "Top choice costs 500k more but has 4.8 rating vs 4.2",
        "Cheapest option has only 50 reviews"
    ],
    "per_option": [
        {
            "option_id": "offer_id_123",
            "pros": ["High rating", "Many reviews"],
            "cons": ["Slightly more expensive"]
        }
    ],
    "summary": "Recommended: iPhone 15 128GB from Shopee..."
  }
}
```

---

## Layer 6: Response Assembly & Return to Client

After orchestrator completes, service returns result to API:

### Final Response Structure

```python
{
  "request_id": "abc123",
  "query": "iPhone 15",
  "latency_ms": 950,
  "offers": [
    {
      "site": "shopee",
      "title": "iPhone 15 128GB Official",
      "price": 21990000,
      "url": "https://shopee.vn/...",
      "currency": "VND",
      "rating": 4.8,
      "shop_name": "Apple Official Store"
    },
    ...
  ],
  "scoring": {
    "best": "offer_id_123",
    "confidence": 0.82,
    "option_scores": [
      {"option_id": "offer_id_123", "total_score": 0.82, "rank": 1},
      {"option_id": "offer_id_456", "total_score": 0.73, "rank": 2},
      ...
    ]
  },
  "explanation": {
    "winner": "iPhone 15 128GB from Shopee",
    "confidence": 0.82,
    "best_by_criterion": {
      "price": "offer_id_456",
      "rating": "offer_id_123",
      "overall": "offer_id_123"
    },
    "tradeoffs": [
      "Top choice costs 500k more but has better rating",
      "Cheapest option has limited reviews"
    ],
    "per_option": [
      {
        "option_id": "offer_id_123",
        "pros": ["Highest rating (4.8)", "Official store", "1200+ reviews"],
        "cons": ["Slightly more expensive"]
      }
    ],
    "summary": "Based on your criteria, iPhone 15 128GB from Shopee offers the best overall value..."
  },
  "metadata": {
    "request_id": "abc123",
    "latency_ms": 950,
    "queried_sites": ["shopee", "lazada"],
    "total_offers_found": 12,
    "flow": "smart_buyer"
  }
}
```

---

## Complete Visual Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                              Client                                  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                 FastAPI /v1/smart-buyer (Controller)                │
│                  apps/api/src/api/routes/smart_buyer.py             │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│              OrchestratorService.run_smart_buyer()                  │
│              apps/api/src/services/orchestrator_service.py          │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│           SmartBuyerFlow (LangGraph-Style Orchestrator)             │
│           apps/api/src/router/flows/smart_buyer_flow.py             │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 1. Planner (LLM)                                             │  │
│  │    - Analyze query intent                                     │  │
│  │    - Generate execution plan                                  │  │
│  │    - Select tools & steps                                     │  │
│  └──────────────────────────┬───────────────────────────────────┘  │
│                             │                                       │
│  ┌──────────────────────────▼───────────────────────────────────┐  │
│  │ 2. PriceCompareNode                                          │  │
│  │    packages/agent_core/nodes/price_compare.py                │  │
│  │    ├─> Call PriceCompareTool                                 │  │
│  │    │   packages/tools/tools/price_compare_tool.py            │  │
│  │    │   └─> PriceCompareEngine                                │  │
│  │    │       packages/search_core/ecommerce/price_compare.py   │  │
│  │    │       ├─> ShopeeMockAdapter                             │  │
│  │    │       └─> LazadaMockAdapter                             │  │
│  │    └─> Output: state.facts["offers"] = [...]                 │  │
│  └──────────────────────────┬───────────────────────────────────┘  │
│                             │                                       │
│  ┌──────────────────────────▼───────────────────────────────────┐  │
│  │ 3. DecisionNode                                              │  │
│  │    packages/agent_core/nodes/decision.py                     │  │
│  │    ├─> Call DecisionTool                                     │  │
│  │    │   packages/tools/tools/decision_tool.py                 │  │
│  │    │   ├─> Scoring (multi-criteria)                          │  │
│  │    │   │   packages/decision_core/scoring.py                 │  │
│  │    │   └─> Explainer (trade-offs)                            │  │
│  │    │       packages/decision_core/explainer.py               │  │
│  │    └─> Output: state.facts["scoring"] = {...}                │  │
│  │              state.facts["explanation"] = {...}               │  │
│  └──────────────────────────┬───────────────────────────────────┘  │
│                             │                                       │
│  ┌──────────────────────────▼───────────────────────────────────┐  │
│  │ 4. ExplainNode (Optional - LLM Enhancement)                  │  │
│  │    packages/agent_core/nodes/explain.py                      │  │
│  │    ├─> Use LLM to naturalize explanation                     │  │
│  │    └─> Output: Enhanced state.facts["explanation"]           │  │
│  └──────────────────────────┬───────────────────────────────────┘  │
│                             │                                       │
│  ┌──────────────────────────▼───────────────────────────────────┐  │
│  │ 5. FinalizeNode                                              │  │
│  │    packages/agent_core/nodes/finalize.py                     │  │
│  │    ├─> Assemble final response                               │  │
│  │    ├─> Add metadata                                          │  │
│  │    └─> state.mark_done(output)                               │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Normalized Response                              │
│    {offers, scoring, explanation, metadata}                         │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   HTTP JSON Response → Client                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## LangGraph-Style Characteristics

Your implementation follows LangGraph principles:

### 1. **State-Centric Design**
```python
# State flows through all nodes
AgentState {
    query: str
    facts: Dict[str, Any]  # Mutable working memory
    logs: List[StepLog]    # Execution trace
    budget_tokens: int     # Cost control
    done: bool             # Completion flag
}
```

### 2. **Node-Based Execution**
```python
# Each node is self-contained
class PriceCompareNode(BaseNode):
    async def _run(self, state, ctx):
        # Read from state
        query = state.query
        # Execute logic
        offers = await self.tools.call("price_compare", {...})
        # Write to state
        state.facts["offers"] = offers
        return state
```

### 3. **Sequential Graph Execution**
```python
# Flow executes nodes in order
for node in self.nodes:
    if state.done:
        break
    state = await node.run(state, ctx)
```

### 4. **Observability**
```python
# Every node logs execution
state.add_log(
    kind="price_compare",
    step="run",
    latency_ms=234,
    error=None
)
```

### 5. **Budget Control**
```python
# Token budget prevents runaway costs
if state.spent_tokens >= state.budget_tokens:
    state.mark_done({...})  # Graceful degradation
```

---

## Comparison: Traditional vs LangGraph-Style

### Traditional Approach (Function Chaining)
```python
offers = await fetch_offers(query)
scores = await score_offers(offers, criteria)
explanation = await explain_results(scores)
return {offers, scores, explanation}
```

**Limitations:**
- ❌ No intermediate state visibility
- ❌ Can't pause/resume execution
- ❌ Hard to add conditional logic
- ❌ No budget control
- ❌ Limited observability

### LangGraph-Style (Your Implementation)
```python
state = AgentState(query=query, budget_tokens=5000)
plan = await planner.plan(state)  # LLM decides steps
nodes = instantiate_nodes(plan)

for node in nodes:
    state = await node.run(state, ctx)
    if state.done or budget_exceeded(state):
        break

return state.output
```

**Advantages:**
- ✅ Full state visibility at each step
- ✅ Can add conditional routing
- ✅ Budget enforcement
- ✅ Complete execution logs
- ✅ Fail-soft error handling
- ✅ Dynamic planning via LLM

---

## Data Transformations

### Request → State → Response

```python
# 1. HTTP Request
POST /v1/smart-buyer
{
    "query": "iPhone 15",
    "top_k": 5
}

# 2. AgentState (Internal)
AgentState {
    query: "iPhone 15",
    facts: {
        "prefs": {},
        "offers": [],      # Populated by PriceCompareNode
        "scoring": {},     # Populated by DecisionNode
        "explanation": {}  # Populated by ExplainNode
    },
    logs: [...],
    done: false
}

# 3. HTTP Response
{
    "request_id": "...",
    "query": "iPhone 15",
    "offers": [6 products],
    "scoring": {best, confidence, scores},
    "explanation": {winner, tradeoffs, summary},
    "metadata": {latency_ms, sources}
}
```

---

## Key Design Patterns

### 1. **Dependency Injection**
```python
@router.post("/smart-buyer")
async def smart_buyer(
    tools=Depends(get_tool_registry),
    llm=Depends(get_llm),
    http=Depends(get_http_client)
):
    # Dependencies injected automatically
```

### 2. **Fail-Soft Pattern**
```python
# Nodes never crash the pipeline
try:
    state = await node.run(state, ctx)
except Exception as e:
    state.add_log(error=str(e))
    # Continue with partial results
```

### 3. **Circuit Breaker**
```python
# In PriceCompareTool
if self._circuit_open():
    return {"offers": [], "metadata": {"error": "circuit_open"}}
```

### 4. **Request Tracing**
```python
# request_id flows through entire pipeline
Gateway → Service → Orchestrator → Flow → Nodes → Tools
```

---

## Summary

### Architecture Highlights

**Multi-Agent Reasoning Pipeline:**
- ✅ LangGraph-style stateful execution
- ✅ Dynamic LLM-driven planning
- ✅ Modular node-based architecture
- ✅ Multi-criteria decision making
- ✅ Natural language explanations
- ✅ Budget-aware execution
- ✅ Complete observability

### Key Files

| Layer | File | Purpose |
|-------|------|---------|
| API | `apps/api/src/api/routes/smart_buyer.py` | HTTP endpoint |
| Service | `apps/api/src/services/orchestrator_service.py` | Coordination |
| Flow | `apps/api/src/router/flows/smart_buyer_flow.py` | Graph execution |
| Nodes | `packages/agent_core/nodes/*.py` | Individual steps |
| Tools | `packages/tools/tools/*.py` | Tool implementations |
| Engine | `packages/search_core/ecommerce/price_compare.py` | Domain logic |

### Data Flow Summary

```
Request (JSON)
    ↓
Validation (Pydantic)
    ↓
Service (ctx preparation)
    ↓
Orchestrator (state initialization)
    ↓
Flow (graph execution)
    ↓
Nodes (sequential/conditional)
    ├─> PriceCompareNode → offers
    ├─> DecisionNode → scoring
    ├─> ExplainNode → explanation
    └─> FinalizeNode → final output
    ↓
Response (JSON)
```

### Why This Architecture?

**Traditional Pipeline** (linear):
```
fetch → filter → sort → return
```
**Limitations**: Simple, but can't handle complex reasoning, trade-offs, or adaptive planning.

**LangGraph-Style** (stateful graph):
```
plan → execute → observe → score → explain → finalize
```
**Benefits**: Multi-step reasoning, conditional logic, budget control, full observability.

---

**For implementation details, see:**
- Architecture: `ARCHITECTURE.md`
- Run guide: `RUN_GUIDE.md`
- Development plan: `develop_planning.md`
- Code inventory: `CODE_INVENTORY.md`
