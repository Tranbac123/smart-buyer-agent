# 12 Core Concepts for Production-Grade AI Agent Architecture

To fully understand and control your AI Agent system architecture, knowing the flows alone is not enough.

You must also master **12 core concept groups**—each is an "architectural pillar" in a production-grade AI Agent system.

This comprehensive guide covers the complete mental model of a **Senior AI Agent Architect**, aligned with the architecture you're building:

```
API → Service Layer → Orchestrator → Flow → Nodes → Tools → Engines → Memory → LLM → Infrastructure
```

---

## 🌐 12 Essential Concepts (A to Z)

**Organized into 3 architectural tiers:**

---

## Tier I: Application Architecture Level

### 1. Layered Architecture

Understanding the separation of concerns across layers:

**Layers in Your System:**
- **Router** (FastAPI) - HTTP endpoints
- **Service Layer** - Business logic coordination
- **Orchestrator** - Workflow management
- **Domain Logic** - Agents, Flows, Nodes
- **Tools & Engines** - Executable capabilities
- **Infrastructure** - LLM, Memory, HTTP client

**Your Current Architecture:**
```
API → Services → Orchestrator → Flow → Node → Tool → Engine → External API
```

**👉 This is Clean Architecture for AI Agents**

**Key Principles:**
- Inner layers don't know about outer layers
- Dependencies point inward
- Easy to test, swap, and scale

**Example:**
```python
# ✅ Good: Node doesn't know about HTTP
class PriceCompareNode:
    def __init__(self, tools: ToolRegistry):  # Depends on abstraction
        self.tools = tools

# ❌ Bad: Node coupled to HTTP
class PriceCompareNode:
    def __init__(self, shopee_url: str):  # Depends on concrete detail
        self.url = shopee_url
```

---

### 2. Dependency Injection (DI) & Wiring

Understanding who provides what:

**Critical Questions:**
- Who provides the **tool registry**?
- Who provides the **LLM client**?
- Who creates the **HTTP client**?
- Where should dependencies be injected?

**Golden Rule**: **Inject at Service level, NOT in Nodes**

**Why DI Matters:**
- ✅ **Easy to test** - Mock dependencies
- ✅ **Easy to scale** - Swap implementations
- ✅ **Request isolation** - Each request has its own context

**Example:**

```python
# ✅ Good: DI at API/Service level
@router.post("/smart-buyer")
async def smart_buyer(
    tools=Depends(get_tool_registry),  # ← Injected
    llm=Depends(get_llm),              # ← Injected
    http=Depends(get_http_client)      # ← Injected
):
    flow = SmartBuyerFlow(tools=tools, llm=llm)
    return await flow.run(state, ctx)

# ❌ Bad: Creating dependencies inside nodes
class PriceCompareNode:
    async def _run(self, state, ctx):
        tools = ToolRegistry()  # ← Creates new instance every time
        llm = OpenAI(api_key="...")  # ← Hardcoded dependency
```

**Your Implementation:**
```python
# apps/api/src/dependencies/
├── llm_provider.py         # get_llm()
├── tools_provider.py       # get_tool_registry()
├── http_client_provider.py # get_http_client()
└── memory_provider.py      # get_memory()
```

---

### 3. Orchestration (Agent Orchestrator)

The orchestrator is the **conductor** that controls the entire execution.

**Orchestrator Responsibilities:**
- ⏱️ **Lifecycle management** - Start and end execution
- ⏰ **Timeout control** - Prevent runaway processes
- 🛡️ **Error handling** - Catch and handle failures
- 🏗️ **State initialization** - Build initial `AgentState`
- 🔄 **Flow execution** - Run the workflow graph
- 📦 **Output normalization** - Merge and format results

**Your Implementation:**

```python
# apps/api/src/services/orchestrator_service.py
class OrchestratorService:
    async def run_smart_buyer(
        self,
        *,
        query: str,
        tools: ToolRegistry,
        llm: ILLMClient,
        request_id: str,
        timeout_s: float = 20.0
    ) -> Dict[str, Any]:
        # 1. Build initial state
        state = AgentState(session_id=request_id, query=query)
        
        # 2. Create flow
        flow = SmartBuyerFlow(tools=tools, llm=llm)
        
        # 3. Execute with timeout
        try:
            result = await asyncio.wait_for(
                flow.run(state, ctx),
                timeout=timeout_s
            )
            return result
        except asyncio.TimeoutError:
            return self._error_response(request_id, "timeout")
        except Exception as e:
            return self._error_response(request_id, str(e))
```

