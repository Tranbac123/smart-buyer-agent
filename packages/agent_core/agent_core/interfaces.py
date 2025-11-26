# packages/agent_core/agent_core/interfaces.py
from __future__ import annotations

"""
Interfaces & type contracts used across the Agent stack.

Design goals:
- Keep this module dependency-free (no imports from other project modules) to avoid cycles.
- Provide narrow, async-first Protocols that are easy to mock in tests.
- Use light TypedDicts to standardize payload shapes between layers (tools, decision, retrieval…).
"""

from typing import (
    Any,
    AsyncIterable,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Protocol,
    TypedDict,
    Union,
    runtime_checkable,
)

# ------------------------------------------------------------------------------
# Common domain shapes (TypedDict) — keep minimal to avoid over-coupling
# ------------------------------------------------------------------------------

class OfferTD(TypedDict, total=False):
    """Normalized e-commerce offer."""
    id: str
    site: str
    title: str
    price: Union[int, float]
    currency: str
    url: str
    shipping: Optional[str]
    in_stock: Optional[bool]
    # Extra domain-specific fields are allowed:
    # seller, rating, warranty, images, attributes, etc.


class CriterionTD(TypedDict, total=False):
    """Multi-criteria decision criterion."""
    name: str
    weight: float           # [0..1]
    maximize: bool          # True => higher is better
    description: Optional[str]


class OptionCriterionScoreTD(TypedDict, total=False):
    raw_value: Any
    normalized_value: float
    weight: float
    weighted_score: float


class OptionScoreTD(TypedDict, total=False):
    """Per-option scoring bundle."""
    option_id: Optional[str]
    rank: Optional[int]
    total_score: Optional[float]
    criterion_scores: Mapping[str, OptionCriterionScoreTD]


class ScoringBundleTD(TypedDict, total=False):
    """Top-level scoring envelope consumed by Explain/Finalize nodes."""
    confidence: float
    option_scores: List[OptionScoreTD]
    best: Optional[str]


class TradeoffTD(TypedDict, total=False):
    criterion: str
    better_option: Optional[str]
    difference: float


class PerOptionBulletTD(TypedDict, total=False):
    option_id: Optional[str]
    pros: List[str]
    cons: List[str]
    note: Optional[str]


class BestByCriterionTD(TypedDict, total=False):
    option_id: Optional[str]
    value: Optional[float]
    title: Optional[str]


class ExplanationTD(TypedDict, total=False):
    """Human-facing explanation payload."""
    winner: Optional[str]
    confidence: float
    best_by_criterion: Mapping[str, BestByCriterionTD]
    tradeoffs: List[TradeoffTD]
    per_option: List[PerOptionBulletTD]
    summary: str


# Generic tool I/O shapes
ToolPayload = Dict[str, Any]
ToolResult = Dict[str, Any]


# ------------------------------------------------------------------------------
# LLM client
# ------------------------------------------------------------------------------

@runtime_checkable
class ILLMClient(Protocol):
    """
    Minimal async LLM client.
    Keep the surface area small; wrap provider-specific features inside your implementation.
    """

    async def complete(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        response_format: Optional[str] = None,
        stop: Optional[List[str]] = None,
    ) -> Any:
        """
        Return a single-shot completion. Shape of the return value is implementation-defined
        (string, dict, or provider-native object). Callers should wrap it if they require a strict type.
        """
        ...

    # Optional streaming interface (implement if supported)
    async def stream_complete(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        response_format: Optional[str] = None,
        stop: Optional[List[str]] = None,
    ) -> AsyncIterable[Any]:
        """Yield streaming chunks (text tokens or provider-native deltas)."""
        ...


# ------------------------------------------------------------------------------
# Tools registry & tool abstraction
# ------------------------------------------------------------------------------

@runtime_checkable
class ITool(Protocol):
    """Every tool must expose an async call with a dict payload/result."""

    async def call(self, payload: ToolPayload) -> ToolResult:
        ...


@runtime_checkable
class IToolRegistry(Protocol):
    """
    Registry for tools. Implementations typically hold a {name: ITool} map,
    provide registration, and a convenience async call.
    """

    def register(self, name: str, tool: ITool) -> None:
        ...

    def get(self, name: str) -> ITool:
        ...

    async def call(self, name: str, payload: ToolPayload) -> ToolResult:
        ...


# ------------------------------------------------------------------------------
# Memory (short/long-term)
# ------------------------------------------------------------------------------

@runtime_checkable
class IMemory(Protocol):
    """Abstract key-value memory with optional TTL and snapshot support."""

    async def get(self, key: str) -> Any:
        ...

    async def set(self, key: str, value: Any, ttl_s: Optional[int] = None) -> None:
        ...

    async def delete(self, key: str) -> None:
        ...

    async def snapshot(self, session_id: str) -> Dict[str, Any]:
        """
        Return a compact snapshot for a session/context, to be injected into AgentState.
        Implementations may decide what to include (e.g., preferences, last winner, etc.).
        """
        ...


# ------------------------------------------------------------------------------
# Retrieval/RAG contracts (optional but useful for growth)
# ------------------------------------------------------------------------------

@runtime_checkable
class IRetriever(Protocol):
    """
    Retrieve relevant documents for a query.
    Each document is a simple dict with fields like: {id, text, score, source, metadata}
    """

    async def retrieve(
        self,
        query: str,
        k: int = 8,
        filters: Optional[Mapping[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        ...


@runtime_checkable
class IReranker(Protocol):
    """
    Rerank documents returned by a retriever.
    Input: (query, docs)
    Output: top_k docs in a new order with updated scores
    """

    async def rerank(
        self,
        query: str,
        docs: List[Dict[str, Any]],
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        ...


@runtime_checkable
class ICompressor(Protocol):
    """
    Compress/summarize documents to fit a token budget.
    Return reduced documents (e.g., extracted passages) while preserving attribution.
    """

    async def compress(
        self,
        docs: List[Dict[str, Any]],
        max_tokens: int,
    ) -> List[Dict[str, Any]]:
        ...


@runtime_checkable
class IVectorStore(Protocol):
    """
    Optional vector store contract for indexing & similarity search.
    Keep intentionally small; adapt in your concrete implementation.
    """

    async def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Mapping[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """Return stored IDs (provided or generated)."""
        ...

    async def similarity_search(
        self,
        query: str,
        k: int = 8,
        filters: Optional[Mapping[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        ...


# ------------------------------------------------------------------------------
# Policy / Guard interfaces (optional — plug into orchestrator/graph guards)
# ------------------------------------------------------------------------------

@runtime_checkable
class IPolicy(Protocol):
    """Generic policy for budget/latency/step-safety checks."""

    def allow_step(self, *, step_index: int, spent_tokens: int, budget_tokens: int) -> bool:
        ...

    def allow_tool(self, *, tool_name: str) -> bool:
        ...


# ------------------------------------------------------------------------------
# Convenience union types used around the stack
# ------------------------------------------------------------------------------

JSONLike = Union[None, str, int, float, bool, Dict[str, Any], List[Any]]
DocLike = Dict[str, Any]
DocsLike = List[DocLike]
OptionsLike = List[OfferTD]
CriteriaLike = List[CriterionTD]
