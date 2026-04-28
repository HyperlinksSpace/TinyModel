#!/usr/bin/env python3
"""Horizon 48: dual control — minimum distinct approvers.

Loads texts/horizon48_dual_control_sample.json; pass iff len(set(approver_ids)) >= min_distinct_approvers.
Writes horizon48_dual_control_run/1.0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "texts" / "horizon48_dual_control_sample.json"
_SCHEMA = "horizon48_dual_control_run/1.0"
_OUT = _REPO / ".tmp" / "horizon48-dual-control" / "run.json"


def run_verify(path: Path) -> tuple[dict, bool]:
    m = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    ok = True
    for ch in m["checks"]:
        ids = [str(x) for x in ch["approver_ids"]]
        need = int(ch["min_distinct_approvers"])
        exp = bool(ch["expect_pass"])
        distinct = len(set(ids))
        got = distinct >= need
        row_ok = got == exp
        ok = ok and row_ok
        rows.append(
            {
                "distinct_count": distinct,
                "min_distinct_approvers": need,
                "pass_gate": got,
                "expect_pass": exp,
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
        "horizon": 48,
        "schema": _SCHEMA,
        "mode": "dual_control_smoke",
        "ok": ok,
        **body,
        "note": "Production adds hardware tokens, duty calendars, and segregation-of-duties proofs.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon48 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon48 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
