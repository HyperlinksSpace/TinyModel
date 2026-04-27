#!/usr/bin/env python3
"""Horizon 18: operational readiness checklist — structured game-day / launch gates.

Loads texts/horizon18_readiness_sample.json and simulates passing required checks.
Writes horizon18_readiness_run/1.0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "texts" / "horizon18_readiness_sample.json"
_SCHEMA = "horizon18_readiness_run/1.0"
_OUT = _REPO / ".tmp" / "horizon18-readiness" / "run.json"


def simulate_check(check_id: str) -> bool:
    """Demo: all checks pass except ids containing '_fail_demo'."""
    return "_fail_demo" not in check_id


def run_verify(path: Path) -> tuple[dict, bool]:
    m = json.loads(path.read_text(encoding="utf-8"))
    phases = m["phases"]
    rows = []
    ok = True
    for ph in phases:
        pname = ph["name"]
        for ch in ph["checks"]:
            cid = ch["id"]
            req = ch.get("required", False)
            passed = simulate_check(cid)
            row_ok = passed or not req
            ok = ok and row_ok
            rows.append(
                {
                    "phase": pname,
                    "check_id": cid,
                    "required": req,
                    "passed": passed,
                    "gate_ok": row_ok,
                }
            )
    return (
        {
            "manifest_path": str(path.relative_to(_REPO)) if path.is_relative_to(_REPO) else str(path),
            "checks": rows,
        },
        ok,
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verify", action="store_true")
    p.add_argument("--manifest", type=str, default=str(_DEFAULT))
    p.add_argument("--output-json", type=str, default=str(_OUT))
    return p.parse_args()


def main() -> int:
    a = parse_args()
    if not a.verify:
        print("Use --verify.", file=sys.stderr)
        return 2
    path = Path(a.manifest)
    if not path.is_file():
        print(f"Missing: {path}", file=sys.stderr)
        return 1
    body, ok = run_verify(path)
    out = Path(a.output_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "horizon": 18,
        "schema": _SCHEMA,
        "mode": "readiness_checklist_smoke",
        "ok": ok,
        **body,
        "note": "Wire simulate_check to real CI/API probes in production.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon18 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon18 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
