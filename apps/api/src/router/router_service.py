# apps/api/src/router/router_service.py
"""
Router Service
Intent router that dispatches requests to state-first services.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional, Protocol

# IMPORTANT: adjust import to your project layout
from apps.api.src.services.smart_buyer_service import SmartBuyerService


class Intent(Enum):
    """Supported user intents."""
    CHAT = "chat"
    SMART_BUYER = "smart_buyer"
    DEEP_RESEARCH = "deep_research"
    CODE_AGENT = "code_agent"


class IntentDetector(Protocol):
    async def detect(self, message: str, context: Optional[Dict[str, Any]] = None) -> Intent: ...


class KeywordIntentDetector:
    """
    Simple keyword-based detector (placeholder).
    Replace with LLM-based detector later if needed.
    """

    SMART_BUYER_KEYWORDS = {
        "giá", "price", "mua", "buy", "so sánh", "compare", "rẻ nhất", "cheapest",
        "tốt nhất", "best deal", "shopee", "lazada", "tiki", "deal", "khuyến mãi",
        "discount", "sản phẩm", "product", "hàng", "goods",
    }

    DEEP_RESEARCH_KEYWORDS = {
        "nghiên cứu", "research", "phân tích", "analyze",
        "tìm hiểu", "giải thích chi tiết", "summarize", "tổng hợp", "investigate",
    }

    CODE_AGENT_KEYWORDS = {
        "code", "lập trình", "programming", "debug", "fix bug", "viết code",
        "refactor", "optimize code", "function", "class", "algorithm",
    }

    async def detect(self, message: str, context: Optional[Dict[str, Any]] = None) -> Intent:
        msg = (message or "").lower()

        if any(k in msg for k in self.SMART_BUYER_KEYWORDS):
            return Intent.SMART_BUYER
        if any(k in msg for k in self.DEEP_RESEARCH_KEYWORDS):
            return Intent.DEEP_RESEARCH
        if any(k in msg for k in self.CODE_AGENT_KEYWORDS):
            return Intent.CODE_AGENT

        # Allow explicit override via context
        if context:
            explicit = context.get("intent") or context.get("flow_type")
            if explicit:
                try:
                    return Intent(explicit)
                except ValueError:
                    pass

        return Intent.CHAT


class RouterService:
    """
    Routes user messages to the appropriate state-first service.

    Today only Smart Buyer has a full state-first implementation.
    Other intents return placeholder responses until their flows are built.
    """

    def __init__(
        self,
        *,
        smart_buyer_service: SmartBuyerService,
        intent_detector: Optional[IntentDetector] = None,
    ) -> None:
        self.smart_buyer_service = smart_buyer_service
        self.intent_detector = intent_detector or KeywordIntentDetector()

    async def route(
        self,
        *,
        message: str,
        session_id: str,
        context: Optional[Dict[str, Any]] = None,
        intent: Optional[Intent] = None,
    ) -> Dict[str, Any]:
        ctx = context or {}
        detected_intent = intent or await self.intent_detector.detect(message, ctx)

        if detected_intent == Intent.SMART_BUYER:
            payload = await self._handle_smart_buyer(message=message, session_id=session_id, context=ctx)
        else:
            payload = self._placeholder_response(detected_intent, message)

        # Standard envelope for router responses
        return {
            "intent": detected_intent.value,
            "flow_type": detected_intent.value,
            "session_id": session_id,
            **payload,
        }

    # ------------------------------------------------------------------ #
    # Intent handlers
    # ------------------------------------------------------------------ #

    async def _handle_smart_buyer(
        self,
        *,
        message: str,
        session_id: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Map message/context → SmartBuyerService inputs.
        Keep this thin; orchestration lives in the service/flow.
        """
        query = context.get("query") or message
        top_k = int(context.get("top_k", 5))
        prefs = context.get("prefs")
        criteria = context.get("criteria")
        sites = context.get("sites")

        result = await self.smart_buyer_service.run(
            query=query,
            top_k=top_k,
            prefs=prefs,
            criteria=criteria,
            sites=sites,
            request_id=context.get("request_id") or session_id,
            timeout_s=context.get("timeout_s"),
            max_steps=context.get("max_steps"),
        )

        return {
            "type": Intent.SMART_BUYER.value,
            "payload": result,
            "metadata": {"status": "ok"},
        }

    # ------------------------------------------------------------------ #
    # Fallbacks
    # ------------------------------------------------------------------ #

    def _placeholder_response(self, intent: Intent, message: str) -> Dict[str, Any]:
        return {
            "type": intent.value,
            "payload": {
                "response": f"{intent.value} agent is not implemented yet.",
                "metadata": {"status": "not_implemented", "echo": message},
            },
            "metadata": {"status": "not_implemented"},
        }
