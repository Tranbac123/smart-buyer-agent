from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Protocol, runtime_checkable

from packages.agent_core.agent_core.models import AgentState
from packages.tools.tools.registry import ToolRegistry
from packages.llm_client.llm_client.base import ILLMClient
from packages.memory_core.memory_core.base import IMemory


logger = logging.getLogger("quantumx.orchestrator.agent_runner")


@runtime_checkable
class FlowLike(Protocol):
    name: str

    async def run(self, state: AgentState) -> AgentState:
        ...


class RunnerRetryableError(Exception):
    pass


@runtime_checkable
class IContextStore(Protocol):
    async def load(self, thread_id: str) -> Dict[str, Any]:
        ...

    async def save(self, thread_id: str, context: Dict[str, Any]) -> None:
        ...


@dataclass
class AgentRunConfig:
    timeout_s: float = 60.0
    max_retries: int = 1
    backoff_base_s: float = 0.5
    backoff_max_s: float = 5.0
    trace_sample_rate: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentRunResult:
    state: AgentState
    trace_id: str
    flow_name: str
    duration_s: float
    timed_out: bool
    retries: int


class AgentRunner:
    def __init__(
        self,
        *,
        tools: ToolRegistry,
        llm: ILLMClient,
        memory: Optional[IMemory] = None,
        context_store: Optional[IContextStore] = None,
        max_concurrent: int = 16,
        default_timeout_s: float = 60.0,
        default_max_retries: int = 1,
        logger_: Optional[logging.Logger] = None,
    ) -> None:
        self.tools = tools
        self.llm = llm
        self.memory = memory
        self.context_store = context_store
        self._sema = asyncio.Semaphore(max_concurrent)
        self._default_timeout_s = default_timeout_s
        self._default_max_retries = default_max_retries
        self._logger = logger_ or logger

    async def run(
        self,
        *,
        flow: FlowLike,
        state: AgentState,
        thread_id: Optional[str] = None,
        config: Optional[AgentRunConfig] = None,
    ) -> AgentRunResult:
        run_cfg = config or AgentRunConfig(
            timeout_s=self._default_timeout_s,
            max_retries=self._default_max_retries,
        )

        trace_id = _extract_or_set_trace_id(state)
        flow_name = getattr(flow, "name", flow.__class__.__name__)
        started_at = time.perf_counter()

        self._logger.info(
            "agent_run.start",
            extra={
                "trace_id": trace_id,
                "flow": flow_name,
                "thread_id": thread_id,
                "timeout_s": run_cfg.timeout_s,
                "max_retries": run_cfg.max_retries,
                "metadata": run_cfg.metadata,
            },
        )

        if self.context_store and thread_id:
            await self._attach_context(state, thread_id, trace_id)

        async with self._sema:
            result_state, timed_out, retries_used = await self._run_with_retry(
                flow=flow,
                state=state,
                trace_id=trace_id,
                flow_name=flow_name,
                timeout_s=run_cfg.timeout_s,
                max_retries=run_cfg.max_retries,
                backoff_base_s=run_cfg.backoff_base_s,
                backoff_max_s=run_cfg.backoff_max_s,
            )

        if self.context_store and thread_id:
            await self._persist_context(result_state, thread_id, trace_id)

        duration_s = time.perf_counter() - started_at

        self._logger.info(
            "agent_run.end",
            extra={
                "trace_id": trace_id,
                "flow": flow_name,
                "thread_id": thread_id,
                "duration_s": duration_s,
                "timed_out": timed_out,
                "retries_used": retries_used,
            },
        )

        return AgentRunResult(
            state=result_state,
            trace_id=trace_id,
            flow_name=flow_name,
            duration_s=duration_s,
            timed_out=timed_out,
            retries=retries_used,
        )

    async def _run_with_retry(
        self,
        *,
        flow: FlowLike,
        state: AgentState,
        trace_id: str,
        flow_name: str,
        timeout_s: float,
        max_retries: int,
        backoff_base_s: float,
        backoff_max_s: float,
    ) -> tuple[AgentState, bool, int]:
        attempt = 0
        last_exc: Optional[BaseException] = None
        timed_out = False

        while attempt <= max_retries:
            attempt += 1
            try:
                self._logger.debug(
                    "agent_run.attempt",
                    extra={
                        "trace_id": trace_id,
                        "flow": flow_name,
                        "attempt": attempt,
                        "timeout_s": timeout_s,
                    },
                )
                result_state = await asyncio.wait_for(flow.run(state), timeout=timeout_s)
                return result_state, False, attempt - 1
            except asyncio.TimeoutError as exc:
                timed_out = True
                last_exc = exc
                self._logger.warning(
                    "agent_run.timeout",
                    extra={
                        "trace_id": trace_id,
                        "flow": flow_name,
                        "attempt": attempt,
                        "timeout_s": timeout_s,
                    },
                )
            except RunnerRetryableError as exc:
                last_exc = exc
                self._logger.warning(
                    "agent_run.retryable_error",
                    extra={
                        "trace_id": trace_id,
                        "flow": flow_name,
                        "attempt": attempt,
                        "exc_type": type(exc).__name__,
                        "message": str(exc),
                    },
                )
            except Exception as exc:
                last_exc = exc
                self._logger.exception(
                    "agent_run.error",
                    extra={
                        "trace_id": trace_id,
                        "flow": flow_name,
                        "attempt": attempt,
                        "exc_type": type(exc).__name__,
                    },
                )
                break

            if attempt > max_retries:
                break

            backoff = min(backoff_max_s, backoff_base_s * (2 ** (attempt - 1)))
            await asyncio.sleep(backoff)

        assert last_exc is not None
        raise last_exc

    async def _attach_context(
        self,
        state: AgentState,
        thread_id: str,
        trace_id: str,
    ) -> None:
        try:
            ctx = await self.context_store.load(thread_id)  # type: ignore[union-attr]
        except Exception as exc:
            self._logger.warning(
                "agent_run.context_load_failed",
                extra={
                    "trace_id": trace_id,
                    "thread_id": thread_id,
                    "exc_type": type(exc).__name__,
                    "message": str(exc),
                },
            )
            return

        if not ctx:
            return

        if hasattr(state, "facts") and isinstance(getattr(state, "facts"), dict):
            state.facts = dict(state.facts or {})
            state.facts.setdefault("context", ctx)
        elif hasattr(state, "context"):
            setattr(state, "context", ctx)

        self._logger.debug(
            "agent_run.context_attached",
            extra={"trace_id": trace_id, "thread_id": thread_id},
        )

    async def _persist_context(
        self,
        state: AgentState,
        thread_id: str,
        trace_id: str,
    ) -> None:
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

        try:
            await self.context_store.save(thread_id, ctx)  # type: ignore[union-attr]
            self._logger.debug(
                "agent_run.context_saved",
                extra={"trace_id": trace_id, "thread_id": thread_id},
            )
        except Exception as exc:
            self._logger.warning(
                "agent_run.context_save_failed",
                extra={
                    "trace_id": trace_id,
                    "thread_id": thread_id,
                    "exc_type": type(exc).__name__,
                    "message": str(exc),
                },
            )


def _extract_or_set_trace_id(state: AgentState) -> str:
    if hasattr(state, "trace_id"):
        existing = getattr(state, "trace_id")
        if isinstance(existing, str) and existing:
            return existing

    trace_id = uuid.uuid4().hex

    if hasattr(state, "trace_id"):
        try:
            setattr(state, "trace_id", trace_id)
        except Exception:
            pass

    if hasattr(state, "facts") and isinstance(getattr(state, "facts"), dict):
        facts = dict(state.facts or {})
        facts.setdefault("trace_id", trace_id)
        state.facts = facts

    return trace_id
