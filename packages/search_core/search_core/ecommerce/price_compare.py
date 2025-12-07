# Backwards-compatible shim for legacy imports.
from .price_compare_service import (
    PriceCompareEngine,
    EcommercePriceCompareService as PriceCompare,
)

__all__ = ["PriceCompareEngine", "PriceCompare"]
