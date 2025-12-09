# QuantumX AI - Development Roadmap

**Philosophy**: Focus on a "thin vertical slice" to get an early demo: 1 route → call 1 tool → return offer list + short recommendation. Then add sites/logic later. This is the recommended roadmap (low risk, fast testable version).

**Current Status**: Architecture complete (80%), critical implementation gaps preventing MVP launch.

**Time to MVP**: 4-8 hours of focused work

---

## 🎯 Quick Start Guide

### Prerequisites
```bash
# Python 3.10+
python --version

# Node.js 18+
node --version

# Install Python package manager
pip install --upgrade pip
```

### Setup Steps (First Time)
```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install Python dependencies (after creating requirements.txt)
pip install -r apps/api/requirements.txt

# 3. Setup environment variables
cp apps/api/.env.example apps/api/.env
# Edit .env with your API keys

# 4. Install frontend dependencies
cd apps/web-app
npm install

# 5. Setup frontend environment
cp .env.local.example .env.local
# Edit with API URL
```

---

## Phase 0: Critical Fixes (BLOCKING) ⚠️
**Must complete before anything else works. Estimated: 2-3 hours**

### 0.1 Fix Syntax Errors in API Routes (~45 min)
**File**: `apps/api/src/api/routes/smart_buyer.py`

**Syntax Fixes**:
- [ ] Line 23: Fix `required_tags = Optional[List[str]]` → `required_tags: Optional[List[str]] = None`
- [ ] Line 75: Fix `@router.port` → `@router.post`
- [ ] Line 79: Import/define `OrchestratorService` dependency
- [ ] Line 80-82: Import missing dependencies (`ToolsProvider`, `get_llm`, `get_http_client`)
- [ ] Line 93: Fix typo `req.critetia` → `req.criteria`
- [ ] Line 111: Fix typo `ScotingOut` → `ScoringOut`
- [ ] Line 113: Fix typo `confidnet` → `confidence`
- [ ] Line 116: Fix typo `os` → `opt` (in loop variable)

**After Fixes - Add Schema Validation**:
- [ ] Create mini test script to validate request/response schemas
- [ ] Lock the contract: `query, top_k, prefs, criteria` → maps to Orchestrator
- [ ] Test with sample payload to prevent schema regression

```python
# Test script: tests/test_smart_buyer_schema.py
from apps.api.src.api.routes.smart_buyer import SmartBuyerRequest

def test_schema():
    req = SmartBuyerRequest(query="iPhone 15", top_k=5)
    assert req.query == "iPhone 15"
    assert req.top_k == 5
    print("✅ Schema validation passed")
```

### 0.2 Create Python Dependencies File (~15 min)
**File**: `apps/api/requirements.txt`

```txt
# Core Framework
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.5.0
pydantic-settings>=2.1.0

# HTTP Client (choose httpx only, no requests for MVP)
httpx>=0.25.0

# LLM Providers (optional - only install when needed)
# openai>=1.3.0
# anthropic>=0.7.0

# Database (optional for MVP - enable in Phase B)
# psycopg[binary]>=3.1.0
# redis>=5.0.0

# Utilities
python-dotenv>=1.0.0

# Note: Keep dependencies minimal for MVP
# Add openai/anthropic only when LLM explanations are enabled
```

### 0.3 Implement Basic OpenAI Client (~1 hour)
**File**: `packages/llm_client/llm_client/openai_client.py`

```python
from typing import Optional, Any
from openai import AsyncOpenAI
from .base import ILLMClient

class OpenAIClient(ILLMClient):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
    
    async def complete(
        self,
        sys: Optional[str] = None,
        user: Optional[str] = None,
        format: Optional[str] = None
    ) -> str:
        messages = []
        if sys:
            messages.append({"role": "system", "content": sys})
        if user:
            messages.append({"role": "user", "content": user})
        
        kwargs = {"model": self.model, "messages": messages}
        if format == "json":
            kwargs["response_format"] = {"type": "json_object"}
        
        response = await self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""
```

### 0.4 Fix LLM Provider Import Error (~10 min)
**File**: `apps/api/src/dependencies/llm_provider.py`

- [ ] Line 62: Fix `packages.llm_client.local_client import` → `from packages.llm_client.llm_client.local_client import`
- [ ] Line 31: Fix `return Node` → `return None`