**🔧 Your `OrchestratorService` is exactly right!**

---

## Tier II: Agent Architecture Level

### 4. Workflow / Graph Execution

The **most important concept** in Agent systems.

**Core Graph Concepts:**

1. **Node** - A single atomic operation (search, score, explain)
2. **Step** - An execution instance of a node
3. **Edge** - Connection between nodes (sequential or conditional)
4. **Planner** - Generates the execution graph dynamically
5. **Router** - Decides which path to take
6. **Conditional branching** - `if/else` logic in the graph
7. **Termination criteria** - When to stop execution
8. **Retry strategies** - How to handle failures
9. **Parallel vs Sequential** - Concurrent or ordered execution

**All major frameworks use graph-based workflows:**
- LangGraph
- AutoGen
- CrewAI

**Your Implementation (LangGraph-Style):**

```python
# Sequential graph with conditional termination
for idx, node in enumerate(self.nodes):
    if state.done:  # ← Termination criteria
        break
    
    state = await node.run(state, ctx)
    
    if self._budget_exceeded(state):  # ← Conditional branching
        state.mark_done({...})
        break
```

**Graph Structure:**

```
┌──────────────────────────────────────────────┐
│          Smart Buyer Graph                   │
├──────────────────────────────────────────────┤
│                                              │
│  [START]                                     │
│     ↓                                        │
│  [PriceCompareNode]                          │
│     ↓                                        │
│  [DecisionNode]                              │
│     ↓                                        │
│  [ExplainNode] ←─────┐                       │
│     ↓                │ (skip if no offers)   │
│  [FinalizeNode]      │                       │
│     ↓                │                       │
│  [END] ←─────────────┘                       │
│                                              │
└──────────────────────────────────────────────┘
```

---

### 5. State Management (AgentState)

The **working memory** of your agent during execution.

**Key State Components:**

```python
class AgentState(BaseModel):
    # Core fields
    session_id: str              # Request identifier
    query: str                   # User query
    
    # Working memory
    facts: Dict[str, Any]        # Accumulated data
    logs: List[StepLog]          # Execution trace
    output: Optional[Dict]       # Final result
    context: Optional[Dict]      # Additional context
    
    # Control flags
    done: bool                   # Completion status
    step_idx: int                # Current step
    
    # Budget tracking
    budget_tokens: int           # Token limit
    spent_tokens: int            # Tokens used
```

**State Evolution Example:**

```python
# Initial state
state = AgentState(
    session_id="req-123",
    query="iPhone 15",
    facts={},
    done=False
)

# After PriceCompareNode
state.facts = {
    "offers": [6 products]
}

# After DecisionNode
state.facts = {
    "offers": [6 products],
    "scoring": {best, confidence},
    "explanation": {winner, tradeoffs}
}

# After FinalizeNode
state.done = True
state.output = {
    "offers": [...],
    "scoring": {...},
    "explanation": {...}
}
```

**Immutable vs Mutable:**

```python
# Mutable approach (your current implementation)
async def _run(self, state, ctx):
    state.facts["offers"] = offers  # Mutates state
    return state

# Immutable approach (pure functional)
async def _run(self, state, ctx):
    return state.model_copy(update={
        "facts": {**state.facts, "offers": offers}
    })
```

**💡 This is the "temporary memory" of your agent during request processing.**

---

### 6. Nodes (Atomic Reasoning Steps)

**The MOST IMPORTANT concept in Agent architecture.**

**What is a Node?**
- A **single, focused action**
- **Single responsibility** principle
- Pure function-like: `input → processing → output`

**Your Nodes:**
- `PriceCompareNode` - Fetch product offers
- `DecisionNode` - Score and rank options
- `ExplainNode` - Generate explanations
- `FinalizeNode` - Package final response

**Node Design Principles:**

```python
class PriceCompareNode(BaseNode):
    """
    ✅ Good node design:
    - Doesn't know about API/HTTP
    - Doesn't know about FastAPI
    - Only knows: state + ctx → updated state
    """
    
    async def _run(self, state: AgentState, ctx: Dict) -> AgentState:
        # Read from state
        query = state.query
        
        # Execute logic (via tools)
        offers = await self.tools.call("price_compare", {
            "query": query,
            "top_k": ctx.get("top_k", 6)
        })
        
        # Write to state
        state.facts["offers"] = offers
        
        # Return updated state
        return state
```

**What Nodes Should NOT Do:**

