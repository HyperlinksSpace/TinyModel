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
