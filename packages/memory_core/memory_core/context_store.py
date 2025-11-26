from __future__ import annotations

import abc
import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Protocol, runtime_checkable

from packages.agent_core.agent_core.models import AgentState


logger = logging.getLogger("quantumx.memory.context_store")


@runtime_checkable
class IContextStore(Protocol):
    async def load(self, thread_id: str) -> Dict[str, Any]:
        ...

    async def save(self, thread_id: str, context: Dict[str, Any]) -> None:
        ...

    async def load_into_state(self, thread_id: str, state: AgentState) -> AgentState:
        ...

    async def persist_from_state(self, thread_id: str, state: AgentState) -> None:
        ...


class BaseContextStore(IContextStore, abc.ABC):
    async def load_into_state(self, thread_id: str, state: AgentState) -> AgentState:
        ctx = await self.load(thread_id)
        if not ctx:
            return state

        if hasattr(state, "facts") and isinstance(getattr(state, "facts"), dict):
            facts = dict(state.facts or {})
            facts["context"] = ctx
            state.facts = facts
        elif hasattr(state, "context"):
            setattr(state, "context", ctx)

        return state

    async def persist_from_state(self, thread_id: str, state: AgentState) -> None:
        ctx: Optional[Dict[str, Any]] = None

        if hasattr(state, "context"):
            maybe_ctx = getattr(state, "context")
            if isinstance(maybe_ctx, dict):
                ctx = maybe_ctx

        if ctx is None and hasattr(state, "facts"):
            facts = getattr(state, "facts")
            if isinstance(facts, dict):
                maybe_ctx = facts.get("context")
                if isinstance(maybe_ctx, dict):
                    ctx = maybe_ctx

        if ctx is None:
            return

        await self.save(thread_id, ctx)


class InMemoryContextStore(BaseContextStore):
    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def load(self, thread_id: str) -> Dict[str, Any]:
        async with self._lock:
            return dict(self._store.get(thread_id, {}))

    async def save(self, thread_id: str, context: Dict[str, Any]) -> None:
        async with self._lock:
            self._store[thread_id] = dict(context)


class JsonFileContextStore(BaseContextStore):
    def __init__(self, root_dir: str | Path) -> None:
        self._root = Path(root_dir)
        self._root.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    def _path_for(self, thread_id: str) -> Path:
        safe_id = thread_id.replace("/", "_").replace("\\", "_")
        return self._root / f"{safe_id}.json"

    async def load(self, thread_id: str) -> Dict[str, Any]:
        path = self._path_for(thread_id)
        if not path.exists():
            return {}

        async with self._lock:
            try:
                data = path.read_text(encoding="utf-8")
                if not data.strip():
                    return {}
                import json

                raw = json.loads(data)
                if isinstance(raw, dict):
                    return raw
                return {}
            except Exception as exc:
                logger.warning(
                    "context_store.json.load_failed",
                    extra={
                        "thread_id": thread_id,
                        "path": str(path),
                        "exc_type": type(exc).__name__,
                        "message": str(exc),
                    },
                )
                return {}

    async def save(self, thread_id: str, context: Dict[str, Any]) -> None:
        path = self._path_for(thread_id)
        async with self._lock:
            try:
                import json

                tmp_path = path.with_suffix(".json.tmp")
                tmp_path.write_text(
                    json.dumps(context, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                tmp_path.replace(path)
            except Exception as exc:
                logger.warning(
                    "context_store.json.save_failed",
                    extra={
                        "thread_id": thread_id,
                        "path": str(path),
                        "exc_type": type(exc).__name__,
                        "message": str(exc),
                    },
                )
