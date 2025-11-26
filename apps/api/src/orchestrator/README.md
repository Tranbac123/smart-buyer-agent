# Orchestrator Architecture

## Overview
The Orchestrator layer maps router flows to agent_core components and coordinates execution of complex multi-step agent workflows.

## Structure

```
apps/api/src/orchestrator/
├── orchestrator_service.py          # Main orchestrator service
└── flows/
    ├── __init__.py
    ├── base_orchestrator.py         # Abstract base class
    └── smart_buyer_orchestrator.py  # Smart Buyer implementation
```

## Smart Buyer Orchestrator

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     Smart Buyer Orchestrator                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────┐    ┌───────────┐    ┌──────────────┐             │
│  │  Router  │───▶│Orchestrator│───▶│ agent_core   │             │
│  │ Service  │    │  Service   │    │  Components  │             │
│  └──────────┘    └───────────┘    └──────────────┘             │
│                         │                                         │
│                         ▼                                         │
│              ┌──────────────────────┐                            │
│              │ SmartBuyerOrchestrator│                            │
│              └──────────────────────┘                            │
│                         │                                         │
│         ┌───────────────┼───────────────┐                       │
│         ▼               ▼               ▼                       │
│   ┌──────────┐   ┌──────────┐   ┌──────────┐                  │
│   │ search_  │   │ decision_│   │  tools   │                  │
│   │  core    │   │   core   │   │ registry │                  │
│   └──────────┘   └──────────┘   └──────────┘                  │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Execution Pipeline

```
User Query: "So sánh giá iPhone 15"
     ↓
┌────────────────────────────────────────────────────────────────┐
│ Phase 1: PLAN (agent_core.planner)                             │
├────────────────────────────────────────────────────────────────┤
│ • Parse query with QueryUnderstanding                          │
│ • Detect intent: compare? or find best?                        │
│ • Determine search strategy                                     │
│ Output: {intent: "compare", sites: ["shopee","lazada","tiki"]} │
└────────────────────────────────────────────────────────────────┘
     ↓
┌────────────────────────────────────────────────────────────────┐
│ Phase 2: ACT (agent_core.executor + tools)                     │
├────────────────────────────────────────────────────────────────┤
│ • Call price_compare_tool                                       │
│ • Use search_core.ecommerce.price_compare                       │
│ • Search across multiple sites                                  │
│ Output: {results: [...20 products...], summary: {...}}         │
└────────────────────────────────────────────────────────────────┘
     ↓
┌────────────────────────────────────────────────────────────────┐
│ Phase 3: OBSERVE (agent_core.observer)                         │
├────────────────────────────────────────────────────────────────┤
│ • Analyze search results                                        │
│ • Check quality metrics (ratings, reviews)                      │
│ • Identify patterns                                             │
│ Output: {total: 20, avg_rating: 4.5, price_range: 5000000}    │
└────────────────────────────────────────────────────────────────┘
     ↓
┌────────────────────────────────────────────────────────────────┐
│ Phase 4: SCORE (decision_core.scoring)                         │
├────────────────────────────────────────────────────────────────┤
│ • Rank with search_core.ranking (BM25 + business scores)       │
│ • Score with decision_core.scoring (multi-criteria)             │
│ • Criteria: price (25%), rating (30%), reviews (25%), sold (20%)│
│ • Sort by RELEVANCE, not just price                             │
│ Output: [{option: {...}, total_score: 0.85}, ...]              │
└────────────────────────────────────────────────────────────────┘
     ↓
┌────────────────────────────────────────────────────────────────┐
│ Phase 5: EXPLAIN (decision_core.explainer + LLM)               │
├────────────────────────────────────────────────────────────────┤
│ • Get top 1-3 options                                           │
│ • Generate pros/cons for each                                   │
│ • Identify warnings (low reviews, suspicious price)             │
│ • Create suggestions                                            │
│ • Use LLM for natural language explanation                      │
│ Output: {top_options: [...], warnings: [...], suggestions: [...]}│
└────────────────────────────────────────────────────────────────┘
     ↓
┌────────────────────────────────────────────────────────────────┐
│ Phase 6: REFINE (agent_core.reflector + refiner)               │
├────────────────────────────────────────────────────────────────┤
│ • Reflect on results quality                                    │
│ • Decide if another iteration is needed                         │
│ • Refine plan if necessary                                      │
│ Output: {should_refine: false, confidence: 0.8}                │
└────────────────────────────────────────────────────────────────┘
     ↓
┌────────────────────────────────────────────────────────────────┐
│ Final Response                                                  │
├────────────────────────────────────────────────────────────────┤
│ **Top Recommendation:**                                         │
│ 🏆 iPhone 15 128GB                                             │
│ • Score: 0.85/1.0                                              │
│ • Price: 21,990,000 VNĐ                                        │
│ • Rating: 4.8/5 (1,234 reviews)                                │
│                                                                 │
│ **Pros:**                                                       │
│ ✓ Strong rating: 4.8                                           │
│ ✓ High review count indicates reliability                      │
│ ✓ Competitive price                                            │
│                                                                 │
│ **Warnings:**                                                   │
│ ⚠️ Alternative option on Lazada 500k cheaper                   │
│                                                                 │
│ **Suggestions:**                                                │
│ 💡 Consider waiting for upcoming sale events                   │
└────────────────────────────────────────────────────────────────┘
```

