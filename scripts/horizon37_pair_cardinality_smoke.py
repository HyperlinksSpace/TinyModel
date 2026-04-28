#!/usr/bin/env python3
"""Horizon 37: pair cardinality — distinct dimension pairs vs pair budget.

Loads texts/horizon37_pair_cardinality_sample.json; counts unique (dim_a, dim_b).
Writes horizon37_pair_cardinality_run/1.0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "texts" / "horizon37_pair_cardinality_sample.json"
_SCHEMA = "horizon37_pair_cardinality_run/1.0"
_OUT = _REPO / ".tmp" / "horizon37-pair-cardinality" / "run.json"


def pair_count(rows: list[dict[str, str]]) -> int:
    pairs: set[tuple[str, str]] = set()
    for row in rows:
        pairs.add((row["dim_a"], row["dim_b"]))
    return len(pairs)


def within_budget(max_pairs: int, rows: list[dict[str, str]]) -> bool:
    return pair_count(rows) <= max_pairs


def run_verify(path: Path) -> tuple[dict, bool]:
    m = json.loads(path.read_text(encoding="utf-8"))
    out_rows = []
    ok = True
    for i, sc in enumerate(m["scenarios"]):
        mx = int(sc["max_distinct_pairs"])
        rws = sc["rows"]
        exp = bool(sc["expect_within_budget"])
        n = pair_count(rws)
        got = n <= mx
        row_ok = got == exp
        ok = ok and row_ok
        out_rows.append(
            {
                "scenario_index": i,
                "distinct_pairs": n,
                "max_distinct_pairs": mx,
                "within_budget": got,
                "expect_within_budget": exp,
                "match": row_ok,
            }
        )
    body = {
        "manifest_path": str(path.relative_to(_REPO)) if path.is_relative_to(_REPO) else str(path),
        "scenarios": out_rows,
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
        "horizon": 37,
        "schema": _SCHEMA,
        "mode": "pair_cardinality_smoke",
        "ok": ok,
        **body,
        "note": "Pairs explode metric series; combine with H31 single-dimension caps and sampling.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon37 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon37 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
