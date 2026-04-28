#!/usr/bin/env python3
"""Horizon 34: quorum / strict majority — yes votes vs replica count.

Loads texts/horizon34_quorum_sample.json; strict majority iff votes_yes * 2 > replicas_total.
Writes horizon34_quorum_run/1.0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "texts" / "horizon34_quorum_sample.json"
_SCHEMA = "horizon34_quorum_run/1.0"
_OUT = _REPO / ".tmp" / "horizon34-quorum" / "run.json"


def strict_majority(votes_yes: int, replicas_total: int) -> bool:
    if replicas_total <= 0:
        return False
    return votes_yes * 2 > replicas_total


def run_verify(path: Path) -> tuple[dict, bool]:
    m = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    ok = True
    for sc in m["scenarios"]:
        r = int(sc["replicas_total"])
        vy = int(sc["votes_yes"])
        exp = bool(sc["expect_strict_majority"])
        got = strict_majority(vy, r)
        row_ok = got == exp
        ok = ok and row_ok
        rows.append(
            {
                "replicas_total": r,
                "votes_yes": vy,
                "strict_majority": got,
                "expect_strict_majority": exp,
                "match": row_ok,
            }
        )
    body = {
        "manifest_path": str(path.relative_to(_REPO)) if path.is_relative_to(_REPO) else str(path),
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
        "horizon": 34,
        "schema": _SCHEMA,
        "mode": "quorum_strict_majority_smoke",
        "ok": ok,
        **body,
        "note": "Production adds Byzantine faults, weighted votes, and partition semantics.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon34 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon34 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
