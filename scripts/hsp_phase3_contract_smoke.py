#!/usr/bin/env python3
"""Stdlib contract smoke: Phase 3 API JSON shapes for HSP sidecar integration.

Validates request/response fields documented in texts/phase3-serving-profile.md
against sample payloads and the HSP program corpus (no live server, no torch).

Examples:
  python scripts/hsp_phase3_contract_smoke.py --verify
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_scripts = Path(__file__).resolve().parent
_REPO = _scripts.parent
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))

from hsp_corpus_lib import chunk_title, load_chunks

_CORPUS = _REPO / "texts" / "hsp_program_corpus.md"
_OUT = _REPO / ".tmp" / "hsp-phase3-contract" / "run.json"
_SCHEMA = "hsp_phase3_contract_smoke_run/1.0"
_PROG = "hsp_phase3_contract_smoke"
_MIN_CHUNKS = 8


def _fail(msg: str) -> None:
    raise ValueError(msg)


def validate_healthz(body: Any) -> None:
    if not isinstance(body, dict) or body.get("status") != "ok":
        _fail("healthz must be {\"status\": \"ok\"}")


def validate_classify_request(body: Any) -> None:
    if not isinstance(body, dict):
        _fail("classify request must be object")
    texts = body.get("texts")
    if not isinstance(texts, list) or not texts or not all(isinstance(t, str) for t in texts):
        _fail("classify request.texts must be non-empty list[string]")


def validate_classify_response(body: Any) -> None:
    if not isinstance(body, dict):
        _fail("classify response must be object")
    items = body.get("items")
    if not isinstance(items, list) or not items:
        _fail("classify response.items must be non-empty list")
    for item in items:
        if not isinstance(item, dict):
            _fail("classify item must be object")
        scores = item.get("label_scores")
        if not isinstance(scores, dict) or not scores:
            _fail("classify item.label_scores must be non-empty object")
        for k, v in scores.items():
            if not isinstance(k, str) or not isinstance(v, (int, float)):
                _fail("label_scores entries must be string -> number")


def validate_retrieve_request(body: Any, *, min_candidates: int = 1) -> None:
    if not isinstance(body, dict):
        _fail("retrieve request must be object")
    query = body.get("query")
    if not isinstance(query, str) or not query.strip():
        _fail("retrieve request.query must be non-empty string")
    candidates = body.get("candidates")
    if not isinstance(candidates, list) or len(candidates) < min_candidates:
        _fail("retrieve request.candidates must be list with enough entries")
    if not all(isinstance(c, str) and c.strip() for c in candidates):
        _fail("retrieve request.candidates must be list[string]")
    top_k = body.get("top_k", 3)
    if not isinstance(top_k, int) or top_k < 1 or top_k > 100:
        _fail("retrieve request.top_k must be int in 1..100")


def validate_retrieve_response(body: Any, *, num_candidates: int) -> None:
    if not isinstance(body, dict):
        _fail("retrieve response must be object")
    hits = body.get("hits")
    if not isinstance(hits, list):
        _fail("retrieve response.hits must be list")
    for hit in hits:
        if not isinstance(hit, dict):
            _fail("retrieve hit must be object")
        idx = hit.get("index")
        text = hit.get("text")
        score = hit.get("score")
        if not isinstance(idx, int) or idx < 0 or idx >= num_candidates:
            _fail(f"retrieve hit.index out of range: {idx!r}")
        if not isinstance(text, str) or not text.strip():
            _fail("retrieve hit.text must be non-empty string")
        if not isinstance(score, (int, float)):
            _fail("retrieve hit.score must be number")


def validate_plan_request(body: Any) -> None:
    if not isinstance(body, dict):
        _fail("plan request must be object")
    text = body.get("text")
    if not isinstance(text, str) or not text.strip():
        _fail("plan request.text must be non-empty string")
    candidates = body.get("candidates", [])
    if candidates is not None and not isinstance(candidates, list):
        _fail("plan request.candidates must be list when present")
    if isinstance(candidates, list) and not all(isinstance(c, str) for c in candidates):
        _fail("plan request.candidates must be list[string]")
    top_k = body.get("top_k", 2)
    if not isinstance(top_k, int) or top_k < 1 or top_k > 100:
        _fail("plan request.top_k must be int in 1..100")
    mc = body.get("min_confidence", 0.55)
    mm = body.get("min_margin", 0.10)
    if not isinstance(mc, (int, float)) or not 0.0 <= float(mc) <= 1.0:
        _fail("plan request.min_confidence must be number in 0..1")
    if not isinstance(mm, (int, float)) or not 0.0 <= float(mm) <= 1.0:
        _fail("plan request.min_margin must be number in 0..1")
    ctx = body.get("context")
    if ctx is not None:
        if not isinstance(ctx, dict):
            _fail("plan request.context must be object or null")
        if ctx.get("route") is not None and not isinstance(ctx.get("route"), str):
            _fail("plan request.context.route must be string or null")


def validate_plan_response(body: Any) -> None:
    if not isinstance(body, dict):
        _fail("plan response must be object")
    text = body.get("text")
    if not isinstance(text, str) or not text.strip():
        _fail("plan response.text must be non-empty string")
    intent = body.get("intent")
    if not isinstance(intent, str) or not intent.strip():
        _fail("plan response.intent must be non-empty string")
    ctx = body.get("context")
    if ctx is not None and not isinstance(ctx, dict):
        _fail("plan response.context must be object or null")
    route_hint = body.get("route_hint")
    if route_hint is not None and not isinstance(route_hint, str):
        _fail("plan response.route_hint must be string or null")
    actions = body.get("actions")
    if not isinstance(actions, list):
        _fail("plan response.actions must be list")
    for action in actions:
        if not isinstance(action, dict) or not isinstance(action.get("type"), str):
            _fail("plan action must be object with string type")
    probs = body.get("probs")
    if not isinstance(probs, dict) or not probs:
        _fail("plan response.probs must be non-empty object")
    routing = body.get("routing")
    if not isinstance(routing, dict):
        _fail("plan response.routing must be object")
    if not isinstance(routing.get("fallback"), bool):
        _fail("plan routing.fallback must be bool")
    if routing.get("label") is not None and not isinstance(routing.get("label"), str):
        _fail("plan routing.label must be string or null")
    for key in ("confidence", "margin"):
        if not isinstance(routing.get(key), (int, float)):
            _fail(f"plan routing.{key} must be number")
    if not isinstance(routing.get("reason"), str):
        _fail("plan routing.reason must be string")
    retrieval = body.get("retrieval")
    if retrieval is not None:
        if not isinstance(retrieval, dict):
            _fail("plan response.retrieval must be object or null")
        for key in ("top_idx", "hybrid_score", "keyword_overlap"):
            if not isinstance(retrieval.get(key), (int, float)):
                _fail(f"plan retrieval.{key} must be number")
        for key in ("top_title", "chunk_preview"):
            if not isinstance(retrieval.get(key), str):
                _fail(f"plan retrieval.{key} must be string")


def build_hsp_sample_requests(chunks: list[str]) -> dict[str, Any]:
    """Payloads matching Hyperlinks Space Program ai/tinymodel.ts client calls."""
    return {
        "healthz": {"status": "ok"},
        "classify_request": {"texts": ["open swap page and explain slippage"]},
        "classify_response_sample": {
            "items": [{"label_scores": {"World": 0.12, "Business": 0.55, "Sports": 0.08, "Sci/Tech": 0.25}}]
        },
        "retrieve_request": {
            "query": "connect telegram messages TDLib gateway",
            "candidates": chunks,
            "top_k": 3,
        },
        "retrieve_response_sample": {
            "hits": [
                {
                    "index": 5,
                    "text": chunks[5] if len(chunks) > 5 else chunks[0],
                    "score": 0.87,
                }
            ]
        },
        "plan_request": {"text": "open swap page"},
        "plan_request_with_context": {
            "text": "what is this",
            "context": {"route": "/shield", "locale": "en"},
        },
        "plan_response_sample": {
            "text": "open swap page",
            "intent": "navigate",
            "context": None,
            "route_hint": "navigate:/swap",
            "actions": [{"type": "navigate", "path": "/swap"}],
            "probs": {"World": 0.12, "Business": 0.55, "Sports": 0.08, "Sci/Tech": 0.25},
            "routing": {
                "fallback": False,
                "label": "Business",
                "confidence": 0.55,
                "margin": 0.2,
                "reason": "accepted",
            },
            "retrieval": None,
        },
    }


def run_verify() -> tuple[bool, dict[str, Any]]:
    if not _CORPUS.is_file():
        _fail(f"missing corpus {_CORPUS}")

    chunks = load_chunks(_CORPUS)
    if len(chunks) < _MIN_CHUNKS:
        _fail(f"need >= {_MIN_CHUNKS} chunks, got {len(chunks)}")

    samples = build_hsp_sample_requests(chunks)
    checks: list[dict[str, Any]] = []

    def _check(name: str, fn) -> None:
        try:
            fn()
            checks.append({"name": name, "ok": True})
        except ValueError as e:
            checks.append({"name": name, "ok": False, "error": str(e)})
            raise

    _check("healthz", lambda: validate_healthz(samples["healthz"]))
    _check("classify_request", lambda: validate_classify_request(samples["classify_request"]))
    _check(
        "classify_response",
        lambda: validate_classify_response(samples["classify_response_sample"]),
    )
    _check(
        "retrieve_request",
        lambda: validate_retrieve_request(
            samples["retrieve_request"], min_candidates=_MIN_CHUNKS
        ),
    )
    _check(
        "retrieve_response",
        lambda: validate_retrieve_response(
            samples["retrieve_response_sample"], num_candidates=len(chunks)
        ),
    )
    _check("plan_request", lambda: validate_plan_request(samples["plan_request"]))
    _check(
        "plan_request_context",
        lambda: validate_plan_request(samples["plan_request_with_context"]),
    )
    _check(
        "plan_response",
        lambda: validate_plan_response(samples["plan_response_sample"]),
    )

    # Round-trip JSON (HSP fetch + JSON.parse)
    for key in ("classify_request", "retrieve_request", "plan_request", "plan_request_with_context"):
        raw = json.dumps(samples[key])
        parsed = json.loads(raw)
        if key == "classify_request":
            validate_classify_request(parsed)
        elif key in ("plan_request", "plan_request_with_context"):
            validate_plan_request(parsed)
        else:
            validate_retrieve_request(parsed, min_candidates=_MIN_CHUNKS)

    titles = [chunk_title(c) for c in chunks]
    artifact = {
        "schema": _SCHEMA,
        "corpus": str(_CORPUS),
        "chunk_count": len(chunks),
        "titles": titles,
        "checks": checks,
        "ok": True,
    }
    return True, artifact


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verify", action="store_true", help="Exit 0 when contract checks pass.")
    p.add_argument("--output-json", type=str, default="", help=f"Write run JSON (default: {_OUT}).")
    return p


def main() -> None:
    args = build_parser().parse_args()
    try:
        ok, artifact = run_verify()
    except ValueError as e:
        print(f"{_PROG}: FAIL {e}", file=sys.stderr)
        raise SystemExit(1) from e

    out_path = Path(args.output_json) if args.output_json else _OUT
    if args.verify or args.output_json:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {out_path}")

    print(f"{_PROG}: checks={len(artifact['checks'])} ok={ok}")
    if args.verify:
        print(f"{_PROG} verify: OK")


if __name__ == "__main__":
    main()
