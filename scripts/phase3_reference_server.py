#!/usr/bin/env python3
"""Minimal reference HTTP API for classify + retrieve (stable shape for integrators).

Uses `TinyModelRuntime` (PyTorch). For ONNX-only serving, put a reverse proxy in front of
an ORT worker or adapt this file to use `onnxruntime` like `phase3_benchmark.py`.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_scripts = Path(__file__).resolve().parent
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))

from phase3_common import resolve_checkpoint_or_hub

from tinymodel_runtime import TinyModelRuntime


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--model",
        type=str,
        default=os.environ.get("TINYMODEL_PATH", "HyperlinksSpace/TinyModel1"),
        help="Checkpoint path or Hub id (or set TINYMODEL_PATH).",
    )
    p.add_argument("--host", type=str, default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    args.model = resolve_checkpoint_or_hub(args.model)
    try:
        from fastapi import FastAPI
        import uvicorn
        from pydantic import BaseModel, Field
    except ImportError as e:
        print(
            "Install optional deps: pip install fastapi uvicorn pydantic\n"
            f"({e})",
            file=sys.stderr,
        )
        raise SystemExit(1) from e

    rt = TinyModelRuntime(args.model, device="cpu", max_length=128)
    app = FastAPI(
        title="TinyModel reference API",
        version="0.1.0",
        description="Classify and retrieve; see `texts/phase3-serving-profile.md` for contract.",
    )

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

    @app.get("/")
    def root() -> dict[str, str]:  # type: ignore[no-untyped-def]
        """So opening the base URL in a browser is not a bare 404 (matches Horizon 2 server shape)."""
        return {
            "service": "TinyModel Phase 3 reference API",
            "model": args.model,
            "docs": "/docs",
            "openapi_json": "/openapi.json",
            "health": "/healthz",
            "classify": "POST /v1/classify (JSON: texts[])",
            "retrieve": "POST /v1/retrieve (JSON: query, candidates[], top_k)",
        }

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/classify", response_model=ClassifyOut)
    def v1_classify(req: ClassifyIn) -> ClassifyOut:  # type: ignore[no-untyped-def]
        probs = rt.classify(req.texts)
        return ClassifyOut(
            items=[ClassifyItem(label_scores=p) for p in probs]
        )

    @app.post("/v1/retrieve", response_model=RetrieveOut)
    def v1_retrieve(req: RetrieveIn) -> RetrieveOut:  # type: ignore[no-untyped-def]
        hits = rt.retrieve(req.query, req.candidates, top_k=req.top_k)
        return RetrieveOut(
            hits=[
                RetrieveHit(index=h.index, text=h.text, score=h.score)
                for h in hits
            ],
        )

    print(f"Starting reference server on http://{args.host}:{args.port} model={args.model!r}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
