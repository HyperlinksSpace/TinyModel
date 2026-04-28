#!/usr/bin/env python3
"""Horizon 40: composite policy AND — all gates must pass.

Loads texts/horizon40_policy_and_sample.json; composite_ok = all(gate.pass).
Writes horizon40_policy_and_run/1.0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "texts" / "horizon40_policy_and_sample.json"
_SCHEMA = "horizon40_policy_and_run/1.0"
_OUT = _REPO / ".tmp" / "horizon40-policy-and" / "run.json"


def composite_all_pass(gates: list[dict]) -> bool:
    return all(bool(g["pass"]) for g in gates)


def run_verify(path: Path) -> tuple[dict, bool]:
    m = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    ok = True
    for i, sc in enumerate(m["scenarios"]):
        gates = sc["gates"]
        exp = bool(sc["expect_all_pass"])
        got = composite_all_pass(gates)
        row_ok = got == exp
        ok = ok and row_ok
        rows.append(
            {
                "scenario_index": i,
                "gate_count": len(gates),
                "all_pass": got,
                "expect_all_pass": exp,
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
        "horizon": 40,
        "schema": _SCHEMA,
        "mode": "policy_and_smoke",
        "ok": ok,
        **body,
        "note": "Extend with OR groups, weighted scores, and exception workflows.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon40 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon40 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