```python
# ❌ Bad: Node knows about HTTP
class BadNode(BaseNode):
    async def _run(self, state, ctx):
        response = requests.get("http://api.com")  # ← Direct HTTP call
        
# ❌ Bad: Node knows about FastAPI
class BadNode(BaseNode):
    async def _run(self, state, ctx):
        raise HTTPException(404)  # ← HTTP-specific error
        
# ❌ Bad: Node has multiple responsibilities
class BadNode(BaseNode):
    async def _run(self, state, ctx):
        offers = fetch_offers()
        scores = score_offers()
        explanation = explain_offers()  # ← Should be 3 separate nodes
```

**Nodes are:**
- ✅ **Testable** - Pure logic, easy to mock
- ✅ **Reusable** - Can use in different flows
- ✅ **Composable** - Chain them in any order
- ✅ **Observable** - Each logs its execution

---

### 7. Tools (External Capabilities)

A tool is a **capability** that your agent can use.

**Your Tools:**
- `price_compare` - Multi-site product search
- `decision_score` - Multi-criteria scoring & explanation
- `tavily_search` - Web search (optional)
- `http_request` - Generic HTTP calls
- `search_web` - Search tool

**Critical Tool Concepts:**

1. **Input Schema** - What the tool accepts
   ```python
   {
       "query": str,
       "top_k": int,
       "prefs": dict,
       "sites": list[str]?
   }
   ```

2. **Output Schema** - What the tool returns
   ```python
   {
       "offers": list[dict],
       "metadata": dict
   }
   ```

3. **Timeout** - Per-tool execution limits
   ```python
   async def call(self, payload):
       return await asyncio.wait_for(
           self.engine.compare(...),
           timeout=8.0  # ← Tool-level timeout
       )
   ```

4. **Retry Logic** - Exponential backoff
   ```python
   for attempt in range(max_retries + 1):
       try:
           return await self._execute()
       except TransientError:
           await asyncio.sleep(backoff_base * (2 ** attempt))
   ```

5. **Circuit Breaker** - Prevent cascading failures
   ```python
   if self._cb_failures >= threshold:
       self._cb_open_until = now + cooldown
       return {"offers": [], "error": "circuit_open"}
   ```

6. **Normalization Rules** - Standardize output
   ```python
   # Different sites, same output format
   shopee_offer → {"site": "shopee", "price": 100, ...}
   lazada_offer → {"site": "lazada", "price": 100, ...}
   ```

**Tool Registry:**

```python
# packages/tools/tools/registry.py
class ToolRegistry:
    def register(self, name: str, tool: Any):
        self._tools[name] = tool
    
    async def call(self, name: str, payload: dict):
        tool = self._tools.get(name)
        return await tool.call(payload)
    
    def list_tools(self) -> List[str]:
        return list(self._tools.keys())
```

---

## Tier III: AI & Data Layer

### 8. LLM Client Abstraction

**Golden Rule**: **NEVER call LLM directly** - always use abstraction layer

**Why Abstraction Matters:**
- Swap providers (OpenAI ↔ Anthropic ↔ Local) without code changes
- Add retry, caching, monitoring at one place
- Test with mock LLM
- Track costs centrally

**Abstraction Layers:**

1. **ILLMClient** - Base interface
   ```python
   class ILLMClient(ABC):
       @abstractmethod
       async def complete(self, system: str, user: str, format: str?) -> str:
           ...
   ```

2. **ChatCompletion** - Text generation
3. **Embedding** - Vector generation (for RAG)
4. **Rerank** - Result re-ranking
5. **Explanation Generator** - Natural language output
6. **Planner LLM** - Generate execution plans

**Your Implementation:**

```python
# packages/llm_client/llm_client/
├── base.py              # ILLMClient interface
├── openai_client.py     # OpenAI implementation
├── anthropic_client.py  # Anthropic implementation
└── local_client.py      # Dev/test fallback
```

**Critical LLM Concepts:**

1. **Batching** - Multiple requests in one call
   ```python
   responses = await llm.complete_batch([
       {"system": sys, "user": user1},
       {"system": sys, "user": user2}
   ])
   ```

2. **Streaming** - Real-time response chunks
   ```python
   async for chunk in llm.stream(system=sys, user=user):
       yield chunk
   ```

3. **Token Counting** - Track costs
   ```python
   tokens_used = count_tokens(prompt + response)
   state.spend_tokens(tokens_used)
   ```

