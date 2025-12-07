from __future__ import annotations

from functools import lru_cache

from packages.control_plane.control_plane.core import ControlPlane, ToolRegistry
from packages.control_plane.control_plane.policy import (
    GlobalPolicy,
    OrgPolicy,
    PolicyEngine,
    PolicyStore,
    QuotaLimits,
    RolePolicy,
    SkillDefinition,
)
from packages.tools.tool_specs.price_compare_spec import register_price_compare_tool
from packages.tools.tool_specs.decision_spec import register_decision_tool
from packages.tools.tool_specs.scraper_spec import register_scraper_tool
from packages.tools.tool_specs.web_search_spec import register_web_search_tool


def _build_registry() -> ToolRegistry:
    registry = ToolRegistry()
    register_price_compare_tool(registry)
    register_decision_tool(registry)
    register_scraper_tool(registry)
    register_web_search_tool(registry)
    return registry


def _build_policy_engine() -> PolicyEngine:
    policy_store = PolicyStore(
        global_policy=GlobalPolicy(
            max_tools_per_request=8,
            default_allowed_tools={"health_check"},
        ),
        skills={
            "smart_buyer_basic": SkillDefinition(
                name="smart_buyer_basic",
                tools={"price_compare", "decision_score", "scraper_fetch", "web_search"},
            ),
        },
        orgs={
            "org_demo": OrgPolicy(
                org_id="org_demo",
                enabled_skills={"smart_buyer_basic"},
                quotas=QuotaLimits(
                    daily_calls=5_000,
                    per_tool_daily={
                        "price_compare": 2_000,
                        "decision_score": 2_000,
                        "scraper_fetch": 5_000,
                        "web_search": 5_000,
                    },
                ),
                roles={
                    "admin": RolePolicy(
                        name="admin",
                        allowed_skills={"smart_buyer_basic"},
                    ),
                    "viewer": RolePolicy(
                        name="viewer",
                        allowed_skills={"smart_buyer_basic"},
                    ),
                },
            )
        },
    )
    return PolicyEngine(policy_store=policy_store)


@lru_cache(maxsize=1)
def get_control_plane() -> ControlPlane:
    registry = _build_registry()
    policy_engine = _build_policy_engine()
    return ControlPlane(registry=registry, policy_engine=policy_engine)
