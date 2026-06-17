#!/usr/bin/env python3
"""Run all Hyperlinks Space Program integration verify gates in one command.

Stdlib gates (no torch): corpus, lexical RAG, Phase 3 JSON contract, corpus export,
meta.tinymodel contract, ub_eval nl_signals + hsp_intents.

With --full (needs torch): hybrid RAG, route-then-retrieve glue, live HTTP server smoke.

Examples:
  python scripts/hsp_integration_smoke.py --verify
  python scripts/hsp_integration_smoke.py --verify --full
  python scripts/hsp_integration_smoke.py --verify --full --model .tmp/phase3-smoke
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

_scripts = Path(__file__).resolve().parent
_REPO = _scripts.parent
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))

_OUT = _REPO / ".tmp" / "hsp-integration-smoke" / "run.json"
_SCHEMA = "hsp_integration_smoke_run/1.0"
_PROG = "hsp_integration_smoke"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--verify",
        action="store_true",
        help="Exit 0 when all selected integration gates pass.",
    )
    p.add_argument(
        "--full",
        action="store_true",
        help="Also run torch gates (hybrid RAG, glue, live HTTP server).",
    )
    p.add_argument(
        "--model",
        type=str,
        default=None,
        help="Checkpoint for --full torch gates (default: rag_faq_smoke picker).",
    )
    p.add_argument("--output-json", type=str, default="", help=f"Write run JSON (default: {_OUT}).")
    return p


def _run_gate(name: str, argv: list[str]) -> dict[str, Any]:
    cmd = [sys.executable, str(_scripts / argv[0]), *argv[1:]]
    r = subprocess.run(
        cmd,
        cwd=_REPO,
        capture_output=True,
        text=True,
        timeout=900,
    )
    ok = r.returncode == 0
    row: dict[str, Any] = {
        "name": name,
        "cmd": " ".join(argv),
        "ok": ok,
        "exit_code": r.returncode,
    }
    if not ok:
        row["stderr_tail"] = r.stderr[-2000:] if r.stderr else ""
        row["stdout_tail"] = r.stdout[-2000:] if r.stdout else ""
    return row


def run_verify(model: str | None, full: bool) -> tuple[bool, dict[str, Any]]:
    stdlib_gates: list[tuple[str, list[str]]] = [
        ("corpus", ["hsp_corpus_smoke.py", "--verify"]),
        ("lexical_rag", ["hsp_rag_smoke.py", "--verify"]),
        ("phase3_contract", ["hsp_phase3_contract_smoke.py", "--verify"]),
        ("corpus_export", ["hsp_corpus_export.py", "--verify"]),
        ("meta_contract", ["hsp_meta_contract_smoke.py", "--verify"]),
        ("screen_context", ["hsp_screen_context_smoke.py", "--verify"]),
        ("reference_client", ["hsp_reference_client_smoke.py", "--verify"]),
        ("ub_eval", ["ub_eval_runner.py", "--verify"]),
    ]

    rows: list[dict[str, Any]] = []
    for name, argv in stdlib_gates:
        row = _run_gate(name, argv)
        rows.append(row)
        if not row["ok"]:
            print(f"{_PROG}: FAIL gate {name}", file=sys.stderr)
            if row.get("stderr_tail"):
                print(row["stderr_tail"], file=sys.stderr)
            raise SystemExit(1)

    torch_gates: list[tuple[str, list[str]]] = []
    model_id: str | None = None
    if full:
        from rag_faq_smoke import _pick_model

        model_id = _pick_model(model)
        torch_gates = [
            ("hybrid_rag", ["hsp_rag_hybrid_smoke.py", "--verify", "--model", model_id]),
            (
                "route_then_retrieve",
                ["hsp_route_then_retrieve.py", "--verify", "--model", model_id],
            ),
            (
                "live_server",
                ["hsp_phase3_server_smoke.py", "--verify", "--model", model_id],
            ),
        ]
        for name, argv in torch_gates:
            row = _run_gate(name, argv)
            rows.append(row)
            if not row["ok"]:
                print(f"{_PROG}: FAIL gate {name}", file=sys.stderr)
                if row.get("stderr_tail"):
                    print(row["stderr_tail"], file=sys.stderr)
                raise SystemExit(1)

    passed = sum(1 for r in rows if r["ok"])
    artifact = {
        "schema": _SCHEMA,
        "mode": "full" if full else "stdlib",
        "model": model_id,
        "gates_total": len(rows),
        "gates_passed": passed,
        "ok": passed == len(rows),
        "gates": rows,
    }
    return True, artifact


def main() -> None:
    args = build_parser().parse_args()
    if not args.verify:
        build_parser().print_help()
        raise SystemExit(2)

    try:
        ok, artifact = run_verify(args.model, args.full)
    except subprocess.TimeoutExpired as e:
        print(f"{_PROG}: FAIL timeout {e}", file=sys.stderr)
        raise SystemExit(1) from e

    out_path = Path(args.output_json) if args.output_json else _OUT
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")

    print(
        f"{_PROG}: mode={artifact['mode']} gates={artifact['gates_passed']}/{artifact['gates_total']} ok={ok}"
    )
    print(f"{_PROG} verify: OK")


if __name__ == "__main__":
    main()