### 0.5 Create Environment Configuration Files (~20 min)

**File**: `apps/api/.env.example`
```bash
# API Configuration
QX_ENV=dev
QX_HOST=0.0.0.0
QX_PORT=8000
QX_DEBUG=true

# LLM Provider
QX_LLM_PROVIDER=openai
QX_OPENAI_API_KEY=sk-your-key-here
QX_ANTHROPIC_API_KEY=sk-ant-your-key-here

# CORS
QX_CORS_ORIGINS=http://localhost:3000,http://localhost:3001

# Optional Features
QX_FEATURES__ENABLE_SMART_BUYER=true
QX_FEATURES__ENABLE_RAG=false
QX_FEATURES__ENABLE_SEARCH_CACHE=false  # Enable in Phase B with Redis

# Request ID for observability
QX_ENABLE_REQUEST_ID=true
```

**File**: `apps/api/.env`
```bash
# Copy from .env.example and add real API keys
```

**File**: `apps/web-app/.env.local.example`
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_ENABLE_STREAMING=true
```

### 0.6 Create Fake Product Adapter for Testing (~30 min)
**File**: `packages/search_core/search_core/ecommerce/sites/fake_adapter.py`

```python
"""Fake adapter for testing without real scraping"""
from typing import List, Dict, Any
import random

class FakeAdapter:
    """Returns static fake products for testing"""
    
    PRODUCTS = [
        {"name": "iPhone 15 128GB", "base_price": 21990000},
        {"name": "iPhone 15 Pro 256GB", "base_price": 28990000},
        {"name": "Samsung Galaxy S24", "base_price": 19990000},
        {"name": "Xiaomi 14", "base_price": 16990000},
        {"name": "OPPO Find X6", "base_price": 18990000},
    ]
    
    def search(self, query: str, limit: int = 6) -> List[Dict[str, Any]]:
        results = []
        for i, prod in enumerate(self.PRODUCTS[:limit]):
            # Add some variance
            price = prod["base_price"] + random.randint(-500000, 500000)
            rating = round(random.uniform(3.8, 4.9), 1)
            reviews = random.randint(50, 2000)
            sold = random.randint(100, 5000)
            
            results.append({
                "id": f"fake_{i}",
                "name": prod["name"],
                "price": price,
                "rating": rating,
                "review_count": reviews,
                "sold": sold,
                "url": f"https://example.com/product/{i}",
                "image_url": "https://via.placeholder.com/200",
                "shop_name": f"Shop {i+1}",
                "site": "shopee"  # Fake site
            })
        return results
```

### 0.7 Wire Orchestrator to Routes (~45 min)
**File**: `apps/api/src/api/routes/smart_buyer.py`

Add proper imports and dependency injection:
```python
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from apps.api.src.orchestrator.orchestrator_service import OrchestratorService
from apps.api.src.dependencies.llm_provider import get_llm
from apps.api.src.dependencies.tools_provider import get_tools
from apps.api.src.dependencies.http_client_provider import get_http_client

# Add dependency provider
def get_orchestrator_service() -> OrchestratorService:
    from apps.api.src.dependencies.llm_provider import get_llm
    from apps.api.src.dependencies.memory_provider import get_memory
    from apps.api.src.dependencies.tools_provider import get_tools
    from apps.api.src.dependencies.rag_provider import get_rag
    
    return OrchestratorService(
        llm_client=get_llm(),
        memory_service=get_memory(),
        tools_registry=get_tools(),
        rag_service=get_rag()
    )
```

---

## Phase A: End-to-End Working Flow (Happy Path)
**After Phase 0 fixes, build the vertical slice. Estimated: 2-3 hours**

### A.1 Minimal API Route Setup (~30 min)

**Goal**: GET `/v1/healthz` and POST `/v1/smart-buyer` working

**Files to verify/update**:
- [x] `apps/api/src/api/routes/health.py` (already exists)
- [ ] `apps/api/src/api/routes/smart_buyer.py` (fix errors from Phase 0)
- [ ] `apps/api/src/api/http_gateway.py` (verify route mounting)

**Test**:
```bash
# Start API
cd apps/api
uvicorn src.main:app --reload --port 8000

# In another terminal
curl http://localhost:8000/v1/healthz
curl -X POST http://localhost:8000/v1/smart-buyer \
  -H "Content-Type: application/json" \
  -d '{"query": "iPhone 15", "top_k": 5}'
