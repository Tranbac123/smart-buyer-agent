# apps/api/src/api/routes/smart_buyer.py
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field, conint, conlist

from dependencies.tools_provider import get_tool_registry
from dependencies.llm_provider import get_llm
from dependencies.http_client_provider import get_http_client
from dependencies.orchestrator_provider import get_orchestrator_service
from services.orchestrator_service import OrchestratorService


router = APIRouter(tags=["smart-buyer"])


class CriterionIn(BaseModel):
    name: str
    weight: float = Field(gt=0)
    maximize: bool = True
    description: Optional[str] = None


class PreferencesIn(BaseModel):
    budget: Optional[Decimal] = None
    required_tags: Optional[List[str]] = None
    option_label: Optional[str] = None


class SmartBuyerRequest(BaseModel):
    query: str = Field(min_length=2)
    top_k: conint(ge=1, le=20) = 6
    prefs: Optional[PreferencesIn] = None
    criteria: Optional[conlist(CriterionIn, min_length=1)] = None


class OfferOut(BaseModel):
    id: Optional[str] = None
    site: str
    title: str
    price: Decimal
    url: str
    currency: str = "VND"
    rating: Optional[float] = None
    shop_name: Optional[str] = None
    tags: Optional[List[str]] = None


class OptionScoreOut(BaseModel):
    option_id: str
    total_score: float
    rank: int


class ScoringOut(BaseModel):
    best: Optional[str] = None
    confidence: float = 0.0
    option_scores: List[OptionScoreOut] = Field(default_factory=list)


class ExplanationOut(BaseModel):
    winner: Optional[str] = None
    confidence: float = 0.0
    best_by_criterion: Dict[str, Any] = Field(default_factory=dict)
    tradeoffs: List[str] = Field(default_factory=list)
    per_option: List[Dict[str, Any]] = Field(default_factory=list)
    summary: str = ""


class SmartBuyerResponse(BaseModel):
    request_id: str
    query: str
    latency_ms: int
    offers: List[OfferOut]
    scoring: ScoringOut
    explanation: ExplanationOut
    metadata: Dict[str, Any] = Field(default_factory=dict)
    summary_text: Optional[str] = None
<<<<<<< Updated upstream
=======


class ChatMessageOut(BaseModel):
    id: str
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: datetime
    metadata: Optional[Dict[str, Any]] = None


class SmartBuyerChatRequest(BaseModel):
    message: str = Field(min_length=2)
    conversation_id: Optional[str] = None
    top_k: conint(ge=1, le=20) = 6
    prefs: Optional[PreferencesIn] = None
    criteria: Optional[conlist(CriterionIn, min_length=1)] = None


class SmartBuyerChatResponse(BaseModel):
    conversation_id: str
    messages: List[ChatMessageOut]
    offers: List[OfferOut]
    scoring: ScoringOut
    explanation: ExplanationOut
    metadata: Dict[str, Any] = Field(default_factory=dict)
    summary_text: Optional[str] = None
>>>>>>> Stashed changes


def _correlation_id(x_request_id: Optional[str]) -> str:
    return x_request_id or uuid.uuid4().hex


