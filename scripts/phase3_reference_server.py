#!/usr/bin/env python3
"""Minimal reference HTTP API for classify + retrieve (stable shape for integrators).

Uses `TinyModelRuntime` (PyTorch). For ONNX-only serving, put a reverse proxy in front of
an ORT worker or adapt this file to use `onnxruntime` like `phase3_benchmark.py`.
"""

import argparse
import os
import sys
from pathlib import Path

_scripts = Path(__file__).resolve().parent
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))

_PROG = "phase3_reference_server"


def build_parser() -> argparse.ArgumentParser:
    epilog = (
        "Install: pip install -r optional-requirements-phase3.txt "
        "(fastapi, uvicorn, pydantic; torch and transformers load when the server starts).\n"
        "Examples:\n"
        "  python scripts/phase3_reference_server.py --model HyperlinksSpace/TinyModel1\n"
        "  python scripts/phase3_reference_server.py --model artifacts/phase1/runs/smoke/ag_news/scratch "
        "--host 127.0.0.1 --port 8765\n"
        "Environment: TINYMODEL_PATH overrides the default Hub id for --model. "
        "Swagger: http://127.0.0.1:8765/docs with default host/port."
    )
    p = argparse.ArgumentParser(
        prog=_PROG,
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog,
    )
    p.add_argument(
        "--model",
        type=str,
        default=os.environ.get("TINYMODEL_PATH", "HyperlinksSpace/TinyModel1"),
        help="Checkpoint path or Hub id (or set TINYMODEL_PATH).",
    )
    p.add_argument("--host", type=str, default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    return p


def parse_args() -> argparse.Namespace:
    return build_parser().parse_args()


def create_reference_app(rt, model_name: str):
    """Build FastAPI app for Uvicorn or in-process probes."""
    try:
        from fastapi import Body, FastAPI
    except ImportError as e:
        raise ImportError(
            "Install optional deps: pip install fastapi uvicorn pydantic"
        ) from e

    from phase3_reference_models import (
        ClassifyIn,
        ClassifyItem,
        ClassifyOut,
        RetrieveHit,
        RetrieveIn,
        RetrieveOut,
    )

    app = FastAPI(
        title="TinyModel reference API",
        version="0.1.0",
        description="Classify and retrieve; see `texts/phase3-serving-profile.md` for contract.",
    )

    @app.get("/")
    def root() -> dict[str, str]:
        return {
            "service": "TinyModel Phase 3 reference API",
            "model": model_name,
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
    def v1_classify(payload: ClassifyIn = Body()) -> ClassifyOut:
        probs = rt.classify(payload.texts)
        return ClassifyOut(items=[ClassifyItem(label_scores=p) for p in probs])

    @app.post("/v1/retrieve", response_model=RetrieveOut)
    def v1_retrieve(payload: RetrieveIn = Body()) -> RetrieveOut:
        hits = rt.retrieve(payload.query, payload.candidates, top_k=payload.top_k)
        return RetrieveOut(
            hits=[
                RetrieveHit(index=h.index, text=h.text, score=h.score)
                for h in hits
            ],
        )

    return app


def main() -> None:
    from phase3_common import resolve_checkpoint_or_hub
    from tinymodel_runtime import TinyModelRuntime

    args = parse_args()
    args.model = resolve_checkpoint_or_hub(args.model)
    try:
        import uvicorn
    except ImportError as e:
        print(
            "Install optional deps: pip install fastapi uvicorn pydantic\n"
            f"({e})",
            file=sys.stderr,
        )
        raise SystemExit(1) from e

    rt = TinyModelRuntime(args.model, device="cpu", max_length=128)
    app = create_reference_app(rt, args.model)
    print(f"Starting reference server on http://{args.host}:{args.port} model={args.model!r}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