4. **Model Selection** - Choose based on task
   ```python
   # Planning: Use smart model
   plan = await llm.complete(..., model="gpt-4o")
   
   # Simple tasks: Use fast model
   summary = await llm.complete(..., model="gpt-4o-mini")
   ```

5. **Cost Monitoring** - Track spend
   ```python
   cost = tokens_used * price_per_1k_tokens / 1000
   logger.info(f"LLM call cost: ${cost:.4f}")
   ```

6. **Caching** - Avoid duplicate LLM calls
   ```python
   @lru_cache(maxsize=100)
   async def cached_complete(prompt_hash):
       return await llm.complete(...)
   ```

---

### 9. Memory Layers

**3 types of memory in AI Agent systems:**

#### **1. Short-Term Memory** (`AgentState`)
- **Purpose**: Single request processing
- **Lifetime**: Request duration only
- **Storage**: In-memory (Python objects)
- **Use case**: Working memory during execution

```python
# Short-term memory
state.facts["offers"] = [...]  # Lives only during this request
```

#### **2. Long-Term Memory** (Vector DB / Redis / PostgreSQL)
- **Purpose**: Cross-session persistence
- **Lifetime**: Days, weeks, or permanent
- **Storage**: Database (Redis, PostgreSQL, SQLite)
- **Use case**: User preferences, past searches, learned patterns

```python
# Long-term memory
await memory.save(
    session_id=user_id,
    key="preferences",
    value={"budget": 20000000, "preferred_sites": ["shopee"]}
)

# Retrieve later
prefs = await memory.get(session_id=user_id, key="preferences")
```

#### **3. Episodic Memory** (Logs, Events)
- **Purpose**: System improvement and debugging
- **Lifetime**: As long as needed for analysis
- **Storage**: Log files, analytics DB
- **Use case**: Performance analysis, agent refinement

```python
# Episodic memory
state.logs = [
    {"node": "price_compare", "latency_ms": 234},
    {"node": "decision", "latency_ms": 89},
    ...
]
```

**Key Memory Operations:**

1. **Retrieve** - Get relevant memories
   ```python
   memories = await memory.retrieve(query="iPhone preferences", top_k=3)
   ```

2. **Score** - Rank by relevance
   ```python
   scored = memory.score(memories, current_context)
   ```

3. **Merge** - Combine multiple memories
   ```python
   merged = memory.merge(session_memory, user_memory)
   ```

4. **Write-back Rules** - When to persist
   ```python
   if confidence > 0.8:
       await memory.save(...)  # Only save high-confidence data
   ```

5. **Summarization** - Compress old memories
   ```python
   summary = await llm.summarize(old_conversations)
   await memory.replace(old_data, summary)
   ```

6. **TTL** (Time-To-Live) - Expiration
   ```python
   await memory.save(key="search_cache", value=offers, ttl=600)  # 10 min
   ```

7. **Eviction** - Remove old data
   ```python
   # LRU: Least Recently Used
   if memory_full:
       memory.evict_lru(count=10)
   ```

---

### 10. Retrieval (RAG / Hybrid Search)

**Future enhancement**: SmartBuyer can use RAG (Retrieval-Augmented Generation) for:

**Use Cases:**
- 📊 **Product analysis** - Deep dive into specifications
- ⭐ **Review aggregation** - Analyze thousands of reviews
- 📈 **Price history** - Track price trends over time
- 📋 **Spec sheets** - Compare technical specifications
- 🏆 **Benchmarks** - Performance comparisons

**RAG Concepts You Need to Know:**

#### **1. BM25** (Text-based search)
```python
# Traditional keyword matching
scores = bm25.score(query="iPhone 15", documents=reviews)
# Returns: [0.82, 0.71, 0.45, ...]
```

#### **2. Embeddings** (Semantic search)
```python
# Vector-based similarity
query_vec = embed("iPhone 15 battery life")
doc_vecs = embed_batch(all_reviews)
scores = cosine_similarity(query_vec, doc_vecs)
```

#### **3. Hybrid Search** (Best of both)
```python
# Combine BM25 + embeddings
final_score = alpha * bm25_score + (1 - alpha) * embedding_score
```

#### **4. Reranking** (Cross-Encoder)
```python
# Initial retrieval: Get top 100
candidates = hybrid_search(query, top_k=100)

# Rerank: Get best 10
reranked = cross_encoder.rerank(query, candidates, top_k=10)
```

#### **5. Chunking** (Document splitting)
```python
# Split long documents
chunks = chunk_document(
    text=long_review,
    chunk_size=512,
    overlap=50
)
```

