# packages/search_core/search_core/ecommerce/sites/shopee_adapter.py
from __future__ import annotations

import logging
from pydantic import BaseModel

class ShopeeOffer(BaseModel):
    """Normalized offer shape expected by PriceCompareEngine.
    Adjust fields to match your existing Offer model if you already have one.
    """
    