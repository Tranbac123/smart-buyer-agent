##1. Mục tiêu & nguyên tắc của Memory Layer
Mục tiêu:
Agent không quên: context đủ dùng cho reasoning & tool.
Agent không ngu lặp lỗi: có procedural / experience memory.
Đa-tenant, multi-agent: mỗi user, mỗi agent, mỗi flow có policy riêng.
Dễ mở rộng: hôm nay chỉ RAG, mai thêm Graph-RAG, Acontext, KV-cache… không vỡ kiến trúc.
Nguyên tắc:
Memory là 1 service/domain riêng, không trộn vào Flow/Node.
Luôn có interface IMemory + các sub-store cụ thể bên dưới.
Flow/Agent không query DB trực tiếp → luôn đi qua Memory Layer.

##1. High-level: Memory Layer đặt ở đâu?
[Gateway] 
   ↓
[Router] 
   ↓
[Orchestrator]
   ↓
[Flow Graph (LangGraph-style)]
   ↓
[Node (Agent / Tool Planner / Worker)]
   ↓           ↘
[Tool]         [LLM Client]
   ↘             ↑
     →→→→ [Memory Layer] ←←←

Memory Layer nằm giữa Node/Tool/LLM, không nằm ngoài:
Node hỏi Memory trước khi quyết định plan/tool.
LLM call có thể được “boost” bằng context từ Memory.
Sau mỗi step, Node/Tool ghi lại vào Memory.

##3. Memory Layer = 1 “Facade” + nhiều “Store” chuyên trách
Kiến trúc:
                    +-------------------------+
                    |       MemoryFacade      |  (IMemory)
                    +-----------+-------------+
                                |
         +-----------+----------+---------+---------------------+
         |           |                    |                     |
+--------v--+  +-----v--------+   +------v------+        +------v-------+
| Dialog    |  | State/Task   |   | Semantic    |        | Procedural   |
| Memory    |  | Memory       |   | Memory (RAG)|        | Memory (SOP) |
+-----------+  +--------------+   +-------------+        +--------------+
      |                |                 |                       |
      |                |                 |                       |
+-----v-----+    +-----v------+    +-----v------+          +-----v---------+
| Profile   |    | Experience |    | External  |          | Acontext-like |
| /Pref     |    | /Eval      |    | KB/Graph  |          | Skill Store   |
+-----------+    +------------+    +-----------+          +---------------+

Các loại memory chính:
DialogMemory – hội thoại ngắn hạn, summary, salience.
State/TaskMemory – graph state, agent state, task progress.
SemanticMemory (RAG) – vector store, text, docs, Graph-RAG.
ProceduralMemory (SOP/Skill) – quy trình đã học được (SOP).
Profile/PreferenceMemory – user info, style, constraints.
Experience/EvalMemory – logs cho error/success, dùng để rút rule.
Tất cả được wrap bởi IMemory / MemoryFacade để Flow chỉ dùng 1 API.

4. Interface tổng quát: IMemory

Ý tưởng: mọi Node chỉ nói chuyện với 1 facade:

from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from enum import Enum


class MemoryScope(str, Enum):
    DIALOG = "dialog"
    STATE = "state"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    PROFILE = "profile"
    EXPERIENCE = "experience"


class MemoryQuery(BaseModel):
    user_id: str
    session_id: str
    agent_id: str
    flow_id: Optional[str] = None
    node_id: Optional[str] = None
    scopes: List[MemoryScope]
    query: Optional[str] = None          # cho semantic/procedural
    task_type: Optional[str] = None      # cho SOP/experience
    extra: Dict[str, Any] = {}


class MemoryResultItem(BaseModel):
    scope: MemoryScope
    payload: Dict[str, Any]              # ví dụ: messages, docs, sop, profile...


class MemoryWriteEvent(BaseModel):
    user_id: str
    session_id: str
    agent_id: str
    flow_id: Optional[str] = None
    node_id: Optional[str] = None
    scope: MemoryScope
    data: Dict[str, Any]                 # nội dung cần lưu
    meta: Dict[str, Any] = {}

