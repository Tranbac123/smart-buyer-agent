from __future__ import annotations

from typing import Any, Dict, List

from packages.control_plane.control_plane.core import RequestContext, ToolRegistry, ToolSpec
from packages.tools.tools.scraper_tool import ScraperBatchInput, ScraperBatchResult, ScraperTool

_scraper_tool = ScraperTool()


async def scraper_fetch_handler(
    requests: List[Dict[str, Any]],
    request_ctx: RequestContext | None = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"requests": requests}
    if request_ctx is not None:
        payload["_ctx"] = request_ctx
    return await _scraper_tool.call(payload)


def register_scraper_tool(registry: ToolRegistry) -> None:
    spec = ToolSpec(
        name="scraper_fetch",
        handler=scraper_fetch_handler,
        description="Fetch multiple HTTP resources with retries, caching, and telemetry.",
        input_schema=ScraperBatchInput,
        output_schema=ScraperBatchResult,
        allowed_orgs=["org_demo", "org_premium"],
        tags=["http", "scraper", "fetch"],
        pass_context=True,
    )
    registry.register(spec)


