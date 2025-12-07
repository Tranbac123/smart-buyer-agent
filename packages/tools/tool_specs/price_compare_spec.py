# packages/tools/control_plane/price_compare_tool.py
from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field, validator

from packages.control_plane.control_plane.core import ToolRegistry, ToolSpec
from packages.search_core.search_core.ecommerce.price_compare_service import (
    PriceCompareEngine,
)


class PriceCompareInput(BaseModel):
    query: str = Field(min_length=2)
    max_items: int = Field(default=5, ge=1, le=20)
    sites: List[str] | None = None

    @validator("sites", each_item=True)
    def _normalize_site(cls, value: str) -> str:
        return value.strip().lower()


class PriceCompareOutput(BaseModel):
    items: List[Dict[str, Any]]
    metadata: Dict[str, Any] = Field(default_factory=dict)


_engine = PriceCompareEngine()


async def price_compare_handler(
    query: str,
    max_items: int = 5,
    sites: List[str] | None = None,
) -> Dict[str, Any]:
    result = await _engine.compare(query=query, top_k=max_items, sites=sites)
    return {
        "items": result.get("offers", []),
        "metadata": result.get("metadata", {}),
    }


def register_price_compare_tool(registry: ToolRegistry) -> None:
    spec = ToolSpec(
        name="price_compare",
        handler=price_compare_handler,
        description="Compare product prices across vendors.",
        input_schema=PriceCompareInput,
        output_schema=PriceCompareOutput,
        allowed_orgs=["org_demo", "org_premium"],
        tags=["product", "pricing"],
    )
    registry.register(spec)




