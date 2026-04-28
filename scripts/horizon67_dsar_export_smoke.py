#!/usr/bin/env python3
"""Horizon 67: DSAR export SLA — privacy turnaround gate for regulated tiers.

Loads texts/horizon67_dsar_export_sample.json; compliant iff tier not listed or hours ≤ max.
Writes horizon67_dsar_export_run/1.0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "texts" / "horizon67_dsar_export_sample.json"
_SCHEMA = "horizon67_dsar_export_run/1.0"
_OUT = _REPO / ".tmp" / "horizon67-dsar-export" / "run.json"


def run_verify(path: Path) -> tuple[dict, bool]:
    m = json.loads(path.read_text(encoding="utf-8"))
    tiers = {str(x).lower().strip() for x in m["customer_tiers_requiring_fast_export"]}
    mx = int(m["max_hours_to_complete_export"])
    rows = []
    ok = True
    for ch in m["checks"]:
        tier = str(ch["customer_tier"]).lower().strip()
        hrs = int(ch["hours_to_complete_export"])
        exp = bool(ch["expect_compliant"])
        needs = tier in tiers
        got = (not needs) or (hrs <= mx)
        row_ok = got == exp
        ok = ok and row_ok
        rows.append(
            {
                "customer_tier": tier,
                "requires_fast_export": needs,
                "hours_to_complete_export": hrs,
                "compliant": got,
                "expect_compliant": exp,
                "match": row_ok,
            }
        )
    body = {
        "manifest_path": str(path.relative_to(_REPO)) if path.is_relative_to(_REPO) else str(path),
        "max_hours_to_complete_export": mx,
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
        "horizon": 67,
        "schema": _SCHEMA,
        "mode": "dsar_export_smoke",
        "ok": ok,
        **body,
        "note": "Production adds identity proofs, jurisdictional carve-outs, and audit receipts.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon67 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon67 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
