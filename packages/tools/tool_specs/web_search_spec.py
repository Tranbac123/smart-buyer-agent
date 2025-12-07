from __future__ import annotations

from typing import Any, Dict, Optional

from packages.control_plane.control_plane.core import (
    RequestContext,
    ToolRegistry,
    ToolSpec,
)
from packages.tools.tools.search_web import (
    WebSearchInput,
    WebSearchResult,
    WebSearchTool,
    build_web_search_tool,
)

_web_search_tool: Optional[WebSearchTool] = None


def _get_web_search_tool() -> WebSearchTool:
    global _web_search_tool
    if _web_search_tool is None:
        _web_search_tool = build_web_search_tool()
    return _web_search_tool


async def web_search_handler(
    query: str,
    num_results: int = 5,
    search_type: str = "search",
    gl: str = "vn",
    hl: str = "vi",
    use_cache: bool = True,
    cache_ttl_sec: Optional[int] = None,
    timeout_sec: Optional[int] = None,
    max_retries: Optional[int] = None,
    backoff_base_ms: Optional[int] = None,
    tag: Optional[str] = None,
    request_ctx: RequestContext | None = None,
) -> Dict[str, Any]:
    """
    Thin wrapper that forwards PlanStep parameters to the async WebSearchTool.
    """

    payload: Dict[str, Any] = {
        "query": query,
        "num_results": num_results,
        "search_type": search_type,
        "gl": gl,
        "hl": hl,
        "use_cache": use_cache,
    }

    optional_fields = {
        "cache_ttl_sec": cache_ttl_sec,
        "timeout_sec": timeout_sec,
        "max_retries": max_retries,
        "backoff_base_ms": backoff_base_ms,
        "tag": tag,
    }
    for key, value in optional_fields.items():
        if value is not None:
            payload[key] = value

    if request_ctx is not None:
        payload["_ctx"] = request_ctx

    tool = _get_web_search_tool()
    return await tool.call(payload)


def register_web_search_tool(
    registry: ToolRegistry,
    *,
    tool: Optional[WebSearchTool] = None,
) -> None:
    """
    Register the Serper-powered web_search tool inside the Control Plane registry.
    """

    global _web_search_tool
    if tool is not None:
        _web_search_tool = tool

    spec = ToolSpec(
        name="web_search",
        handler=web_search_handler,
        description="Search the public web via Serper.dev.",
        input_schema=WebSearchInput,
        output_schema=WebSearchResult,
        allowed_orgs=["org_demo", "org_premium"],
        tags=["search", "web"],
        pass_context=True,
    )
    registry.register(spec)


