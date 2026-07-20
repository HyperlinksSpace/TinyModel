"""Pydantic models for phase3_reference_server (module-level for FastAPI binding)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ClassifyIn(BaseModel):
    texts: list[str] = Field(..., min_length=1, description="One or more input strings.")


class ClassifyItem(BaseModel):
    label_scores: dict[str, float]


class ClassifyOut(BaseModel):
    items: list[ClassifyItem]


class RetrieveIn(BaseModel):
    query: str
    candidates: list[str] = Field(default_factory=list)
    top_k: int = Field(3, ge=1, le=100)


class RetrieveHit(BaseModel):
    index: int
    text: str
    score: float


class RetrieveOut(BaseModel):
    hits: list[RetrieveHit]


class PlanContext(BaseModel):
    route: str | None = Field(None, description="Current app route, e.g. /swap.")
    locale: str | None = Field(None, description="UI locale, e.g. en or ru.")
    wallet_connected: bool | None = Field(None, description="Whether wallet is linked.")
    surface: str | None = Field(None, description="Client surface, e.g. strategy-site or ai-core.")
    visible_section: str | None = Field(None, description="Visible strategy section id.")
    tour_active: bool | None = Field(None, description="Whether guided tour is active.")


class PlanIn(BaseModel):
    text: str = Field(..., min_length=1, description="User message to plan.")
    candidates: list[str] = Field(
        default_factory=list,
        description="Optional corpus chunks; server uses bundled HSP corpus when empty.",
    )
    top_k: int = Field(2, ge=1, le=100)
    min_confidence: float = Field(0.55, ge=0.0, le=1.0)
    min_margin: float = Field(0.10, ge=0.0, le=1.0)
    context: PlanContext | None = None


class PlanRouting(BaseModel):
    fallback: bool
    label: str | None = None
    confidence: float
    margin: float
    reason: str


class PlanRetrieval(BaseModel):
    top_idx: int
    top_title: str
    hybrid_score: float
    keyword_overlap: float
    chunk_preview: str
    query_used: str | None = None


class PlanOut(BaseModel):
    text: str
    intent: str
    context: PlanContext | None = None
    route_hint: str | None = None
    actions: list[dict[str, str]]
    probs: dict[str, float]
    routing: PlanRouting
    retrieval: PlanRetrieval | None = None
    reply_text: str | None = Field(
        None,
        description="Optional verbatim reply (e.g. strategy_handshake) for integrators.",
    )