```

### A.2 Tool Registry + Core Tools (~45 min)

**File**: `packages/tools/tools/registry.py`

- [ ] Verify `register()` method works
- [ ] Register `price_compare` tool
- [ ] Register `decision_score` tool
- [ ] Add `has_tool()` method for validation
- [ ] **Add health check**: Expose `list_tools()` for `/v1/readyz` endpoint

**File**: `packages/tools/tools/price_compare_tool.py`
- [x] Already implemented with retry + circuit breaker (excellent!)
- [ ] Verify `site` filter works
- [ ] Test circuit breaker behavior
- [ ] Test with fake adapter

**File**: `packages/tools/tools/decision_tool.py`
- [ ] Verify it calls `decision_core.scoring.score_options()`
- [ ] Verify it calls `explainer.build_explanation()`
- [ ] Add confidence calculation: `confidence = (top1_score - top2_score) / top1_score`
- [ ] Log scoring margin for observability

**Health Check Integration**:
```python
# Add to apps/api/src/api/routes/health.py
@router.get("/readyz")
async def ready_check(tools: ToolRegistry = Depends(get_tools)):
    registered = tools.list_tools()
    if len(registered) == 0:
        raise HTTPException(503, "No tools registered")
    return {"status": "ready", "tools": registered}
```

**Test**:
```python
# Test in Python REPL
from packages.tools.tools.registry import ToolRegistry
registry = ToolRegistry()
print(registry.list_tools())  # Should show: ['price_compare', 'decision_score']
result = await registry.call("price_compare", {"query": "iPhone", "top_k": 5})
print(result["offers"])
```

### A.3 Connect Fake Adapter to Price Compare (~20 min)

**File**: `packages/search_core/search_core/ecommerce/price_compare.py`

Update to use FakeAdapter:
```python
from .sites.fake_adapter import FakeAdapter

class PriceCompareEngine:
    def __init__(self):
        # Use fake adapter for MVP
        self.adapters = {"shopee": FakeAdapter()}
    
    async def compare(self, query: str, top_k: int, prefs, sites):
        all_results = []
        for site_name, adapter in self.adapters.items():
            try:
                results = adapter.search(query, limit=top_k)
                all_results.extend(results)
            except Exception as e:
                logger.error(f"Site {site_name} failed: {e}")
        
        return {
            "offers": all_results[:top_k],
            "metadata": {"total_found": len(all_results)}
        }
```

### A.4 Decision Core Verification (~30 min)

**File**: `packages/decision_core/decision_core/scoring.py`
- [ ] Verify multi-criteria scoring works
- [ ] Test with fake products
- [ ] Ensure normalization works

**File**: `packages/decision_core/decision_core/explainer.py`
- [ ] Implement rule-based explanation (no LLM needed for MVP)
- [ ] Generate pros/cons based on scores
- [ ] Generate warnings for low ratings/reviews

**Test**:
```python
from packages.decision_core.decision_core.scoring import Scoring, Criterion
from packages.decision_core.decision_core.explainer import Explainer

criteria = [
    Criterion(name="price", weight=0.4, maximize=False),
    Criterion(name="rating", weight=0.6, maximize=True)
]
scoring = Scoring(criteria)
results = scoring.score_options(fake_products)
print(results[0])  # Top scoring product
```

### A.5 Create Startup Scripts (~15 min)

**File**: `scripts/start-api.sh`
```bash
#!/bin/bash
set -e

cd "$(dirname "$0")/.."

echo "🚀 Starting QuantumX API..."

# Activate venv if exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Check .env exists
if [ ! -f "apps/api/.env" ]; then
    echo "❌ Missing apps/api/.env file"
    echo "💡 Copy from .env.example and add your API keys"
    exit 1
fi

# Start API
cd apps/api
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

**File**: `scripts/start-frontend.sh`
```bash
#!/bin/bash
set -e

cd "$(dirname "$0")/../apps/web-app"

echo "🎨 Starting QuantumX Frontend..."

# Check .env.local exists
if [ ! -f ".env.local" ]; then
    echo "❌ Missing .env.local file"
    echo "💡 Copy from .env.local.example"
    exit 1
fi

# Install deps if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Start dev server
npm run dev
```

