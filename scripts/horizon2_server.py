#!/usr/bin/env python3
"""Minimal HTTP server for Horizon 2 generation (local causal LM). Same product shape as `phase3_reference_server.py`.

Requires: `pip install -r optional-requirements-horizon2.txt` and (for the API) `pip install -r optional-requirements-phase3.txt`
or `fastapi` + `uvicorn` in your environment."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_scripts = Path(__file__).resolve().parent
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))

from horizon2_core import (
    DEFAULT_INSTRUCTION_MODEL,
    SMOKE_MODEL_ID,
    build_user_prompt,
    format_for_model,
    generate_completion,
    load_causal_lm,
    pick_device,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--model",
        type=str,
        default=None,
        help="HF model id (default: HORIZON2_MODEL or smol instruct; use --smoke for tiny gpt2).",
    )
    p.add_argument("--smoke", action="store_true", help=f"Use {SMOKE_MODEL_ID!r}")
    p.add_argument("--device", default="auto", help="auto | cpu | cuda | mps")
    p.add_argument("--host", type=str, default="127.0.0.1")
    p.add_argument("--port", type=int, default=8766)
    p.add_argument("--max-new-tokens", type=int, default=128)
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    if args.smoke:
        mid = SMOKE_MODEL_ID
    elif args.model:
        mid = args.model
    else:
        mid = os.environ.get("HORIZON2_MODEL", DEFAULT_INSTRUCTION_MODEL)
    dev = pick_device(args.device)
    try:
        from fastapi import FastAPI, HTTPException
        import uvicorn
        from pydantic import BaseModel, Field
    except ImportError as e:
        print("Need: pip install fastapi uvicorn pydantic", file=sys.stderr)
        raise SystemExit(1) from e

    print(f"Loading {mid!r} on {dev!r} ...", flush=True)
    lm = load_causal_lm(mid, dev)

    app = FastAPI(
        title="TinyModel Horizon2 reference API",
        version="0.1.0",
        description="POST /v1/generate for summarize|reformulate|grounded; see texts/horizon2-handbook.md",
    )

    class GenIn(BaseModel):
        task: str
        text: str
        context: str = ""
        max_new_tokens: int = Field(args.max_new_tokens, ge=1, le=1024)
        seed: int = Field(args.seed, ge=0, le=2**31 - 1)

    class GenOut(BaseModel):
        output: str
        n_prompt_tokens: int
        n_new_tokens: int
        seconds: float

    @app.get("/")
    def root() -> dict[str, str]:  # type: ignore[no-untyped-def]
        """So opening http://127.0.0.1:8766/ in a browser is not a bare 404."""
        return {
            "service": "TinyModel Horizon2 reference API",
            "model": mid,
            "docs": "/docs",
            "openapi_json": "/openapi.json",
            "health": "/healthz",
            "generate": "POST /v1/generate (JSON body: task, text, optional context)",
        }

    @app.get("/healthz")
    def healthz() -> dict[str, str]:  # type: ignore[no-untyped-def]
        return {"status": "ok", "horizon2_model": mid}

    @app.post("/v1/generate", response_model=GenOut)
    def v1_gen(req: GenIn) -> GenOut:  # type: ignore[no-untyped-def]
        if req.task not in ("summarize", "reformulate", "grounded"):
            raise HTTPException(status_code=400, detail="task must be summarize, reformulate, or grounded")
        if req.task == "grounded" and not req.context.strip():
            raise HTTPException(status_code=400, detail="grounded needs non-empty context")
        up = build_user_prompt(
            req.task, req.text, context=req.context.strip() or None
        )
        prompt = format_for_model(lm.tokenizer, up)
        out, np_, nn_, sec = generate_completion(
            lm,
            prompt,
            max_new_tokens=req.max_new_tokens,
            seed=req.seed,
        )
        return GenOut(
            output=out,
            n_prompt_tokens=np_,
            n_new_tokens=nn_,
            seconds=round(sec, 4),
        )

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
