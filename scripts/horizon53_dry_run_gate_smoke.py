#!/usr/bin/env python3
"""Horizon 53: dry-run gate — mutating ops blocked in simulation mode.

Loads texts/horizon53_dry_run_gate_sample.json; allow iff not (dry_run and mutating_operation).
Writes horizon53_dry_run_gate_run/1.0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "texts" / "horizon53_dry_run_gate_sample.json"
_SCHEMA = "horizon53_dry_run_gate_run/1.0"
_OUT = _REPO / ".tmp" / "horizon53-dry-run-gate" / "run.json"


def run_verify(path: Path) -> tuple[dict, bool]:
    m = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    ok = True
    for ch in m["checks"]:
        dry = bool(ch["dry_run"])
        mut = bool(ch["mutating_operation"])
        exp = bool(ch["expect_allow"])
        got = not (dry and mut)
        row_ok = got == exp
        ok = ok and row_ok
        rows.append(
            {
                "dry_run": dry,
                "mutating_operation": mut,
                "allow": got,
                "expect_allow": exp,
                "match": row_ok,
            }
        )
    body = {
        "manifest_path": str(path.relative_to(_REPO)) if path.is_relative_to(_REPO) else str(path),
        "checks": rows,
    }
    return body, ok


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
        "horizon": 53,
        "schema": _SCHEMA,
        "mode": "dry_run_gate_smoke",
        "ok": ok,
        **body,
        "note": "Production adds shadow writes, fenced sandboxes, and audit replay.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon53 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon53 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