@router.post("/smart-buyer", response_model=SmartBuyerResponse, status_code=status.HTTP_200_OK)
async def smart_buyer(
    req: SmartBuyerRequest,
    request: Request,
    svc: OrchestratorService = Depends(get_orchestrator_service),
    tools=Depends(get_tool_registry),
    llm=Depends(get_llm),
    http=Depends(get_http_client),
    x_request_id: Optional[str] = Header(default=None, convert_underscores=True),
):
    started = time.perf_counter()
    rid = _correlation_id(x_request_id)

    user_id = request.headers.get("x-user-id")
    org_id = request.headers.get("x-org-id")
    role = request.headers.get("x-user-role")
    channel = request.headers.get("x-channel") or "web"

    try:
        result = await svc.run_smart_buyer(
            query=req.query,
            top_k=req.top_k,
            prefs=req.prefs.model_dump() if req.prefs else None,
            criteria=[c.model_dump() for c in req.criteria] if req.criteria else None,
            tools=tools,
            llm=llm,
            http=http,
            request_id=rid,
            user_id=user_id,
            org_id=org_id,
            role=role,
            channel=channel,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={"request_id": rid, "error": type(e).__name__})

    latency_ms = int((time.perf_counter() - started) * 1000)

    (
        offers,
        scoring,
        explanation,
        metadata,
    ) = _parse_smart_buyer_payload(result, req.top_k)

    halt_reason = metadata.get("halt_reason") or metadata.get("error")
    if halt_reason:
        status_map = {
            "quota_exceeded": status.HTTP_429_TOO_MANY_REQUESTS,
            "tool_blocked": status.HTTP_403_FORBIDDEN,
            "skill_not_allowed": status.HTTP_403_FORBIDDEN,
            "tool_error": status.HTTP_502_BAD_GATEWAY,
        }
        raise HTTPException(
            status_code=status_map.get(halt_reason, status.HTTP_400_BAD_REQUEST),
            detail={
                "error": halt_reason,
                "message": metadata.get("message"),
                "request_id": rid,
            },
        )

    return SmartBuyerResponse(
        request_id=rid,
        query=req.query,
        latency_ms=latency_ms,
        offers=offers,
        scoring=scoring,
        explanation=explanation,
        metadata=metadata,
        summary_text=result.get("summary_text"),
    )


@router.post(
    "/smart-buyer/chat",
    response_model=SmartBuyerChatResponse,
    status_code=status.HTTP_200_OK,
)
async def smart_buyer_chat(
    req: SmartBuyerChatRequest,
    request: Request,
    svc: OrchestratorService = Depends(get_orchestrator_service),
    tools=Depends(get_tool_registry),
    llm=Depends(get_llm),
    http=Depends(get_http_client),
    x_request_id: Optional[str] = Header(default=None, convert_underscores=True),
):
    started = time.perf_counter()
    rid = _correlation_id(x_request_id)
    message = req.message.strip()
    if len(message) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "message_too_short", "request_id": rid},
        )

    user_id = request.headers.get("x-user-id")
    org_id = request.headers.get("x-org-id")
    role = request.headers.get("x-user-role")
    channel = request.headers.get("x-channel") or "web"

    conversation_id = req.conversation_id or uuid.uuid4().hex

    try:
        result = await svc.run_smart_buyer(
            query=message,
            top_k=req.top_k,
            prefs=req.prefs.model_dump() if req.prefs else None,
            criteria=[c.model_dump() for c in req.criteria] if req.criteria else None,
            tools=tools,
            llm=llm,
            http=http,
            request_id=rid,
            user_id=user_id,
            org_id=org_id,
            role=role,
            channel=channel,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail={"request_id": rid, "error": type(e).__name__}
        ) from e

    (
        offers,
        scoring,
        explanation,
        metadata,
    ) = _parse_smart_buyer_payload(result, req.top_k)
    metadata = metadata | {"conversation_id": conversation_id}

    halt_reason = metadata.get("halt_reason") or metadata.get("error")
    if halt_reason:
        status_map = {
            "quota_exceeded": status.HTTP_429_TOO_MANY_REQUESTS,
            "tool_blocked": status.HTTP_403_FORBIDDEN,
            "skill_not_allowed": status.HTTP_403_FORBIDDEN,
            "tool_error": status.HTTP_502_BAD_GATEWAY,
        }
        raise HTTPException(
            status_code=status_map.get(halt_reason, status.HTTP_400_BAD_REQUEST),
            detail={
                "error": halt_reason,
                "message": metadata.get("message"),
                "request_id": rid,
            },
        )

    assistant_text = (
        result.get("summary_text")
        or explanation.summary
        or _summarize_offers(offers)
    )
    top_recommendations = _build_top_recommendations(offers, scoring)

    messages = [
        ChatMessageOut(
            id=uuid.uuid4().hex,
            role="user",
            content=message,
            created_at=_utc_now(),
        ),
        ChatMessageOut(
            id=uuid.uuid4().hex,
            role="assistant",
            content=assistant_text,
            created_at=_utc_now(),
            metadata={
                "flow_type": "smart_buyer",
                "top_recommendations": top_recommendations,
                "explanation": explanation.model_dump(),
                "summary_text": result.get("summary_text"),
            },
        ),
    ]

    return SmartBuyerChatResponse(
        conversation_id=conversation_id,
        messages=messages,
        offers=offers,
        scoring=scoring,
        explanation=explanation,
        metadata=metadata,
        summary_text=result.get("summary_text"),
    )