#### **6. Metadata Filters** (Structured filtering)
```python
# Filter before semantic search
results = retriever.search(
    query="laptop gaming",
    filters={
        "price": {"$lt": 30000000},
        "rating": {"$gte": 4.0},
        "site": {"$in": ["shopee", "lazada"]}
    }
)
```

**Your RAG Implementation (Future):**

```python
# packages/rag/
├── indexer.py      # Index product data
├── retriever.py    # Retrieve relevant info
└── reranker.py     # Rerank results
```

---

## Tier IV: Infrastructure Level

### 11. Observability (Logs, Metrics, Tracing)

**Critical for debugging and optimization** - this is how you debug agents quickly.

#### **A. Logs** (What happened?)

**Types of Logs:**

1. **Node Logs** - Each step's execution
   ```python
   logger.info("PriceCompareNode executed", extra={
       "request_id": rid,
       "offers_found": 6,
       "latency_ms": 234
   })
   ```

2. **Tool Logs** - Tool calls and results
   ```python
   logger.info("price_compare tool called", extra={
       "query": "iPhone 15",
       "sites": ["shopee", "lazada"],
       "success": True
   })
   ```

3. **Request Logs** - Full request lifecycle
   ```python
   logger.info("Request completed", extra={
       "request_id": rid,
       "total_latency_ms": 950,
       "nodes_executed": 4,
       "tokens_spent": 430
   })
   ```

4. **Error Logs** - Failures and exceptions
   ```python
   logger.error("Node failed", extra={
       "node": "price_compare",
       "error": "TimeoutError",
       "retry_attempt": 2
   })
   ```

5. **Structured Logs** - JSON format for parsing
   ```python
   {
       "timestamp": "2024-11-18T10:30:45Z",
       "level": "INFO",
       "request_id": "abc123",
       "node": "decision",
       "latency_ms": 89,
       "offers_scored": 6
   }
   ```

#### **B. Metrics** (How is it performing?)

**Key Metrics to Track:**

1. **Latency** - Response time
   ```python
   metrics.histogram("smart_buyer.latency_ms", latency)
   metrics.histogram("node.price_compare.latency_ms", node_time)
   ```

2. **Token Spent** - LLM costs
   ```python
   metrics.counter("llm.tokens_spent", tokens)
   metrics.gauge("llm.cost_usd", cost)
   ```

3. **Requests Per Minute** - Load
   ```python
   metrics.counter("smart_buyer.requests")
   ```

4. **Tool Call Count** - Usage patterns
   ```python
   metrics.counter("tool.price_compare.calls")
   metrics.counter("tool.decision_score.calls")
   ```

5. **Time Per Node** - Bottleneck detection
   ```python
   metrics.histogram("node.price_compare.duration_ms", 234)
   metrics.histogram("node.decision.duration_ms", 89)
   metrics.histogram("node.explain.duration_ms", 1876)
   ```

#### **C. Tracing** (How did it execute?)

**Distributed Tracing:**

1. **Trace ID** - Unique identifier for entire request
   ```python
   trace_id = "trace-abc123"
   # Follows request through all layers
   ```

2. **Span Per Node** - Each node is a span
   ```python
   with tracer.start_span("price_compare_node") as span:
       span.set_attribute("query", query)
       span.set_attribute("top_k", top_k)
       offers = await node.run(state, ctx)
       span.set_attribute("offers_found", len(offers))
   ```

3. **Correlation ID** - Link related requests
   ```python
   # All requests from same user session
   correlation_id = session_id
   ```

**Observability Stack:**

```python
# Your implementation
state.add_log(
    kind="price_compare",
    step="run",
    input={"query": "iPhone 15"},
    output={"offers_count": 6},
    latency_ms=234,
    error=None
)
```

**Visualization:**

```
Request abc123
├─ Span 1: smart_buyer_flow (2.3s)
│  ├─ Span 1.1: planner (150ms)
│  ├─ Span 1.2: price_compare_node (234ms)
│  ├─ Span 1.3: decision_node (89ms)
│  ├─ Span 1.4: explain_node (1876ms)  ← Bottleneck!
│  └─ Span 1.5: finalize_node (12ms)
```

---

### 12. Error Handling & Fail-Soft Strategy

**Core Principle**: Agent architecture must **fail gracefully** - never crash the entire system.

#### **Failure Cascade Strategy**

```
node error      → continue with partial data
tool error      → fallback to alternative
llm error       → retry → fallback → report
orchestrator    → stable error envelope
API error       → 200 OK + partial data + error flag
```