## Component Integration

### search_core Integration
```python
# Query Understanding
query_understanding = QueryUnderstanding()
parsed = query_understanding.parse_query("So sánh giá iPhone 15")
# → {intent: "compare", normalized_query: "so sánh giá iphone 15"}

# Price Comparison
price_compare = PriceCompare()
results = price_compare.compare_prices("iPhone 15", sites=["shopee", "lazada", "tiki"])
# → {results: [...], best_price: {...}, summary: {...}}

# Ranking
ranking = Ranking(text_weight=0.3, business_weight=0.7)
ranked = ranking.rank_results(results, query)
# → Sorted by BM25 + business scores
```

### decision_core Integration
```python
# Scoring
criteria = [
    Criterion(name="price", weight=0.25, maximize=False),
    Criterion(name="rating", weight=0.30, maximize=True),
    Criterion(name="review_count", weight=0.25, maximize=True),
    Criterion(name="sold", weight=0.20, maximize=True),
]
scoring = Scoring(criteria)
scored = scoring.score_options(products)
# → [{option: {...}, total_score: 0.85, criterion_scores: {...}}, ...]

# Explanation
explainer = Explainer(llm_client)
explanation = explainer.compare_options(top_3_products, scored_data)
# → {recommendation: {...}, tradeoffs: [...], pros: [...], cons: [...]}
```

### agent_core Integration (TODO)
```python
# Planner
planner = Planner(llm_client)
plan = await planner.create_plan(query, context)

# Executor
executor = Executor(llm_client, tools_registry)
result = await executor.execute_action("price_compare", params)

# Observer
observer = Observer(llm_client)
observation = await observer.analyze(results, state)

# Reflector
reflector = Reflector(llm_client)
reflection = await reflector.reflect(state)

# Refiner
refiner = Refiner(llm_client)
refined_plan = await refiner.refine_plan(state)
```

## Usage Example

```python
from apps.api.src.orchestrator.orchestrator_service import (
    OrchestratorService, 
    OrchestratorType
)

# Initialize orchestrator
orchestrator = OrchestratorService(
    llm_client=llm_client,
    memory_service=memory_service,
    tools_registry=tools_registry,
    rag_service=rag_service
)

# Execute Smart Buyer flow
result = await orchestrator.orchestrate_smart_buyer(
    query="So sánh giá iPhone 15 trên Shopee và Lazada",
    session_id="user_123",
    context={"max_results": 20}
)

# Access results
print(result["response"])  # Natural language response
print(result["top_recommendations"])  # Top 3 products
print(result["explanation"]["warnings"])  # Warnings
print(result["explanation"]["suggestions"])  # Suggestions
```

## Key Features

### 1. **Separation of Concerns**
- Router handles flow selection
- Orchestrator coordinates agent_core components
- Clean separation between layers

### 2. **Multi-Criteria Scoring**
- Not just price-based
- Balanced scoring: price (25%), rating (30%), reviews (25%), sales (20%)
- Customizable criteria weights

### 3. **Intelligent Explanations**
- Pros/cons for each option
- Warnings for suspicious patterns
- Actionable suggestions
- Natural language via LLM

### 4. **Extensible Architecture**
- Easy to add new orchestrators
- Pluggable components
- agent_core ready for integration

### 5. **Smart Warnings**
- Low review count detection
- Suspicious pricing alerts
- Quality checks
- Multi-site comparison insights

## Future Enhancements

1. **Full agent_core Integration**
   - Replace placeholder implementations
   - Enable true deep reasoning loop

2. **Advanced Query Understanding**
   - NER for product extraction
   - Price range extraction
   - Brand/feature filtering

3. **Dynamic Criteria**
   - User preference learning
   - Category-specific weights
   - Personalized scoring

4. **Enhanced Explanations**
   - Visual comparisons
   - Price history trends
   - Deal quality scores

5. **Multi-iteration Refinement**
   - Auto-retry with refined queries
   - Expand search if insufficient results
   - Cross-site verification

