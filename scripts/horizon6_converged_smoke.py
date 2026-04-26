#!/usr/bin/env python3
"""Horizon 6: converged stack — run multiple horizon --verify steps and one JSON artifact.

Exercises (default): generative (H2), memory (H3), multimodal (H4) — three capability lanes with
a shared run contract. Optional --with-rag adds Horizon 1-style retrieval (needs a local encoder
or Hub access). See README \"Horizon 6\" and texts/further-development-universe-brain.md."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_SCHEMA = "horizon6_converged_run/1.0"
_OUT_DIR = _REPO / ".tmp" / "horizon6-converge"
_DEFAULT_OUT = _OUT_DIR / "run.json"


def _run_step(name: str, cmd: list[str]) -> dict:
    t0 = time.perf_counter()
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    r = subprocess.run(cmd, cwd=str(_REPO), env=env)
    dt = time.perf_counter() - t0
    return {
        "name": name,
        "cmd": cmd,
        "ok": r.returncode == 0,
        "exit_code": r.returncode,
        "seconds": round(dt, 3),
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--verify",
        action="store_true",
        help="Run the default H2+H3+H4 verify chain; write .tmp/horizon6-converge/run.json.",
    )
    p.add_argument(
        "--with-rag",
        action="store_true",
        help="Also run scripts/rag_faq_smoke.py (needs a trained checkpoint or Hub model; may download).",
    )
    p.add_argument(
        "--output-json",
        type=str,
        default=str(_DEFAULT_OUT),
        help=f"Output path (default: {_DEFAULT_OUT}).",
    )
    return p.parse_args()


def main() -> int:
    a = parse_args()
    if not a.verify:
        print("Use --verify to run the converged smoke chain.", file=sys.stderr)
        return 2

    py = sys.executable
    steps: list[dict] = []
    plan: list[tuple[str, list[str]]] = [
        (
            "horizon2_generative",
            [py, str(_REPO / "scripts" / "horizon2_generative.py"), "--verify"],
        ),
        (
            "horizon3_memory",
            [py, str(_REPO / "scripts" / "horizon3_memory_cli.py"), "--verify"],
        ),
        (
            "horizon4_multimodal",
            [py, str(_REPO / "scripts" / "horizon4_multimodal.py"), "--verify"],
        ),
    ]
    if a.with_rag:
        plan.append(
            (
                "horizon1_rag_faq",
                [py, str(_REPO / "scripts" / "rag_faq_smoke.py")],
            )
        )

    for name, cmd in plan:
        rec = _run_step(name, cmd)
        steps.append(rec)
        if not rec["ok"]:
            out = _write_artifact(a.output_json, steps, ok=False)
            print(f"horizon6: FAILED at {name!r} (exit {rec['exit_code']})", file=sys.stderr)
            print(f"horizon6: partial artifact {out}", file=sys.stderr)
            return 1

    out = _write_artifact(a.output_json, steps, ok=True)
    print(f"horizon6 verify: OK wrote {out}", flush=True)
    return 0


def _write_artifact(path: str, steps: list[dict], *, ok: bool) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "horizon": 6,
        "schema": _SCHEMA,
        "mode": "converged_smoke",
        "verify_mode": "subprocess_chain_h2_h3_h4" + ("_and_rag" if any(s["name"] == "horizon1_rag_faq" for s in steps) else ""),
        "ok": ok,
        "steps": steps,
        "note": "Thin orchestration: same policy/observability story is for product layers; this only chains offline/smoke verifiers.",
    }
    p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return p.resolve()


if __name__ == "__main__":
    raise SystemExit(main())