class IMemory:
    async def read(self, query: MemoryQuery) -> List[MemoryResultItem]:
        ...
    async def write(self, event: MemoryWriteEvent) -> None:
        ...
    async def delete_session(self, user_id: str, session_id: str) -> None:
        ...
Flow / Node chỉ thấy IMemory. Bên dưới bạn delegate cho từng store.
5. Tách nhỏ thành các “Store” cụ thể
5.1. DialogMemory – short-term / tóm tắt hội thoại
Lưu: messages, summary, salient facts.
Đọc: các messages gần nhất + summary cho LLM.
class DialogMemoryStore:
    async def get_context(self, user_id, session_id, limit_turns=20):
        ...
    async def append(self, user_id, session_id, role, content):
        ...
    async def update_summary(self, user_id, session_id, summary):
        ...

5.2. State/TaskMemory – graph state (LangGraph-style)
Lưu:
current state (variables, status)
task list, progress, dependencies
class StateMemoryStore:
    async def get_state(self, flow_id, session_id):
        ...
    async def save_state(self, flow_id, session_id, state_dict):
        ...
    async def log_task_step(self, task_id, step, status, error=None):
        ...

5.3. SemanticMemory – RAG, Graph-RAG, external KB
Lưu: document chunks, embeddings, metadata.
Đọc: relevant docs cho câu hỏi hiện tại.
class SemanticMemoryStore:
    async def search(self, query_text: str, filters: Dict[str, Any] = None, top_k=5):
        ...
    async def add_documents(self, docs: List[Dict[str, Any]]):
        ...

Nếu bạn dùng Graph-RAG → search() có thể gọi ra graph store / KG.
5.4. ProceduralMemory (SOP/Skill Store)
Lưu: SOP / structured skills.
Đọc: các skill phù hợp task hiện tại.
class ProceduralMemoryStore:
    async def search_skills(self, task_type: str, query: str = "", top_k=3):
        ...
    async def add_skill(self, sop: Dict[str, Any]):
        ...


Ví dụ sop:
{
  "use_when": "deploy Next.js app to Vercel",
  "tool_sops": [
    {"tool": "create_repo", "action": "create repo from template nextjs"},
    {"tool": "run_cmd", "action": "npm install"},
    ...
  ],
  "preferences": "use pnpm if available"
}
5.5. Profile / PreferenceMemory
Lưu: thong tin user, style, constraints, domain config.
Đọc: inject vào prompt cho tất cả agents.
class ProfileMemoryStore:
    async def get_profile(self, user_id: str) -> Dict[str, Any]:
        ...
    async def update_profile(self, user_id: str, changes: Dict[str, Any]):
        ...
5.6. Experience / EvalMemory
Lưu: step-level logs, error, success, cost, latency.
Dùng: train rule, feed cho Experience Agent (kiểu Acontext).
class ExperienceMemoryStore:
    async def log_step(self, step_data: Dict[str, Any]):
        ...
    async def get_failures(self, task_type: str, limit=50):
        ...
    async def get_successful_traces(self, task_type: str, limit=50):
        ...

6. Cách Memory được gọi trong Flow / Node
6.1. Trước khi Node chạy → READ
Ví dụ Node Planner:
Orchestrator gọi Flow.
Flow tới Node Planner.
Node Planner gọi Memory:
query = MemoryQuery(
    user_id=user_id,
    session_id=session_id,
    agent_id="planner",
    flow_id=flow_id,
    node_id="planner_node",
    scopes=[MemoryScope.DIALOG, MemoryScope.SEMANTIC, MemoryScope.PROCEDURAL, MemoryScope.PROFILE],
    query=user_utterance,
    task_type="build_search_agent"
)
mem_results = await memory.read(query)
dialog_ctx = ...
docs_ctx = ...
skills_ctx = ...
profile = ...

