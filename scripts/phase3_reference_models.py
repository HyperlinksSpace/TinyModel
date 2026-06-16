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


class PlanIn(BaseModel):
    text: str = Field(..., min_length=1, description="User message to plan.")
    candidates: list[str] = Field(
        default_factory=list,
        description="Optional corpus chunks; server uses bundled HSP corpus when empty.",
    )
    top_k: int = Field(2, ge=1, le=100)
    min_confidence: float = Field(0.55, ge=0.0, le=1.0)
    min_margin: float = Field(0.10, ge=0.0, le=1.0)


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


class PlanOut(BaseModel):
    text: str
    route_hint: str | None = None
    actions: list[dict[str, str]]
    probs: dict[str, float]
    routing: PlanRouting
    retrieval: PlanRetrieval | None = None
