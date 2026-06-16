#!/usr/bin/env python3
"""Stdlib contract smoke for HSP /api/ai meta.tinymodel debug payloads.

Maps POST /v1/plan shapes to the meta block HSP will log under meta.tinymodel
when wiring ai/transmitter.ts (Phase 2); no live server or torch.

Examples:
  python scripts/hsp_meta_contract_smoke.py --verify
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

from hsp_meta_lib import build_meta_tinymodel, validate_meta_tinymodel

_OUT = _REPO / ".tmp" / "hsp-meta-contract" / "run.json"
_SCHEMA = "hsp_meta_contract_smoke_run/1.0"
_PROG = "hsp_meta_contract_smoke"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verify", action="store_true", help="Exit 0 when meta contract checks pass.")
    p.add_argument("--output-json", type=str, default="", help=f"Write run JSON (default: {_OUT}).")
    return p


def sample_plan_navigate() -> dict[str, Any]:
    return {
        "text": "open swap page",
        "route_hint": "navigate:/swap",
        "actions": [{"type": "navigate", "path": "/swap"}],
        "probs": {"World": 0.12, "Business": 0.55, "Sports": 0.08, "Sci/Tech": 0.25},
        "routing": {
            "fallback": False,
            "label": "Business",
            "confidence": 0.55,
            "margin": 0.2,
            "reason": "accept",
        },
        "retrieval": None,
    }


def sample_plan_retrieve() -> dict[str, Any]:
    return {
        "text": "explain home feed NFT items",
        "route_hint": None,
        "actions": [],
        "probs": {"World": 0.2, "Sports": 0.15, "Business": 0.25, "Sci/Tech": 0.3},
        "routing": {
            "fallback": True,
            "label": None,
            "confidence": 0.3,
            "margin": 0.05,
            "reason": "below_min_confidence",
        },
        "retrieval": {
            "top_idx": 6,
            "top_title": "Feed",
            "hybrid_score": 0.82,
            "keyword_overlap": 0.4,
            "chunk_preview": "Feed\nHome feed shows NFT items...",
        },
    }


def run_verify() -> tuple[bool, dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    model = "HyperlinksSpace/TinyModel1"

    for name, plan in (
        ("navigate_plan", sample_plan_navigate()),
        ("retrieve_plan", sample_plan_retrieve()),
    ):
        meta = build_meta_tinymodel(plan, model)
        validate_meta_tinymodel(meta)
        raw = json.dumps({"meta": {"tinymodel": meta}})
        parsed = json.loads(raw)
        validate_meta_tinymodel(parsed["meta"]["tinymodel"])
        checks.append({"name": name, "ok": True, "meta": meta})

    artifact = {
        "schema": _SCHEMA,
        "checks": checks,
        "ok": True,
    }
    return True, artifact


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
