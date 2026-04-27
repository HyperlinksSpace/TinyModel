#!/usr/bin/env python3
"""Horizon 23: blast radius — transitive failure over dependency edges.

Loads texts/horizon23_blast_sample.json; propagates failure from failure_origin.
Writes horizon23_blast_radius_run/1.0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "texts" / "horizon23_blast_sample.json"
_SCHEMA = "horizon23_blast_radius_run/1.0"
_OUT = _REPO / ".tmp" / "horizon23-blast-radius" / "run.json"


def impacted(origin: str, edges: list[dict[str, str]]) -> list[str]:
    failed: set[str] = {origin}
    changed = True
    while changed:
        changed = False
        for e in edges:
            dep = e["dependent"]
            req = e["depends_on"]
            if req in failed and dep not in failed:
                failed.add(dep)
                changed = True
    return sorted(failed)


def run_verify(path: Path) -> tuple[dict, bool]:
    m = json.loads(path.read_text(encoding="utf-8"))
    edges = m["edges"]
    rows = []
    ok = True
    for sc in m["scenarios"]:
        origin = sc["failure_origin"]
        got = impacted(origin, edges)
        exp = list(sc["expect_impacted_sorted"])
        row_ok = got == exp
        ok = ok and row_ok
        rows.append(
            {
                "failure_origin": origin,
                "expect_impacted_sorted": exp,
                "got_impacted_sorted": got,
                "match": row_ok,
            }
        )
    body = {
        "manifest_path": str(path.relative_to(_REPO)) if path.is_relative_to(_REPO) else str(path),
        "edge_count": len(edges),
        "scenarios": rows,
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
        "horizon": 23,
        "schema": _SCHEMA,
        "mode": "blast_radius_smoke",
        "ok": ok,
        **body,
        "note": "Real topologies need redundancy modeling, partial failures, and SLO graphs.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon23 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon23 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
