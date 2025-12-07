quantumx/
├─ apps/
│  ├─ api/                       # FastAPI backend (HTTP gateway → router → orchestrator)
│  └─ web-app/                   # Next.js UI (chat, chat history, new chat)
├─ packages/                     # Engine & domain layer (imported by apps/*)
│  ├─ agent_core/                # Agent engine: Plan → Act → Observe → Reflect → Refine
│  ├─ decision_core/             # Scoring & explanation logic (scoring + explainer)
│  ├─ llm_client/                # LLM adapter (OpenAI/Claude/local etc.)
│  ├─ memory_core/               # Session/long-term memory abstraction
│  ├─ rag/                       # Retriever and indexer (hybrid)
│  ├─ search_core/               # Search domain logic (e-commerce price compare, etc.)
│  ├─ tools/                     # Tool registry & tool adapters (price_compare, decision, etc.)
│  └─ shared/                    # Shared config/logging/errors/schemas
├─ infra/                        # docker-compose, migrations, etc. (if present)
├─ ARCHITECTURE.md
├─ file_structure.md
└─ IMPLEMENTATION_SUMMARY.md

apps/api (FastAPI backend)
apps/api/src/
├─ main.py                       # create_app(), mount gateway, telemetry, errors
├─ api/
│  ├─ http_gateway.py            # register middlewares, include_routers (/v1/*)
│  └─ routes/
│     ├─ health.py               # GET /healthz, /readyz
│     ├─ chat.py                 # POST /v1/chat (regular chat)
│     └─ smart_buyer.py          # POST /v1/smart-buyer (price compare + recommendation)
├─ config/
│  └─ settings.py                # ENV, CORS, timeouts, rate limit configuration
├─ dependencies/
│  ├─ http_client_provider.py    # httpx.AsyncClient singleton (user agent/timeout/pool)
│  ├─ llm_provider.py            # ILLMClient (OpenAI/Claude/local)
│  ├─ memory_provider.py         # IMemory (in-memory/redis/pg)
│  ├─ rag_provider.py            # IRetriever
│  └─ tools_provider.py          # ToolRegistry with enabled tools
├─ router/
│  ├─ router_service.py          # select flow by intent (chat/deep_research/smart_buyer/etc.)
│  └─ flows/
│     ├─ base_flow.py            # interface/ABC for flows
│     ├─ chat_flow.py            # regular chat flow
│     ├─ deep_research_flow.py   # deep research flow
│     ├─ code_agent_flow.py      # code agent flow
│     └─ smart_buyer_flow.py     # smart-buyer flow (calls corresponding orchestrator)
├─ orchestrator/
│  ├─ orchestrator_service.py    # facade: prepares DI, calls flow/orchestrator
│  └─ flows/
│     ├─ base_orchestrator.py    # ABC orchestrator by flow
│     └─ smart_buyer_orchestrator.py
│        # Orchestration for Smart-Buyer: create agent by profile,
│        # loop Plan→Act (tool: price_compare/decision) → Finalize
└─ README.md