Make executable:
```bash
chmod +x scripts/start-api.sh scripts/start-frontend.sh
```

### A.6 End-to-End Test & Observability (~45 min)

**Add Request ID Tracking**:
Ensure `request_id` flows through entire pipeline:
- [ ] Gateway → Orchestrator → Flow → Tools → Engine
- [ ] Log with request_id at each stage
- [ ] Return request_id in response

**Add Key Metrics Logging**:
```python
# In orchestrator, log these metrics:
{
    "request_id": rid,
    "query": query,
    "top_k": top_k,
    "total_latency_ms": total_latency,
    "latency_by_site": {"shopee": 234, "lazada": 456},
    "total_offers": 12,
    "offers_returned": 5,
    "top1_score": 0.85,
    "top2_score": 0.73,
    "score_margin": 0.12,  # Confidence indicator
    "winner": "product_123"
}
```

**MVP Definition of Done** (Success Criteria):
- [ ] ✅ POST `/v1/smart-buyer` returns in ≤ 5 seconds
- [ ] ✅ Response contains ≥ 3 offers
- [ ] ✅ Has `scoring.best`, `confidence`, and `summary`
- [ ] ✅ No crashes on popular queries (iPhone, Samsung, Xiaomi)
- [ ] ✅ Frontend shows list + suggestions
- [ ] ✅ Frontend can create "new chat" and save history
- [ ] ✅ Request ID tracked throughout

**Test Checklist**:
- [ ] API starts without errors
- [ ] Health check: `curl http://localhost:8000/v1/healthz`
- [ ] Ready check: `curl http://localhost:8000/v1/readyz` (shows registered tools)
- [ ] Smart buyer route accepts requests
- [ ] Fake products are returned (≥ 3 offers)
- [ ] Scoring is applied (has best + confidence)
- [ ] Response time ≤ 5 seconds
- [ ] Logs show request_id and metrics
- [ ] Frontend loads at http://localhost:3000
- [ ] Can type query and get response
- [ ] Results display in UI with recommendations

**Standard Test Cases** (3-5 queries):
```bash
# Test 1: Popular product
curl -X POST http://localhost:8000/v1/smart-buyer \
  -H "Content-Type: application/json" \
  -d '{"query": "iPhone 15", "top_k": 5}'

# Test 2: Generic query
curl -X POST http://localhost:8000/v1/smart-buyer \
  -H "Content-Type: application/json" \
  -d '{"query": "laptop gaming", "top_k": 6}'

# Test 3: With preferences
curl -X POST http://localhost:8000/v1/smart-buyer \
  -H "Content-Type: application/json" \
  -d '{"query": "Samsung Galaxy", "top_k": 5, "prefs": {"budget": 20000000}}'
```

---

## Phase B: Gradually Thicken (Incremental)
**After MVP works, add features one by one. Estimated: 4-8 hours**

### B.1 Add Real Site Scraping (1-2 hours per site)

**Priority**: Start with easiest site first
1. [ ] Tiki (has public API)
2. [ ] Shopee (requires scraping)
3. [ ] Lazada (requires scraping)

**Implementation per site**:
- [ ] Create site client class
- [ ] Implement search method
- [ ] Parse response to standard format
- [ ] Add error handling
- [ ] Test with real queries
- [ ] Add to PriceCompareEngine

### B.2 Enhance with LLM Explanations (~1 hour)

**Prerequisites**:
- [ ] Install LLM provider: `pip install openai` or `pip install anthropic`
- [ ] Update `.env`: Set `QX_LLM_PROVIDER=openai` and add API key
- [ ] Test LLM connection: Small script to verify `get_llm()` works

**File**: `packages/decision_core/decision_core/explainer.py`

Add LLM-powered explanation with fallback:
```python
async def generate_natural_explanation(
    self,
    top_products: List[Dict],
    scoring_results: Dict
) -> str:
    """Use LLM to generate natural language explanation with fallback"""
    
    # Try LLM first
    try:
        if self.llm and not isinstance(self.llm, LocalClient):
            prompt = f"""
            Explain why these are the top product recommendations:
            
            {json.dumps(top_products[:3], indent=2)}
            
            Provide:
            - Why the top choice is best (2-3 sentences)
            - Key trade-offs between top 3 options
            - Any warnings or concerns
            
            Keep it concise and actionable.
            """
            
            return await self.llm.complete(
                sys="You are a shopping advisor helping users make informed purchase decisions.",
                user=prompt
            )
    except Exception as e:
        logger.warning(f"LLM explanation failed: {e}, falling back to rule-based")
    
    # Fallback to rule-based
    return self._generate_rule_based_explanation(top_products, scoring_results)

def _generate_rule_based_explanation(self, top_products, scoring_results):
    """Rule-based explanation (current MVP version)"""
    # ... existing rule-based logic ...
```

