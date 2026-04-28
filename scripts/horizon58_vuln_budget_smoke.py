#!/usr/bin/env python3
"""Horizon 58: vulnerability budget — critical/high open advisory ceilings.

Loads texts/horizon58_vuln_budget_sample.json; compliant iff counts ≤ configured maxima.
Writes horizon58_vuln_budget_run/1.0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "texts" / "horizon58_vuln_budget_sample.json"
_SCHEMA = "horizon58_vuln_budget_run/1.0"
_OUT = _REPO / ".tmp" / "horizon58-vuln-budget" / "run.json"


def run_verify(path: Path) -> tuple[dict, bool]:
    m = json.loads(path.read_text(encoding="utf-8"))
    mx_c = int(m["max_critical_open"])
    mx_h = int(m["max_high_open"])
    rows = []
    ok = True
    for ch in m["checks"]:
        c = int(ch["critical_open"])
        h = int(ch["high_open"])
        exp = bool(ch["expect_compliant"])
        got = (c <= mx_c) and (h <= mx_h)
        row_ok = got == exp
        ok = ok and row_ok
        rows.append(
            {
                "critical_open": c,
                "high_open": h,
                "compliant": got,
                "expect_compliant": exp,
                "match": row_ok,
            }
        )
    body = {
        "manifest_path": str(path.relative_to(_REPO)) if path.is_relative_to(_REPO) else str(path),
        "max_critical_open": mx_c,
        "max_high_open": mx_h,
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
        "horizon": 58,
        "schema": _SCHEMA,
        "mode": "vuln_budget_smoke",
        "ok": ok,
        **body,
        "note": "Production adds SBOM diffing, waiver workflows, and scanner quorum.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon58 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon58 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
