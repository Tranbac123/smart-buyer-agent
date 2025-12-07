# packages/control_plane/core.py

import inspect
from typing import Any, Callable, Dict, Optional, Protocol
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pydantic import BaseModel, Field


from .policy import PolicyEngine, PolicyStore


class PlanStep(BaseModel):
    action: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)


class RequestContext(BaseModel):
    request_id: str
    user_id: Optional[str] = None
    org_id: Optional[str] = None
    flow_name: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    success: bool
    action: str
    data: Any = None
    error: Optional[str] = None
    started_at: datetime
    finished_at: datetime
    latency_ms: int
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    org_id: Optional[str] = None
    flow_name: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)


class ToolHandler(Protocol):
    def __call__(self, **kwargs: Any) -> Any:
        ...


@dataclass
class ToolSpec:
    name: str
    handler: ToolHandler
    description: str = ""
    input_schema: Optional[type[BaseModel]] = None
    output_schema: Optional[type[BaseModel]] = None
    allowed_orgs: Optional[list[str]] = None
    tags: list[str] = field(default_factory=list)
    pass_context: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        key = spec.name
        if key in self._tools:
            raise ValueError(f"Tool '{key}' already registered")
        self._tools[key] = spec

    def get(self, name: str) -> ToolSpec:
        if name not in self._tools:
            raise KeyError(f"Unknown tool '{name}'")
        return self._tools[name]

    def exists(self, name: str) -> bool:
        return name in self._tools


class ExecutionLogger(Protocol):
    def __call__(self, record: ToolResult) -> None:
        ...


class PrintExecutionLogger:
    def __call__(self, record: ToolResult) -> None:
        print(
            f"[CONTROL_PLANE] tool={record.action} "
            f"success={record.success} "
            f"latency_ms={record.latency_ms} "
            f"request_id={record.request_id} "
            f"user_id={record.user_id} "
            f"org_id={record.org_id}"
        )


class ControlPlane:
    def __init__(
        self,
        *,
        registry: ToolRegistry,
        policy_engine: Optional[PolicyEngine] = None,
        execution_logger: Optional[ExecutionLogger] = None,
    ) -> None:
        self._registry = registry
        self._policy = policy_engine or PolicyEngine(policy_store=PolicyStore())
        self._log = execution_logger or PrintExecutionLogger()

    async def execute(self, step: PlanStep, ctx: RequestContext) -> ToolResult:
        started_at = datetime.now(timezone.utc)
        error_type: Optional[str] = None
        try:
            spec = self._registry.get(step.action)
            self._policy.validate_tool_allowed(spec, ctx)
            self._policy.validate_quota(spec, ctx, tokens_used=0)
            safe_params = self._policy.sanitize_parameters(spec, step.parameters)
            handler_kwargs = safe_params if not spec.pass_context else dict(safe_params)
            if spec.pass_context:
                handler_kwargs["request_ctx"] = ctx
            maybe_result = spec.handler(**handler_kwargs)
            if inspect.isawaitable(maybe_result):
                raw_result = await maybe_result  # type: ignore[assignment]
            else:
                raw_result = maybe_result
            data = self._policy.validate_output(spec, raw_result)
            success = True
            error_msg = None
        except Exception as e:
            success = False
            data = None
            error_msg = str(e)
            error_type = type(e).__name__

        finished_at = datetime.now(timezone.utc)
        latency_ms = int((finished_at - started_at).total_seconds() * 1000)

        result = ToolResult(
            success=success,
            action=step.action,
            data=data,
            error=error_msg,
            started_at=started_at,
            finished_at=finished_at,
            latency_ms=latency_ms,
            request_id=ctx.request_id,
            user_id=ctx.user_id,
            org_id=ctx.org_id,
            flow_name=ctx.flow_name,
            extra={
                "step_context": step.context,
                **({"error_type": error_type} if error_type else {}),
            },
        )

        self._log(result)
        return result
