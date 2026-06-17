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
_REPO = _scripts.parent
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))

_PROG = "phase3_reference_server"
_DEFAULT_HSP_CORPUS = _REPO / "texts" / "hsp_program_corpus.md"


def resolve_hsp_corpus_path(explicit: str | None = None) -> Path:
    """Resolve HSP markdown corpus (env, repo default, Docker path)."""
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    env_path = os.environ.get("TINYMODEL_HSP_CORPUS")
    if env_path:
        candidates.append(Path(env_path))
    candidates.extend(
        [
            _DEFAULT_HSP_CORPUS,
            Path("/app/texts/hsp_program_corpus.md"),
        ]
    )
    seen: set[str] = set()
    for path in candidates:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        if path.is_file():
            return path.resolve()
    tried = ", ".join(str(p) for p in candidates)
    raise FileNotFoundError(f"HSP corpus not found; tried: {tried}")


def build_parser() -> argparse.ArgumentParser:
    epilog = (
        "Install: pip install -r optional-requirements-phase3.txt "
        "(fastapi, uvicorn, pydantic; torch and transformers load when the server starts).\n"
        "Examples:\n"
        "  python scripts/phase3_reference_server.py --model HyperlinksSpace/TinyModel1\n"
        "  python scripts/phase3_reference_server.py --model artifacts/phase1/runs/smoke/ag_news/scratch "
        "--host 127.0.0.1 --port 8765\n"
        "Environment: TINYMODEL_PATH overrides the default Hub id for --model. "
        "HOST and PORT env vars override --host/--port (Railway sets PORT). "
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
    p.add_argument(
        "--hsp-corpus",
        type=str,
        default=os.environ.get("TINYMODEL_HSP_CORPUS", str(_DEFAULT_HSP_CORPUS)),
        help="Markdown corpus for POST /v1/plan when clients omit candidates.",
    )
    p.add_argument("--host", type=str, default=os.environ.get("HOST", "127.0.0.1"))
    p.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8765")))
    return p


def parse_args() -> argparse.Namespace:
    return build_parser().parse_args()


def create_reference_app(rt, model_name: str, hsp_chunks: list[str] | None = None):
    """Build FastAPI app for Uvicorn or in-process probes."""
    try:
        from fastapi import Body, FastAPI, HTTPException
    except ImportError as e:
        raise ImportError(
            "Install optional deps: pip install fastapi uvicorn pydantic"
        ) from e

    from phase3_reference_models import (
        ClassifyIn,
        ClassifyItem,
        ClassifyOut,
        PlanContext,
        PlanIn,
        PlanOut,
        PlanRetrieval,
        PlanRouting,
        RetrieveHit,
        RetrieveIn,
        RetrieveOut,
    )

    bundled_chunks = list(hsp_chunks or [])

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
            "plan": "POST /v1/plan (JSON: text; HSP control-plane glue)",
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

    @app.post("/v1/plan", response_model=PlanOut)
    def v1_plan(payload: PlanIn = Body()) -> PlanOut:
        from hsp_plan_lib import plan_hsp_request

        chunks = payload.candidates if payload.candidates else bundled_chunks
        if not chunks:
            raise HTTPException(
                status_code=400,
                detail="no candidates and no bundled HSP corpus loaded",
            )
        ctx_dict: dict | None = None
        if payload.context is not None:
            ctx_dict = payload.context.model_dump(exclude_none=True)
        plan = plan_hsp_request(
            payload.text,
            rt,
            chunks,
            min_confidence=payload.min_confidence,
            min_margin=payload.min_margin,
            top_k=payload.top_k,
            context=ctx_dict,
        )
        retrieval = None
        if plan["retrieval"] is not None:
            retrieval = PlanRetrieval(**plan["retrieval"])
        out_ctx = None
        if plan.get("context"):
            out_ctx = PlanContext(**plan["context"])
        return PlanOut(
            text=plan["text"],
            intent=plan["intent"],
            context=out_ctx,
            route_hint=plan["route_hint"],
            actions=plan["actions"],
            probs=plan["probs"],
            routing=PlanRouting(**plan["routing"]),
            retrieval=retrieval,
        )

    return app


def main() -> None:
    from hsp_corpus_lib import load_chunks
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

    hsp_corpus = resolve_hsp_corpus_path(args.hsp_corpus)
    hsp_chunks = load_chunks(hsp_corpus)
    print(f"Loaded HSP corpus {hsp_corpus} ({len(hsp_chunks)} chunks)", file=sys.stderr)
    if len(hsp_chunks) < 8:
        print(f"Warning: expected >= 8 corpus chunks, got {len(hsp_chunks)}", file=sys.stderr)

    rt = TinyModelRuntime(args.model, device="cpu", max_length=128)
    app = create_reference_app(rt, args.model, hsp_chunks)
    print(f"Starting reference server on http://{args.host}:{args.port} model={args.model!r}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
