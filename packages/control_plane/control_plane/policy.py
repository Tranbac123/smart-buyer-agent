# packages/control_plane/policy.py

from typing import Any, Dict, Optional, Protocol, TYPE_CHECKING
from datetime import date
from pydantic import BaseModel, Field, ValidationError

if TYPE_CHECKING:
    from .core import ToolSpec, RequestContext


class GlobalPolicy(BaseModel):
    max_tools_per_request: int = 8
    max_concurrent_requests_per_user: int = 10
    enforce_input_schema: bool = True
    default_allowed_tools: set[str] = Field(default_factory=set)
    default_blocked_tools: set[str] = Field(default_factory=set)


class QuotaLimits(BaseModel):
    daily_calls: Optional[int] = None
    per_tool_daily: Dict[str, int] = Field(default_factory=dict)
    daily_llm_tokens: Optional[int] = None


class RolePolicy(BaseModel):
    name: str
    allowed_tools: set[str] = Field(default_factory=set)
    blocked_tools: set[str] = Field(default_factory=set)
    allowed_skills: set[str] = Field(default_factory=set)


class OrgPolicy(BaseModel):
    org_id: str
    enabled_skills: set[str] = Field(default_factory=set)
    allowed_tools: set[str] = Field(default_factory=set)
    blocked_tools: set[str] = Field(default_factory=set)
    roles: Dict[str, RolePolicy] = Field(default_factory=dict)
    quotas: QuotaLimits = Field(default_factory=QuotaLimits)


class SkillDefinition(BaseModel):
    name: str
    tools: set[str] = Field(default_factory=set)


class PolicyStore(BaseModel):
    global_policy: GlobalPolicy = Field(default_factory=GlobalPolicy)
    orgs: Dict[str, OrgPolicy] = Field(default_factory=dict)
    skills: Dict[str, SkillDefinition] = Field(default_factory=dict)


class UsageSnapshot(BaseModel):
    date: date
    total_calls: int = 0
    per_tool_calls: Dict[str, int] = Field(default_factory=dict)
    total_llm_tokens: int = 0


class UsageTracker(Protocol):
    def increment(
        self,
        *,
        org_id: Optional[str],
        user_id: Optional[str],
        tool_name: str,
        tokens_used: int = 0,
    ) -> None:
        ...

    def get_daily_usage(
        self,
        *,
        org_id: Optional[str],
        user_id: Optional[str],
        day: date,
    ) -> UsageSnapshot:
        ...


class InMemoryUsageTracker:
    def __init__(self) -> None:
        self._data: Dict[tuple, UsageSnapshot] = {}

    def _key(self, org_id: Optional[str], user_id: Optional[str], day: date) -> tuple:
        return (org_id or "_", user_id or "_", day.isoformat())

    def increment(
        self,
        *,
        org_id: Optional[str],
        user_id: Optional[str],
        tool_name: str,
        tokens_used: int = 0,
    ) -> None:
        today = date.today()
        key = self._key(org_id, user_id, today)
        snap = self._data.get(key)
        if snap is None:
            snap = UsageSnapshot(date=today)
        snap.total_calls += 1
        snap.total_llm_tokens += max(tokens_used, 0)
        snap.per_tool_calls[tool_name] = snap.per_tool_calls.get(tool_name, 0) + 1
        self._data[key] = snap

    def get_daily_usage(
        self,
        *,
        org_id: Optional[str],
        user_id: Optional[str],
        day: date,
    ) -> UsageSnapshot:
        key = self._key(org_id, user_id, day)
        snap = self._data.get(key)
        if snap is None:
            snap = UsageSnapshot(date=day)
            self._data[key] = snap
        return snap


