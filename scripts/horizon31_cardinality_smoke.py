#!/usr/bin/env python3
"""Horizon 31: cardinality budgets — max distinct values per dimension per batch.

Loads texts/horizon31_cardinality_sample.json; compares observed counts to caps.
Writes horizon31_cardinality_run/1.0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "texts" / "horizon31_cardinality_sample.json"
_SCHEMA = "horizon31_cardinality_run/1.0"
_OUT = _REPO / ".tmp" / "horizon31-cardinality" / "run.json"


def within_budget(max_distinct: dict[str, int], rows: list[dict]) -> bool:
    dims = list(max_distinct.keys())
    for d in dims:
        vals = {row[d] for row in rows if d in row}
        if len(vals) > max_distinct[d]:
            return False
    return True


def run_verify(path: Path) -> tuple[dict, bool]:
    m = json.loads(path.read_text(encoding="utf-8"))
    rows_out = []
    ok = True
    for i, sc in enumerate(m["scenarios"]):
        caps = sc["max_distinct"]
        rws = sc["rows"]
        exp = bool(sc["expect_within_budget"])
        got = within_budget(caps, rws)
        row_ok = got == exp
        ok = ok and row_ok
        counts = {d: len({row[d] for row in rws if d in row}) for d in caps}
        rows_out.append(
            {
                "scenario_index": i,
                "distinct_counts": counts,
                "max_distinct": caps,
                "within_budget": got,
                "expect_within_budget": exp,
                "match": row_ok,
            }
        )
    body = {
        "manifest_path": str(path.relative_to(_REPO)) if path.is_relative_to(_REPO) else str(path),
        "scenarios": rows_out,
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
        "horizon": 31,
        "schema": _SCHEMA,
        "mode": "cardinality_budget_smoke",
        "ok": ok,
        **body,
        "note": "Production adds sliding windows, per-tenant quotas, and approximate sketches.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon31 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon31 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
