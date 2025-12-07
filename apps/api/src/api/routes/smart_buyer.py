# apps/api/src/api/routes/smart_buyer.py
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field, conint, conlist

from services.smart_buyer_service import SmartBuyerService
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

    offers = [OfferOut(**o) for o in result.get("offers", [])]
    scoring_raw = result.get("scoring", {})
    explanation_raw = result.get("explanation", {})
    metadata = result.get("metadata", {})

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
                option_id=str(os.get("option_id")),
                total_score=float(os.get("total_score", 0.0)),
                rank=int(os.get("rank", 0)),
            )
            for os in scoring_raw.get("option_scores", [])
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