**Test LLM Integration**:
```python
# Test script: tests/test_llm.py
from apps.api.src.dependencies.llm_provider import get_llm

async def test_llm():
    llm = get_llm()
    result = await llm.complete(
        sys="You are a helpful assistant.",
        user="Say 'LLM works!'"
    )
    print(f"✅ LLM Response: {result}")
    
# Run: python -m pytest tests/test_llm.py -v
```

### B.3 Add Ranking & Deduplication (~45 min)

**File**: `packages/search_core/search_core/ranking.py`

- [ ] Implement BM25 for text relevance
- [ ] Combine with business scores
- [ ] Add deduplication by (normalized_title + shop)

### B.4 Add Caching (Redis) (~1-2 hours)

**Note**: Redis caching is **Phase B** - NOT needed for MVP. Add after basic flow works.

**Prerequisites**:
- [ ] Install Redis: `brew install redis` (Mac) or `apt-get install redis` (Linux)
- [ ] Start Redis: `redis-server`
- [ ] Install client: `pip install redis`
- [ ] Update `.env`: Set `QX_FEATURES__ENABLE_SEARCH_CACHE=true`

**File**: `apps/api/src/dependencies/cache_provider.py`

```python
import redis.asyncio as redis
import hashlib
import json
from functools import wraps
from typing import Optional

class CacheProvider:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self._client: Optional[redis.Redis] = None
    
    async def get_client(self):
        if not self._client:
            self._client = await redis.from_url(self.redis_url)
        return self._client

def cached(ttl_seconds: int = 600):
    """
    Cache decorator for tool results.
    Cache key based on payload hash (query + prefs).
    TTL: 3-10 minutes to avoid stale data.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from payload
            payload = kwargs.get("payload", {})
            cache_key_data = {
                "query": payload.get("query"),
                "top_k": payload.get("top_k"),
                "prefs": payload.get("prefs")
            }
            key_hash = hashlib.md5(json.dumps(cache_key_data, sort_keys=True).encode()).hexdigest()
            cache_key = f"qx:tool:{func.__name__}:{key_hash}"
            
            try:
                cache = await get_cache()
                
                # Try cache first
                cached_value = await cache.get(cache_key)
                if cached_value:
                    logger.info(f"Cache hit: {cache_key}")
                    return json.loads(cached_value)
                
                # Call function
                result = await func(*args, **kwargs)
                
                # Store in cache (fire and forget)
                await cache.setex(cache_key, ttl_seconds, json.dumps(result))
                logger.info(f"Cache set: {cache_key}, TTL={ttl_seconds}s")
                
                return result
            except Exception as e:
                logger.warning(f"Cache error: {e}, proceeding without cache")
                return await func(*args, **kwargs)
        return wrapper
    return decorator

async def get_cache():
    """Dependency injection for cache"""
    return await redis.from_url("redis://localhost:6379")
```

**Usage in Tool**:
```python
# In packages/tools/tools/price_compare_tool.py
@cached(ttl_seconds=300)  # 5 minutes
async def call(self, payload: Dict[str, Any]) -> Dict[str, Any]:
    # ... existing implementation ...
```

**Why Cache at Tool Level**:
- Cache raw offers before scoring (scoring criteria may change)
- Avoid hammering e-commerce sites during demos
- TTL 3-10 minutes prevents stale prices

### B.5 Improve Error Handling & Logging (~30 min)

- [ ] Add structured logging with request IDs
- [ ] Add error tracking (Sentry optional)
- [ ] Add retry logic for site failures
- [ ] Add fallback responses

---

## Phase C: Polish & Production Ready
**Make it production-ready. Estimated: 4-6 hours**

### C.1 Metrics & Observability (~2 hours)
- [ ] Add latency tracking (p50, p95, p99)
- [ ] Track success rate per site
- [ ] Track query coverage (% with results)
- [ ] Add health check for dependencies

