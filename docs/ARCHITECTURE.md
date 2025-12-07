# QuantumX AI - Architecture Overview

## Complete Request Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER REQUEST                                  │
│             "So sánh giá iPhone 15 trên Shopee và Lazada"          │
└────────────────────────────┬────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 1: HTTP GATEWAY (apps/api/src/api/http_gateway.py)           │
├─────────────────────────────────────────────────────────────────────┤
│ • Receive HTTP request                                              │
│ • Basic auth, rate limiting                                         │
│ • Extract: message, session_id, context                            │
└────────────────────────────┬────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 2: ROUTER SERVICE (apps/api/src/router/router_service.py)    │
├─────────────────────────────────────────────────────────────────────┤
│ • Detect user intent (keyword analysis)                             │
│   - "giá", "so sánh", "Shopee" → Intent.SMART_BUYER                │
│ • Call select_flow(Intent.SMART_BUYER)                              │
│   → Returns SmartBuyerFlow instance                                 │
└────────────────────────────┬────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 3: FLOW (apps/api/src/router/flows/smart_buyer_flow.py)      │
├─────────────────────────────────────────────────────────────────────┤
│ • Lightweight flow wrapper                                          │
│ • Calls orchestrator for complex logic                              │
│ • Handles flow-level concerns (memory, context)                     │
└────────────────────────────┬────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 4: ORCHESTRATOR (orchestrator/flows/smart_buyer_orchestrator)│
├─────────────────────────────────────────────────────────────────────┤
│ 🧠 COORDINATES FULL AGENT EXECUTION                                 │
│                                                                     │
│ ┌─────────────────────────────────────────────────────────────┐   │
│ │ Phase 1: PLAN (agent_core.planner)                          │   │
│ │ ├─ Use QueryUnderstanding to parse query                    │   │
│ │ ├─ Detect: compare mode vs find best                        │   │
│ │ └─ Output: search strategy, sites, criteria                 │   │
│ └─────────────────────────────────────────────────────────────┘   │
│                          ↓                                          │
│ ┌─────────────────────────────────────────────────────────────┐   │
│ │ Phase 2: ACT (agent_core.executor + tools)                  │   │
│ │ ├─ Call price_compare_tool                                   │   │
│ │ ├─ Use search_core.ecommerce.price_compare                   │   │
│ │ └─ Output: products from Shopee, Lazada, Tiki              │   │
│ └─────────────────────────────────────────────────────────────┘   │
│                          ↓                                          │
│ ┌─────────────────────────────────────────────────────────────┐   │
│ │ Phase 3: OBSERVE (agent_core.observer)                      │   │
│ │ ├─ Analyze result quality                                    │   │
│ │ ├─ Check price ranges, ratings distribution                  │   │
│ │ └─ Output: quality metrics, patterns                         │   │
│ └─────────────────────────────────────────────────────────────┘   │
│                          ↓                                          │
│ ┌─────────────────────────────────────────────────────────────┐   │
│ │ Phase 4: SCORE (decision_core)                              │   │
│ │ ├─ Ranking: BM25 + business scores (search_core.ranking)    │   │
│ │ ├─ Scoring: Multi-criteria decision (decision_core.scoring)  │   │
│ │ │  • price: 25% (lower better)                              │   │
│ │ │  • rating: 30% (higher better)                            │   │
│ │ │  • review_count: 25% (higher better)                      │   │
│ │ │  • sold: 20% (higher better)                              │   │
│ │ └─ Output: Sorted by RELEVANCE, not just price              │   │
│ └─────────────────────────────────────────────────────────────┘   │
│                          ↓                                          │
│ ┌─────────────────────────────────────────────────────────────┐   │
│ │ Phase 5: EXPLAIN (decision_core.explainer + LLM)            │   │
│ │ ├─ Get top 1-3 recommendations                               │   │
│ │ ├─ Generate pros/cons (decision_core.explainer)              │   │
│ │ ├─ Identify warnings (low reviews, suspicious price)         │   │
│ │ ├─ Create suggestions (price alerts, alternative sites)      │   │
│ │ └─ Output: Natural language explanation via LLM             │   │
│ └─────────────────────────────────────────────────────────────┘   │
│                          ↓                                          │
│ ┌─────────────────────────────────────────────────────────────┐   │
│ │ Phase 6: REFINE (agent_core.reflector + refiner)            │   │
│ │ ├─ Reflect: Are results sufficient?                          │   │
│ │ ├─ Decide: Need another iteration?                           │   │
│ │ └─ Refine: Adjust plan if needed (currently: single pass)   │   │
│ └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└────────────────────────────┬────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 5: PACKAGE INTEGRATIONS                                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│ ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐  │
│ │  search_core     │  │  decision_core   │  │   agent_core    │  │
│ ├──────────────────┤  ├──────────────────┤  ├─────────────────┤  │
│ │ • QueryUnderstand│  │ • Scoring        │  │ • Planner       │  │
│ │ • Ranking        │  │ • Explainer      │  │ • Executor      │  │
│ │ • PriceCompare   │  │ • Criterion      │  │ • Observer      │  │
│ │ • Shopee         │  │                  │  │ • Reflector     │  │
│ │ • Lazada         │  │                  │  │ • Refiner       │  │
│ │ • Tiki           │  │                  │  │ • Finalizer     │  │
│ └──────────────────┘  └──────────────────┘  └─────────────────┘  │
│                                                                     │
└────────────────────────────┬────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────────┐
│                        RESPONSE TO USER                              │
├─────────────────────────────────────────────────────────────────────┤
│ {                                                                   │
│   "response": "**Top Recommendation:** 🏆 iPhone 15 128GB...",     │
│   "type": "smart_buyer",                                            │
│   "intent": "smart_buyer",                                          │
│   "top_recommendations": [                                          │
│     {                                                               │
│       "rank": 1,                                                    │
│       "product": {                                                  │
│         "name": "iPhone 15 128GB",                                  │
│         "price": 21990000,                                          │
│         "rating": 4.8,                                              │
│         "review_count": 1234,                                       │
│         "site": "shopee"                                            │
│       },                                                            │
│       "score": 0.85,                                                │
│       "pros": ["Strong rating", "High review count"],               │
│       "cons": ["Slightly higher price than Lazada"]                 │
│     }                                                               │
│   ],                                                                │
│   "explanation": {                                                  │
│     "warnings": ["⚠️ Alternative on Lazada 500k cheaper"],         │
│     "suggestions": ["💡 Wait for upcoming sale events"]            │
│   }                                                                 │
│ }                                                                   │
└─────────────────────────────────────────────────────────────────────┘
```

## Architecture Principles

### 1. **Layered Architecture**
```
HTTP Gateway → Router → Flow → Orchestrator → Packages
```
Each layer has clear responsibilities and clean interfaces.

### 2. **Intent-Based Routing**
```python
# Router detects intent from keywords
Intent.SMART_BUYER    → SmartBuyerFlow → SmartBuyerOrchestrator
Intent.DEEP_RESEARCH  → DeepResearchFlow → DeepResearchOrchestrator
Intent.CODE_AGENT     → CodeAgentFlow → CodeAgentOrchestrator
Intent.CHAT           → ChatFlow → (Simple LLM)
```

### 3. **Orchestrator Pattern**
```
Flow (Lightweight) → Orchestrator (Complex Logic)
```
- **Flow**: Entry point, basic setup
- **Orchestrator**: Coordinates agent_core, tools, search_core, decision_core

### 4. **Deep Reasoning Loop**
```
Plan → Act → Observe → Reflect → Refine → (Repeat if needed)
```
Based on agent_core architecture for sophisticated multi-step reasoning.

### 5. **Package Integration**
- **search_core**: Query understanding, ranking, e-commerce search
- **decision_core**: Multi-criteria scoring, explanations
- **agent_core**: Planning, execution, observation, reflection, refinement
- **tools**: Reusable tool implementations
- **llm_client**: LLM abstraction
- **memory_core**: Session and long-term memory
- **rag**: Retrieval for knowledge-intensive tasks

## Smart Buyer Flow Details

### Key Differentiators
✅ **Relevance-based ranking**, not just price
✅ **Multi-criteria scoring**: price (25%), rating (30%), reviews (25%), sales (20%)
✅ **Intelligent warnings**: Low reviews, suspicious pricing
✅ **Actionable suggestions**: Sale events, alternative sites
✅ **Natural language explanations**: Pros, cons, trade-offs
✅ **Multi-site comparison**: Shopee, Lazada, Tiki

### Not Just a Search Engine
Traditional search: Query → Results → Sort by price
**Smart Buyer Agent**: Query → Plan → Search → Analyze → Score → Explain → Recommend

### Example Scenarios

**Scenario 1: Direct Comparison**
```
User: "So sánh giá iPhone 15 trên Shopee và Lazada"
Intent: COMPARE (specific products, specific sites)
Plan: Compare mode, search iPhone 15 on Shopee & Lazada only
Result: Side-by-side comparison with pros/cons
```

**Scenario 2: Best in Category**
```
User: "Tìm laptop gaming giá rẻ tốt nhất"
Intent: RECOMMEND (find best in category)
Plan: Search "laptop gaming", filter by price, rank by value
Result: Top 3 options with quality/price balance
```

**Scenario 3: General Search**
```
User: "Tai nghe Bluetooth"
Intent: SEARCH (general query)
Plan: Broad search, rank by popularity + rating
Result: Popular options with varied price points
```

## Directory Structure

```
quantumx-ai/
├── apps/
│   ├── api/
│   │   └── src/
│   │       ├── main.py                    # FastAPI entry
│   │       ├── api/
│   │       │   └── http_gateway.py        # HTTP endpoints
│   │       ├── router/
│   │       │   ├── router_service.py      # Intent detection → Flow selection
│   │       │   └── flows/
│   │       │       ├── base_flow.py
│   │       │       ├── chat_flow.py
│   │       │       ├── smart_buyer_flow.py
│   │       │       ├── deep_research_flow.py
│   │       │       └── code_agent_flow.py
│   │       ├── orchestrator/
│   │       │   ├── orchestrator_service.py  # Orchestrator coordinator
│   │       │   └── flows/
│   │       │       ├── base_orchestrator.py
│   │       │       └── smart_buyer_orchestrator.py  # ⭐ Main logic
│   │       ├── dependencies/
│   │       │   ├── llm_provider.py
│   │       │   ├── memory_provider.py
│   │       │   ├── tools_provider.py
│   │       │   └── rag_provider.py
│   │       └── config/
│   │           └── settings.py
│   └── web-app/                           # Next.js frontend
├── packages/
│   ├── agent_core/                        # Deep reasoning engine
│   │   └── agent_core/
│   │       ├── planner.py
│   │       ├── executor.py
│   │       ├── observer.py
│   │       ├── reflector.py
│   │       └── refiner.py
│
├── │-- control_plane/                        # Control and policy engine
│   │       ├── control_plane.py        # ControlPlane class
│   │       ├── policies.py             # PolicyEngine
│   │       ├── tool_registry.py        # Tool metadata
│   │       └── logging.py              # Execution log helpers
│
│   ├── search_core/                       # ⭐ Search & ranking
│   │   ├── query_understanding.py
│   │   ├── ranking.py
│   │   └── ecommerce/
│   │       ├── price_compare.py
│   │       └── sites/
│   │           ├── shopee.py
│   │           ├── lazada.py
│   │           └── tiki.py
│   ├── decision_core/                     # ⭐ Scoring & explanations
│   │   ├── scoring.py
│   │   └── explainer.py
│   ├── llm_client/
│   │   ├── openai_client.py
│   │   ├── anthropic_client.py
│   │   └── local_client.py
│   ├── tools/
│   │   ├── registry.py
│   │   ├── search_web.py
│   │   └── price_compare_tool.py
│   ├── memory_core/
│   │   ├── in_memory.py
│   │   └── pg_memory.py
│   └── rag/
│       ├── retriever.py
│       └── indexer.py
└── infra/
    └── docker-compose.yml
```

## Next Steps

### Immediate
1. ✅ Router with intent detection
2. ✅ Flow structure
3. ✅ Orchestrator with Smart Buyer implementation
4. ✅ search_core package
5. ✅ decision_core package

### Short-term
1. ⏳ Implement agent_core components (planner, executor, observer, reflector, refiner)
2. ⏳ Connect tools registry with orchestrator
3. ⏳ Implement actual e-commerce API clients (Shopee, Lazada, Tiki)
4. ⏳ Add LLM client implementations
5. ⏳ Create HTTP gateway endpoints

### Medium-term
1. ⏳ Deep Research orchestrator
2. ⏳ Code Agent orchestrator
3. ⏳ Memory integration (session + long-term)
4. ⏳ RAG for knowledge-intensive queries
5. ⏳ Web frontend integration

### Long-term
1. ⏳ Multi-turn refinement loops
2. ⏳ User preference learning
3. ⏳ Price history tracking
4. ⏳ Deal quality scoring
5. ⏳ Personalized recommendations

