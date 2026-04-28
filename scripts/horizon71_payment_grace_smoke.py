#!/usr/bin/env python3
"""Horizon 71: payment overdue grace — subscription continuity gate.

Loads texts/horizon71_payment_grace_sample.json; allow_service iff hours_past_due ≤ max_hours_past_due_allowed.
Writes horizon71_payment_grace_run/1.0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "texts" / "horizon71_payment_grace_sample.json"
_SCHEMA = "horizon71_payment_grace_run/1.0"
_OUT = _REPO / ".tmp" / "horizon71-payment-grace" / "run.json"


def run_verify(path: Path) -> tuple[dict, bool]:
    m = json.loads(path.read_text(encoding="utf-8"))
    mx = int(m["max_hours_past_due_allowed"])
    rows = []
    ok = True
    for ch in m["checks"]:
        hrs = int(ch["hours_past_due"])
        exp = bool(ch["expect_allow_service"])
        got = hrs <= mx
        row_ok = got == exp
        ok = ok and row_ok
        rows.append(
            {
                "hours_past_due": hrs,
                "allow_service": got,
                "expect_allow_service": exp,
                "match": row_ok,
            }
        )
    body = {
        "manifest_path": str(path.relative_to(_REPO)) if path.is_relative_to(_REPO) else str(path),
        "max_hours_past_due_allowed": mx,
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
        "horizon": 71,
        "schema": _SCHEMA,
        "mode": "payment_grace_smoke",
        "ok": ok,
        **body,
        "note": "Production adds dunning ladders, jurisdiction-specific terms, and hardship workflows.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon71 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon71 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
