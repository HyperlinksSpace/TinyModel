#!/usr/bin/env python3
"""Horizon 2: generative (causal LM) path — summarize / reformulate / grounded with JSON run artifacts.

Complements the encoder + RAG line from Horizon 1. Install: `pip install -r optional-requirements-horizon2.txt`
(then ensure `torch` matches your environment)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_scripts = Path(__file__).resolve().parent
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))

from horizon2_core import (
    DEFAULT_INSTRUCTION_MODEL,
    SMOKE_MODEL_ID,
    dump_json,
    pick_device,
    run_json_artifact,
)

_REPO = _scripts.parent

DEFAULT_SAMPLES = [
    (
        "The central bank held rates steady but signaled cuts later in the year. "
        "Stocks added gains while the dollar drifted lower against major peers."
    ),
    (
        "I was charged twice for the same order last Friday. The receipt shows one "
        "transaction but my card has two authorizations. Please help."
    ),
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--task",
        choices=["summarize", "reformulate", "grounded"],
        default="summarize",
    )
    p.add_argument(
        "--model",
        type=str,
        default=None,
        help="Hugging Face model id (overrides HORIZON2_MODEL / --smoke).",
    )
    p.add_argument(
        "--smoke",
        action="store_true",
        help=f"Use tiny {SMOKE_MODEL_ID!r} for a fast, low-quality check (default without --smoke: env or a small Instruct model).",
    )
    p.add_argument(
        "--device",
        default="auto",
        help="auto | cpu | cuda | mps",
    )
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--max-new-tokens", type=int, default=128)
    p.add_argument(
        "--text",
        type=str,
        help="Single input; if unset, use built-in demo samples (or --input-file).",
    )
    p.add_argument(
        "--input-file",
        type=str,
        help="UTF-8 file with one sample per line (or JSON list of strings).",
    )
    p.add_argument(
        "--context",
        type=str,
        default="",
        help="Optional RAG/FAQ context; required for --task grounded.",
    )
    p.add_argument(
        "--context-file",
        type=str,
        help="Read context from file (e.g. a retrieved chunk from rag_faq_corpus).",
    )
    p.add_argument(
        "--output-json",
        type=str,
        default="",
        help="Write horizon2 run artifact (default: .tmp/horizon2/last_run.json for multi-sample).",
    )
    p.add_argument(
        "--compare-with",
        type=str,
        default="",
        help="Optional second model id: same samples are run again for a side-by-side field in JSON.",
    )
    p.add_argument(
        "--verify",
        action="store_true",
        help="Download/run tiny smoke model once; write .tmp/horizon2-verify/horizon2_run.json; exit 0 on success.",
    )
    p.add_argument(
        "--print-json-stdout",
        action="store_true",
        help="After writing file, also print the JSON to stdout (Windows logs: set PYTHONIOENCODING=utf-8 if needed).",
    )
    return p.parse_args()


def _resolve_model(a: argparse.Namespace) -> str:
    if a.model:
        return a.model
    if a.smoke:
        return SMOKE_MODEL_ID
    return os.environ.get("HORIZON2_MODEL", DEFAULT_INSTRUCTION_MODEL)


def _load_samples(a: argparse.Namespace) -> list[tuple[str, str | None]]:
    ctx: str | None = None
    if a.context_file:
        ctx = Path(a.context_file).read_text(encoding="utf-8").strip() or None
    elif a.context.strip():
        ctx = a.context.strip()

    if a.text:
        return [(a.text, ctx)]
    if a.input_file:
        raw = Path(a.input_file).read_text(encoding="utf-8")
        if raw.lstrip().startswith("["):
            items = json.loads(raw)
            if not isinstance(items, list):
                raise SystemExit("JSON input-file must be a list of strings")
            return [(str(x), ctx) for x in items]
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        return [(ln, ctx) for ln in lines]
    if a.task == "grounded" and not ctx:
        print("--task grounded needs --context or --context-file", file=sys.stderr)
        raise SystemExit(2)
    return [(s, ctx) for s in DEFAULT_SAMPLES]


def _tiers_bloc(device: str, model_id: str) -> dict[str, str]:
    return {
        "smoke_tiny": "sshleifer/tiny-gpt2 on CPU, seconds per short reply (for CI / wiring only).",
        "local_instruct": f"{DEFAULT_INSTRUCTION_MODEL} (default when not --smoke); CPU workable, GPU faster.",
        "api_tier": "Host any OpenAI-compatible or HF Inference endpoint behind your own gateway; this script stays local-weights-only by default.",
        "this_run": f"device={device!r} model_id={model_id!r}",
    }


def run() -> int:
    a = parse_args()
    if a.verify:
        out = str(_REPO / ".tmp" / "horizon2-verify" / "horizon2_run.json")
        d = run_json_artifact(
            model_id=SMOKE_MODEL_ID,
            device="cpu",
            task="summarize",
            max_new_tokens=48,
            seed=0,
            samples_in=[(DEFAULT_SAMPLES[0], None)],
            do_sample=False,
        )
        d["meta"] = _tiers_bloc("cpu", SMOKE_MODEL_ID)
        d["note"] = "horizon2 --verify: tiny model; use without --verify for real quality."
        if not d["samples"] or not (d["samples"][0].get("output", "").strip()):
            print("horizon2 verify: empty output", file=sys.stderr)
            return 1
        dump_json(d, out)
        print(f"horizon2 verify: OK wrote {out}", flush=True)
        return 0

    model_id = _resolve_model(a)
    dev = pick_device(a.device)
    samples_in = _load_samples(a)
    d = run_json_artifact(
        model_id=model_id,
        device=dev,
        task=a.task,
        max_new_tokens=a.max_new_tokens,
        seed=a.seed,
        samples_in=samples_in,
    )
    d["meta"] = _tiers_bloc(d["device"], model_id)

    if a.compare_with:
        d2 = run_json_artifact(
            model_id=a.compare_with,
            device=dev,
            task=a.task,
            max_new_tokens=a.max_new_tokens,
            seed=a.seed,
            samples_in=samples_in,
        )
        d["side_by_side"] = {
            "model_id": a.compare_with,
            "samples": d2["samples"],
        }

    out_path = a.output_json or str(_REPO / ".tmp" / "horizon2" / "last_run.json")
    dump_json(d, out_path)
    print(f"Wrote {out_path}", flush=True)
    if a.print_json_stdout:
        sys.stdout.write(json.dumps(d, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