### C.2 Docker & Deployment (~2 hours)
- [ ] Create Dockerfile for API
- [ ] Update docker-compose.yml
- [ ] Add deployment docs
- [ ] CI/CD pipeline (optional)

### C.3 Testing (~2 hours)
- [ ] Unit tests for critical paths
- [ ] Integration tests for API routes
- [ ] End-to-end test suite
- [ ] Load testing

---

## Progress Tracking

### ✅ Completed
- [x] Architecture design (ARCHITECTURE.md)
- [x] Package structure (agent_core, search_core, decision_core)
- [x] Router with intent detection
- [x] Frontend UI structure
- [x] Orchestrator design

### 🚧 In Progress
- [ ] Phase 0: Critical Fixes

### ⏳ Todo
- [ ] Phase A: End-to-End Flow
- [ ] Phase B: Thicken Features
- [ ] Phase C: Production Polish

---

## Troubleshooting & Tips

### Common Issues

**1. Import Errors (CRITICAL)**
```bash
# Solution 1: Set PYTHONPATH (recommended for development)
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Solution 2: Install packages in editable mode
pip install -e packages/agent_core
pip install -e packages/search_core
pip install -e packages/decision_core
pip install -e packages/tools
pip install -e packages/llm_client
pip install -e packages/memory_core
pip install -e packages/shared

# Add to your shell profile (~/.bashrc or ~/.zshrc):
echo 'export PYTHONPATH="${PYTHONPATH}:$(pwd)"' >> ~/.zshrc
```

**2. Schema Mismatch Errors**
```bash
# Lock pydantic models with simple validation test
python -c "from apps.api.src.api.routes.smart_buyer import SmartBuyerRequest; req = SmartBuyerRequest(query='test', top_k=5); print('✅ Schema OK')"

# If schema breaks, check:
# - Field names match between route → orchestrator → tool
# - Types are correct (str, int, Optional[...])
# - Default values are set
```

**3. LLM API Errors**
```bash
# For MVP, use local client (no API key needed)
# In .env: QX_LLM_PROVIDER=local

# When enabling real LLM:
echo $QX_OPENAI_API_KEY  # Check key is set
python -c "from apps.api.src.dependencies.llm_provider import get_llm; print(get_llm())"

# Test connection
curl https://api.openai.com/v1/models -H "Authorization: Bearer $QX_OPENAI_API_KEY"
```

**4. Port Already in Use**
```bash
# Find and kill process
lsof -ti:8000 | xargs kill -9

# Or use different port
uvicorn src.main:app --port 8001
```

**5. Frontend Can't Connect to API**
- Check CORS settings in `apps/api/src/config/settings.py`
- Verify `NEXT_PUBLIC_API_URL=http://localhost:8000` in `.env.local`
- Check API is running: `curl http://localhost:8000/v1/healthz`
- Check network tab in browser DevTools for CORS errors

**6. Tool Not Registered**
```bash
# Check tools are registered
curl http://localhost:8000/v1/readyz

# Should return: {"status": "ready", "tools": ["price_compare", "decision_score"]}
# If empty, check tools_provider.py registers tools on startup
```

**7. Timeout/Site Failures**
```bash
# Circuit breaker already implemented in PriceCompareTool
# Check logs for: "circuit_open" or "timeout"
# Verify retry + backoff is working
# Use fake adapter for testing: no network calls, no failures
```

### Risks & Mitigation

| Risk | Mitigation | Phase |
|------|------------|-------|
| **Import path errors** | Set `PYTHONPATH=$(pwd)` or `pip install -e packages/*` | Phase 0 |
| **Schema mismatch** | Lock pydantic models + add validation test | Phase 0 |
| **Missing LLM API key** | Default to `local` provider, fail-soft on errors | Phase 0 |
| **Scraping blocked** | Start with fake adapter, add real scraping in Phase B | MVP |
| **LLM slow/expensive** | Use rule-based explainer first, add LLM optional | Phase B |
| **Timeout/site failures** | Retry + backoff + circuit breaker (already in tool) | MVP |
| **Site data varies** | Minimal normalization: title, price, url, rating only | MVP |
| **Complex dependencies** | Keep requirements.txt minimal, docker in Phase C | Phase C |

