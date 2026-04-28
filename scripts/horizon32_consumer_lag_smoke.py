#!/usr/bin/env python3
"""Horizon 32: consumer lag — backlog vs allowed lag budget.

Loads texts/horizon32_consumer_lag_sample.json; lag = max(0, hwm - consumer_pos).
Writes horizon32_consumer_lag_run/1.0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "texts" / "horizon32_consumer_lag_sample.json"
_SCHEMA = "horizon32_consumer_lag_run/1.0"
_OUT = _REPO / ".tmp" / "horizon32-consumer-lag" / "run.json"


def lag_units(hwm: int, consumer_pos: int) -> int:
    return max(0, int(hwm) - int(consumer_pos))


def within_budget(hwm: int, consumer_pos: int, max_lag: int) -> bool:
    return lag_units(hwm, consumer_pos) <= int(max_lag)


def run_verify(path: Path) -> tuple[dict, bool]:
    m = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    ok = True
    for sc in m["scenarios"]:
        hwm = int(sc["high_water_mark"])
        cp = int(sc["consumer_position"])
        mx = int(sc["max_lag_allowed"])
        exp = bool(sc["expect_within_lag_budget"])
        lg = lag_units(hwm, cp)
        got = lg <= mx
        row_ok = got == exp
        ok = ok and row_ok
        rows.append(
            {
                "high_water_mark": hwm,
                "consumer_position": cp,
                "lag_units": lg,
                "max_lag_allowed": mx,
                "within_lag_budget": got,
                "expect_within_lag_budget": exp,
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
        "horizon": 32,
        "schema": _SCHEMA,
        "mode": "consumer_lag_smoke",
        "ok": ok,
        **body,
        "note": "Wire lag to autoscale, backlog alerts, and streaming checkpoint semantics.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon32 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon32 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