class PolicyEngine:
    def __init__(
        self,
        policy_store: PolicyStore,
        usage_tracker: Optional[UsageTracker] = None,
    ) -> None:
        self.store = policy_store
        self.usage = usage_tracker or InMemoryUsageTracker()

    def _resolve_org_policy(self, ctx: "RequestContext") -> OrgPolicy:
        org_id = ctx.org_id or "default"
        org = self.store.orgs.get(org_id)
        if org is None:
            org = OrgPolicy(org_id=org_id)
            self.store.orgs[org_id] = org
        return org

    def _resolve_role_policy(self, org: OrgPolicy, ctx: "RequestContext") -> Optional[RolePolicy]:
        role_name = ctx.metadata.get("role")
        if not role_name:
            return None
        return org.roles.get(role_name)

    def _tools_from_skills(self, org: OrgPolicy) -> set[str]:
        tools: set[str] = set()
        for skill_name in org.enabled_skills:
            skill = self.store.skills.get(skill_name)
            if skill:
                tools.update(skill.tools)
        return tools

    def _compute_allowed_tools(self, org: OrgPolicy, role: Optional[RolePolicy]) -> set[str]:
        g = self.store.global_policy
        allowed = set(g.default_allowed_tools)
        allowed.update(org.allowed_tools)
        allowed.update(self._tools_from_skills(org))
        if role:
            allowed.update(role.allowed_tools)
            for skill_name in role.allowed_skills:
                skill = self.store.skills.get(skill_name)
                if skill:
                    allowed.update(skill.tools)
        blocked = set(g.default_blocked_tools)
        blocked.update(org.blocked_tools)
        if role:
            blocked.update(role.blocked_tools)
        return allowed - blocked

    def validate_tool_allowed(self, tool: "ToolSpec", ctx: "RequestContext") -> None:
        org = self._resolve_org_policy(ctx)
        role = self._resolve_role_policy(org, ctx)
        allowed_tools = self._compute_allowed_tools(org, role)
        if tool.name not in allowed_tools:
            org_id = ctx.org_id or "default"
            role_name = ctx.metadata.get("role") or "anonymous"
            raise PermissionError(
                f"Tool '{tool.name}' is not allowed for org='{org_id}', role='{role_name}'"
            )

    def validate_quota(
        self,
        tool: "ToolSpec",
        ctx: "RequestContext",
        *,
        tokens_used: int = 0,
    ) -> None:
        org = self._resolve_org_policy(ctx)
        limits = org.quotas
        today = date.today()
        usage = self.usage.get_daily_usage(org_id=ctx.org_id, user_id=ctx.user_id, day=today)

        if limits.daily_calls is not None and usage.total_calls >= limits.daily_calls:
            raise RuntimeError(
                f"Daily tool-call quota exceeded for org '{org.org_id}'"
            )

        if limits.daily_llm_tokens is not None and usage.total_llm_tokens + tokens_used > limits.daily_llm_tokens:
            raise RuntimeError(
                f"Daily LLM token quota exceeded for org '{org.org_id}'"
            )

        if limits.per_tool_daily:
            max_calls = limits.per_tool_daily.get(tool.name)
            if max_calls is not None:
                current = usage.per_tool_calls.get(tool.name, 0)
                if current >= max_calls:
                    raise RuntimeError(
                        f"Daily quota exceeded for tool '{tool.name}' in org '{org.org_id}'"
                    )

        self.usage.increment(
            org_id=ctx.org_id,
            user_id=ctx.user_id,
            tool_name=tool.name,
            tokens_used=tokens_used,
        )

    def sanitize_parameters(
        self,
        tool: "ToolSpec",
        parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        g = self.store.global_policy
        if not g.enforce_input_schema or tool.input_schema is None:
            return parameters
        try:
            model = tool.input_schema(**parameters)
        except ValidationError as e:
            raise ValueError(f"Invalid parameters for tool '{tool.name}': {e}")
        return model.dict()

    def validate_output(self, tool: "ToolSpec", result: Any) -> Any:
        if tool.output_schema is None:
            return result
        return tool.output_schema.parse_obj(result)