def _parse_smart_buyer_payload(
    result: Dict[str, Any], requested_top_k: int
) -> tuple[List[OfferOut], ScoringOut, ExplanationOut, Dict[str, Any]]:
    offers = [OfferOut(**o) for o in result.get("offers", [])]
    scoring_raw = result.get("scoring", {})
    explanation_raw = result.get("explanation", {})
    metadata = result.get("metadata", {}) | {"top_k": requested_top_k}

    halt_reason = metadata.get("halt_reason") or metadata.get("error")
    if halt_reason:
        status_map = {
            "quota_exceeded": status.HTTP_429_TOO_MANY_REQUESTS,
            "tool_blocked": status.HTTP_403_FORBIDDEN,
            "skill_not_allowed": status.HTTP_403_FORBIDDEN,
            "tool_error": status.HTTP_502_BAD_GATEWAY,
        }
        raise HTTPException(
            status_code=status_map.get(halt_reason, status.HTTP_400_BAD_REQUEST),
            detail={
                "error": halt_reason,
                "message": metadata.get("message"),
                "request_id": rid,
            },
        )

    scoring = ScoringOut(
        best=scoring_raw.get("best"),
        confidence=float(scoring_raw.get("confidence", 0.0)),
        option_scores=[
            OptionScoreOut(
                option_id=str(option_score.get("option_id")),
                total_score=float(option_score.get("total_score", 0.0)),
                rank=int(option_score.get("rank", index + 1)),
            )
            for index, option_score in enumerate(scoring_raw.get("option_scores", []))
            if isinstance(option_score, dict)
        ],
    )

    explanation = ExplanationOut(
        winner=explanation_raw.get("winner"),
        confidence=float(explanation_raw.get("confidence", scoring.confidence)),
        best_by_criterion=explanation_raw.get("best_by_criterion", {}),
        tradeoffs=explanation_raw.get("tradeoffs", []),
        per_option=explanation_raw.get("per_option", []),
        summary=explanation_raw.get("summary", ""),
    )

<<<<<<< Updated upstream
    return SmartBuyerResponse(
        request_id=rid,
        query=req.query,
        latency_ms=latency_ms,
        offers=offers,
        scoring=scoring,
        explanation=explanation,
        metadata=metadata | {"top_k": req.top_k},
        summary_text=result.get("summary_text"),
    )
=======
    return offers, scoring, explanation, metadata


def _summarize_offers(offers: List[OfferOut]) -> str:
    if not offers:
        return "I could not find any relevant offers yet, please try refining your question."

    lines = []
    for idx, offer in enumerate(offers[:3], start=1):
        price = _format_price(offer.price)
        lines.append(
            f"{idx}. {offer.title} — {price} {offer.currency or 'VND'} on {offer.site}"
        )
    return "Here are the top offers:\n" + "\n".join(lines)


def _format_price(value: Optional[Decimal]) -> str:
    if value is None:
        return "N/A"
    try:
        return f"{value:,.0f}"
    except Exception:
        return str(value)


def _build_top_recommendations(
    offers: List[OfferOut], scoring: ScoringOut
) -> List[Dict[str, Any]]:
    offers_by_id = {
        str(offer.id or idx): offer for idx, offer in enumerate(offers, start=1)
    }
    recommendations = []
    for option in scoring.option_scores:
        offer = offers_by_id.get(option.option_id)
        product = (
            {
                "name": offer.title,
                "price": float(offer.price) if offer.price is not None else None,
                "site": offer.site,
                "url": offer.url,
            }
            if offer
            else None
        )
        recommendations.append(
            {
                "rank": option.rank,
                "score": option.total_score,
                "product": product,
            }
        )
    return recommendations


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
>>>>>>> Stashed changes