Planner build prompt:
system prompt + profile
dialog summary + last turns
SOP/skills (nếu có)
docs từ RAG (nếu cần)
→ LLM ra plan/bước.

6.2. Sau khi Node/Tool chạy → WRITE
Ví dụ sau khi tool gọi xong:
await memory.write(MemoryWriteEvent(
    user_id=user_id,
    session_id=session_id,
    agent_id="worker_agent",
    flow_id=flow_id,
    node_id="http_tool_node",
    scope=MemoryScope.EXPERIENCE,
    data={
        "task_type": "call_external_api",
        "tool_name": "HttpRequestTool",
        "input": tool_input,
        "output": tool_output,
        "error": error,
        "success": error is None,
        "latency_ms": latency,
    },
    meta={"trace_id": trace_id}
))

Và nếu step thành công & đủ “chất lượng”:
Background “Experience Agent” sẽ đọc từ ExperienceStore → rút SOP → push vào ProceduralMemoryStore.

7. Policy Layer: mỗi Flow có MemoryPolicy
Không phải flow nào cũng cần tất cả.
Bạn define MemoryPolicy:
class MemoryPolicy(BaseModel):
    use_dialog: bool = True
    use_semantic: bool = True
    use_procedural: bool = True
    use_profile: bool = True
    write_experience: bool = True
    max_dialog_turns: int = 20
    max_docs: int = 5
    max_skills: int = 3

Flow config:
FLOW_CONFIG["smart_buyer"] = MemoryPolicy(
    use_semantic=True,
    use_procedural=True,
    max_docs=8,
    max_skills=5,
)

MemoryFacade sẽ đọc policy → quyết định:
query store nào
limit bao nhiêu item
có log experience không
8. Tóm tắt kiến trúc Memory Layer chuẩn cho multi-agent
1 Facade IMemory – mọi Node/Flow chỉ gọi 1 chỗ.
6 loại store chính:
DialogMemory
State/TaskMemory
SemanticMemory (RAG/Graph-RAG)
ProceduralMemory (SOP/skills)
ProfileMemory
ExperienceMemory
MemoryPolicy per-flow/agent để custom nhu cầu.
Hooks:
Before Node → memory.read()
After Node/Tool → memory.write()
Background “Experience Agent”:
đọc ExperienceMemory → rút SOP → lưu ProceduralMemory
để agent tự học qua thời gian, không cần fine-tune.