Main responsibilities:
routes/*: HTTP interface, validate I/O, return JSON for web.
router/*: route logic by intent.
orchestrator/*: orchestrate agent core + tools per flow.
dependencies/*: DI providers for client/service (LLM, httpx, tools, etc.).

apps/web-app (Next.js UI)
web-app/
├─ public/
│  ├─ favicon.ico
│  └─ logo.svg
├─ src/
│  ├─ components/
│  │  ├─ Header.tsx              # top bar
│  │  ├─ Sidebar.tsx             # history + new chat
│  │  ├─ ChatWindow.tsx          # list messages + main input area
│  │  ├─ MessageBubble.tsx       # chat bubble
│  │  ├─ NewChatButton.tsx       # create new session (optional)
│  │  └─ ChatList.tsx            # session list (optional)
│  ├─ hooks/
│  │  ├─ useChat.ts              # chat state per sessionId (messages/send)
│  │  └─ useStream.ts            # SSE/stream handler from API (if using streaming)
│  ├─ lib/
│  │  ├─ api.ts                  # call backend API (/v1/chat, /v1/smart-buyer)
│  │  └─ config.ts               # baseURL, keys
│  ├─ pages/
│  │  ├─ _app.tsx                # global layout/providers
│  │  ├─ _document.tsx           # (optional) custom <Html>, fonts
│  │  ├─ index.tsx               # redirect → /chat or thin landing
│  │  ├─ chat.tsx                # single-session page (or use…)
│  │  └─ chat/[id].tsx           # multi-session chat by id (recommended)
│  ├─ styles/                    # CSS/tailwind
│  └─ types/
│     └─ chat.ts                 # type Message, Session, Role, etc.
├─ next.config.js
├─ package.json
├─ README.md
└─ tsconfig.json

Main purpose:
Minimal chat UI: input → call API → display answer.
History: store in localStorage (or call backend) by sessionId.
New chat: create new session → push route /chat/[id].

packages/agent_core (Agent engine)
packages/agent_core/agent_core/
├─ interfaces.py                 # ILLMClient, IToolRegistry, IMemory, IRetriever
├─ models.py                     # AgentState, ToolCall, StepLog, Output, etc.
├─ planner.py                    # Plan: LLM plans tool calls
├─ executor.py                   # Act: execute tool, loop Plan→Act
├─ observer.py                   # Observe: update state with tool results
├─ reflector.py                  # Reflect: check for missing info
├─ refiner.py                    # Refine: polish final result
├─ finalizer.py                  # Package output (text + structured)
├─ policy/
│  ├─ base_policy.py             # policy interface
│  ├─ cost_policy.py             # cost/time constraints
│  └─ safety_policy.py           # content restrictions
└─ profiles/
   ├─ base_profile.py            # agent configuration structure
   ├─ chat_profile.py            # regular chat profile
   ├─ deep_research_profile.py   # deep research profile
   ├─ smart_buyer_profile.py     # smart-buyer profile (allowed tools, budget, depth, etc.)
   └─ profile_manager.py         # select profile by intent/tenant

-> Main purpose: "the brain" of the agent; HTTP-independent; only depends on interfaces & tool registry.

# packages/decision_core (Scoring & Explanation)
packages/decision_core/decision_core/
├─ scoring.py                    # score_options (min–max, reweight if missing, confidence)
└─ explainer.py                  # build_explanation (winner, trade-offs, per-option)
-> Purpose: makes decisions + explanations (rule-based + optional LLM enhancement).

# packages/llm_client (LLM adapters)
packages/llm_client/llm_client/
├─ base.py                       # ILLMClient base
├─ openai_client.py              # OpenAI adapter
├─ anthropic_client.py           # Claude adapter
└─ local_client.py               # local inference adapter (if used)
-> Purpose: unified adapter interface for calling model.

# packages/memory_core (Memory)
packages/memory_core/memory_core/
├─ base.py                       # IMemory
├─ in_memory.py                  # MVP version (RAM/Redis)
└─ pg_memory.py                  # long-term in Postgres/pgvector (future)
-> Purpose: store agent/session short-term and long-term context.

# packages/rag (Retriever/Indexer)
packages/rag/rag/
├─ retriever.py                  # hybrid: BM25 + embeddings + filters
└─ indexer.py                    # build/update index
-> Purpose: used when flow requires external knowledge (deep research/RAG).

# packages/search_core (Search domain: Smart-Buyer)
packages/search_core/search_core/
├─ query_understanding.py        # normalize query, detect variants/intent
├─ ranking.py                    # (optional) separate rerank/dedup layer
└─ ecommerce/
   ├─ models.py                  # Offer, PriceComparisonResult, SearchPreferences
   ├─ normalization.py           # normalize price/currency/tags
   ├─ price_compare.py           # PriceCompareEngine (gather → normalize → rank → clip)
   └─ sites/
      ├─ base.py                 # BaseSiteClient (search→List[Offer])
      ├─ shopee.py               # adapter
      ├─ lazada.py               # adapter
      └─ tiki.py                 # adapter
-> Purpose: logic for finding & comparing prices by domain, separate from tool layer.

# packages/tools (Tool layer)
packages/tools/tools/
├─ registry.py                   # register and call tools by name (price_compare/decision_score, etc.)
├─ price_compare_tool.py         # adapter for search_core.ecommerce.price_compare
└─ decision_tool.py              # adapter for decision_core.scoring + explainer
Purpose: controlled gateway for agent to call domain logic.

# packages/shared (Shared)
packages/shared/shared/
├─ config.py                     # BaseSettings, ENV loader
├─ errors.py                     # AppException, ErrorCode
├─ logging.py                    # setup logger, trace/correlation id
├─ types.py                      # type alias
└─ schemas/                      # (optional) Shared Pydantic schemas between layers
-> Purpose: standardize config, errors, logging, shared types.

# Optional/Recommended Suggestions
apps/api/src/api/routes/: If routes are not yet split, should have health.py, smart_buyer.py, chat.py.
dependencies/http_client_provider.py: very useful to share httpx client instance.
api/schemas/: Pydantic models for request/response, avoid raw dicts in HTTP layer.
api/middlewares/ & api/errors/ & api/telemetry/: logging, CORS, rate-limiting, error schemas, Prometheus/OpenTelemetry — important for production/demo.
web-app/pages/chat/[id].tsx + useChatHistory.ts + storage.ts: for multi-session + "New chat" support.

# Relationship summary
web-app → /v1/* (routes) → router_service → orchestrator (flow)
      → agent_core (profiles/policy)
         → tools (registry → price_compare/decision)
         → search_core (ecommerce.price_compare → sites/*)
         → decision_core (scoring/explainer)
         → llm_client (+ memory_core, rag if needed)