### Prevention Checklist

Before running MVP:
- [ ] ✅ `PYTHONPATH` is set correctly
- [ ] ✅ `.env` has `QX_LLM_PROVIDER=local`
- [ ] ✅ Schema validation test passes
- [ ] ✅ Tools are registered (check `/v1/readyz`)
- [ ] ✅ Fake adapter returns data
- [ ] ✅ Request ID flows through system
- [ ] ✅ Logs show key metrics

---

## Success Metrics (MVP)

**Must Have**:
- [ ] Query → Results in < 5 seconds
- [ ] At least 3 products returned per query
- [ ] Scoring works (top result makes sense)
- [ ] Frontend displays results cleanly
- [ ] No crashes on common queries

**Nice to Have**:
- [ ] LLM explanations
- [ ] Real scraping from 2+ sites
- [ ] Caching working
- [ ] Response time < 2 seconds

---

## Next Actions (Start Here!) - Sequential Order

### Day 1: Foundation (3-4 hours)

**Phase 0 - Critical Setup** (2.5 hours)
1. [ ] **Setup PYTHONPATH** (5 min)
   ```bash
   export PYTHONPATH="${PYTHONPATH}:$(pwd)"
   echo 'export PYTHONPATH="${PYTHONPATH}:$(pwd)"' >> ~/.zshrc
   ```

2. [ ] **Create requirements.txt** (10 min)
   - Copy from Phase 0.2
   - Keep minimal: fastapi, uvicorn, pydantic, httpx, python-dotenv
   - Install: `pip install -r apps/api/requirements.txt`

3. [ ] **Create .env files** (15 min)
   - `apps/api/.env.example` with `QX_LLM_PROVIDER=local`
   - `apps/api/.env` (copy from example)
   - `apps/web-app/.env.local.example`
   - `apps/web-app/.env.local`

4. [ ] **Fix syntax errors** in `smart_buyer.py` (30 min)
   - All 8 fixes from Phase 0.1
   - Add schema validation test

5. [ ] **Fix import errors** in `llm_provider.py` (10 min)
   - Line 31 and 62 fixes

6. [ ] **Create fake_adapter.py** (30 min)
   - Copy from Phase 0.6
   - Returns 5-6 static products with variance

7. [ ] **Create startup scripts** (20 min)
   - `scripts/start-api.sh`
   - `scripts/start-frontend.sh`
   - `chmod +x scripts/*.sh`

**Phase 0 Verification** (30 min)
8. [ ] **Test API startup**
   ```bash
   ./scripts/start-api.sh
   # In another terminal:
   curl http://localhost:8000/v1/healthz
   ```

9. [ ] **Verify tools registered**
   ```bash
   curl http://localhost:8000/v1/readyz
   # Should show: ["price_compare", "decision_score"]
   ```

### Day 2: Integration (2-3 hours)

**Phase A - End-to-End Flow**
10. [ ] **Connect fake adapter** to price_compare.py (20 min)

11. [ ] **Test tool registry** (30 min)
    - Register price_compare, decision_score
    - Add health check to /readyz
    - Test in REPL

12. [ ] **Add observability** (45 min)
    - Request ID tracking throughout
    - Key metrics logging (latency, offers, scores, margin)

13. [ ] **E2E test** (45 min)
    - POST `/v1/smart-buyer` with test queries
    - Verify response structure
    - Check logs for metrics
    - Verify ≤ 5 second response
    - Test 3-5 standard queries

14. [ ] **Frontend integration** (30 min)
    - Start frontend: `./scripts/start-frontend.sh`
    - Test query → results → display
    - Verify new chat + history works

**MVP Complete!** ✅
- Response time ≤ 5s
- Returns ≥ 3 offers
- Has scoring + confidence
- No crashes on common queries
- Frontend works

### Week 1: Enhancement (optional)

**Phase B - Real Features** (pick 1-2)
15. [ ] Add real site scraping (Tiki first) - 2 hours
16. [ ] Add LLM explanations (with fallback) - 1 hour
17. [ ] Add Redis caching - 1-2 hours

---

## Resources

- Architecture: `ARCHITECTURE.md`
- Implementation summary: `IMPLEMENTATION_SUMMARY.md`
- Package docs: `packages/*/README*.md`
- API docs (when running): http://localhost:8000/docs