#### **Error Categories**

**1. Transient Errors** (Retry-able)
```python
try:
    result = await self.tools.call("price_compare", payload)
except (TimeoutError, ConnectionError) as e:
    # Retry with exponential backoff
    await asyncio.sleep(2 ** attempt)
    result = await self.tools.call("price_compare", payload)
```

**2. Permanent Errors** (Fail-soft)
```python
try:
    offers = await fetch_offers()
except ValidationError:
    # Can't fix, return empty
    offers = []
    state.facts["error"] = "validation_failed"
```

**3. Critical Errors** (Abort gracefully)
```python
try:
    state = await flow.run(state, ctx)
except BudgetExceededError:
    # Stop but return what we have
    return state.output or {"offers": [], "error": "budget_exceeded"}
```

#### **Recovery Strategies**

**1. Retry with Backoff**
```python
for attempt in range(max_retries):
    try:
        return await action()
    except TransientError:
        await asyncio.sleep(backoff_base * (2 ** attempt))
# All retries failed
return fallback_value
```

**2. Fallback to Alternative**
```python
try:
    return await primary_llm.complete(...)
except Exception:
    return await fallback_llm.complete(...)  # Cheaper/local model
```

**3. Degraded Mode**
```python
# If scoring fails, return offers without ranking
if scoring_failed:
    return {
        "offers": offers,
        "scoring": None,
        "explanation": {"summary": "Scoring unavailable, showing all results"}
    }
```

**4. Circuit Breaker**
```python
# After 5 consecutive failures, stop calling the service
if self._failures >= 5:
    self._circuit_open_until = now + 30  # 30 seconds cooldown
    return {"error": "circuit_open"}
```

**5. Token Exhaustion Handling**
```python
if state.spent_tokens >= state.budget_tokens:
    state.mark_done({
        "offers": state.facts.get("offers", []),
        "summary": "Partial results due to budget limit"
    })
```

#### **Your Implementation**

**In BaseNode:**
```python
try:
    new_state = await self._run(state, ctx)
    return new_state
except Exception as e:
    # Log error but don't crash
    state.add_log(kind=self.name, step="error", error=str(e))
    return state  # Continue with current state
```

**In OrchestratorService:**
```python
try:
    result = await flow.run(state, ctx)
except asyncio.TimeoutError:
    return self._error_response(request_id, "timeout")
except Exception as e:
    return self._error_response(request_id, str(e))
# Always returns a stable response
```

**In PriceCompareTool:**
```python
# Circuit breaker + retry + timeout
if self._circuit_open():
    return {"offers": [], "metadata": {"error": "circuit_open"}}

for attempt in range(max_retries):
    try:
        return await asyncio.wait_for(
            self.engine.compare(...),
            timeout=self.timeout_s
        )
    except asyncio.TimeoutError:
        if attempt < max_retries - 1:
            await asyncio.sleep(backoff_delay)
            continue
        return {"offers": [], "metadata": {"error": "timeout"}}
```

---

## 🎯 Conclusion

**To fully understand your Smart Buyer Agent architecture, you need to master:**

✅ **12 core concept groups**  
✅ **6 primary flow types**  
✅ **Workflow graph execution** (LangGraph-style)  
✅ **Clean Architecture for AI Agents**  
✅ **Observability & Error Strategy**  
✅ **State & Tool Abstraction**  

**Mastering these concepts = Senior AI Agent Architect mindset**

You won't just write code—you'll **understand the system from top to bottom**.

---

## 📚 Quick Reference

| Tier | Concepts | Files to Study |
|------|----------|----------------|
| **Application** | 1-3: Layering, DI, Orchestration | `apps/api/src/` |
| **Agent** | 4-7: Graph, State, Nodes, Tools | `packages/agent_core/` |
| **AI/Data** | 8-10: LLM, Memory, RAG | `packages/llm_client/`, `packages/memory_core/` |
| **Infrastructure** | 11-12: Observability, Errors | `packages/shared/`, `apps/api/src/api/middlewares/` |

---

## 🔗 Related Documentation

- **Data Flow**: `DATAFLOW.md` - See how data flows through layers
- **Architecture**: `ARCHITECTURE.md` - System design overview  
- **Run Guide**: `RUN_GUIDE.md` - How to run the system
- **Development Plan**: `develop_planning.md` - Implementation roadmap
- **Code Inventory**: `CODE_INVENTORY.md` - File status tracking

---

**Remember**: Great AI Agent systems are built on solid architectural foundations, not just clever prompts!