##9. Cấu trúc thư mục packages/memory_core/
packages/
└── memory_core/
    ├── pyproject.toml              # (nếu tách thành package riêng) hoặc setup.cfg/pyproject trên root
    ├── README.md                   # mô tả ngắn về Memory Layer
    └── memory_core/
        ├── __init__.py

        # 1) Config & constants
        ├── config.py               # config chung, connection string, feature flags
        ├── constants.py            # tên index, default limits, scope names...

        # 2) Models: DTO / schema
        ├── models/
        │   ├── __init__.py
        │   ├── enums.py            # MemoryScope, Role, ErrorType...
        │   ├── base.py             # MemoryQuery, MemoryResultItem, MemoryWriteEvent, MemoryPolicy
        │   ├── dialog.py           # schema cho message, summary, salient fact
        │   ├── state.py            # schema cho FlowState, TaskState, StepLog
        │   ├── semantic.py         # schema cho DocumentChunk, RetrievalResult
        │   ├── procedural.py       # schema cho Skill/SOP, ToolStep, UseWhen
        │   ├── profile.py          # UserProfile, Preferences
        │   └── experience.py       # StepExperience, Trace, Lesson

        # 3) Interfaces: abstract base classes
        ├── interfaces/
        │   ├── __init__.py
        │   ├── memory.py           # IMemory (facade)
        │   ├── dialog_store.py     # IDialogMemoryStore
        │   ├── state_store.py      # IStateMemoryStore
        │   ├── semantic_store.py   # ISemanticMemoryStore
        │   ├── procedural_store.py # IProceduralMemoryStore
        │   ├── profile_store.py    # IProfileMemoryStore
        │   └── experience_store.py # IExperienceMemoryStore

        # 4) Stores: implementation theo backend cụ thể
        ├── stores/
        │   ├── __init__.py
        │   ├── in_memory/
        │   │   ├── __init__.py
        │   │   ├── dialog_in_memory.py
        │   │   ├── state_in_memory.py
        │   │   ├── semantic_in_memory.py
        │   │   ├── procedural_in_memory.py
        │   │   ├── profile_in_memory.py
        │   │   └── experience_in_memory.py
        │   ├── postgres/
        │   │   ├── __init__.py
        │   │   ├── dialog_postgres.py
        │   │   ├── state_postgres.py
        │   │   ├── profile_postgres.py
        │   │   └── experience_postgres.py
        │   ├── vector/
        │   │   ├── __init__.py
        │   │   ├── semantic_pgvector.py
        │   │   ├── semantic_milvus.py
        │   │   └── semantic_opensearch.py
        │   └── procedural/
        │       ├── __init__.py
        │       ├── sop_postgres.py      # lưu SOP/skill ở bảng riêng
        │       └── sop_acontext_adapter.py  # optional: bridge tới Acontext nếu dùng

        # 5) Facade: entrypoint mà Flow/Node sẽ dùng
        ├── facade/
        │   ├── __init__.py
        │   └── memory_facade.py     # MemoryFacade implements IMemory, route đến các store

        # 6) Experience & learning: agent nền trích SOP / lesson
        ├── experience/
        │   ├── __init__.py
        │   ├── experience_agent.py  # đọc ExperienceStore để trích lesson
        │   ├── sop_extractor.py     # logic LLM để convert traces -> SOP/Skill
        │   └── rules_engine.py      # (optional) suy ra rule từ error pattern

        # 7) Adapters: tích hợp ecosystem bên ngoài
        ├── adapters/
        │   ├── __init__.py
        │   ├── acontext_adapter.py  # map IMemory <-> Acontext API
        │   ├── langchain_adapter.py # nếu muốn wrap nó thành LC Memory
        │   └── langgraph_adapter.py # helper hook cho LangGraph state-first

        # 8) Utils: helper chung
        ├── utils/
        │   ├── __init__.py
        │   ├── logging.py           # logger chuẩn cho memory layer
        │   ├── time.py              # helper về timestamp, TTL
        │   └── serialization.py     # chuẩn hóa json/bytes/uuid

        # 9) Tests (nếu để cạnh package)
        └── tests/
            ├── __init__.py
            ├── test_memory_facade.py
            ├── test_dialog_store_in_memory.py
            ├── test_semantic_store_pgvector.py
            ├── test_procedural_store_postgres.py
            └── test_experience_agent.py


Cách dùng trong các service khác

Ở các service (orchestrator / flow / agent), bạn chỉ cần import từ facade:

# apps/orchestrator/src/deps/memory.py
from memory_core.facade.memory_facade import MemoryFacade
from memory_core.stores.in_memory import dialog_in_memory, state_in_memory
from memory_core.stores.vector.semantic_pgvector import PgVectorSemanticStore
from memory_core.stores.procedural.sop_postgres import PostgresSOPStore

memory = MemoryFacade(
    dialog_store=dialog_in_memory.InMemoryDialogStore(...),
    state_store=state_in_memory.InMemoryStateStore(...),
    semantic_store=PgVectorSemanticStore(...),
    procedural_store=PostgresSOPStore(...),
    profile_store=...,
    experience_store=...,
)


Sau đó trong Flow/Node:

from memory_core.models.base import MemoryQuery, MemoryScope
from deps.memory import memory

mem_results = await memory.read(MemoryQuery(
    user_id=user_id,
    session_id=session_id,
    agent_id="planner",
    flow_id=flow_id,
    scopes=[MemoryScope.DIALOG, MemoryScope.SEMANTIC, MemoryScope.PROCEDURAL],
    query=user_utterance,
))
