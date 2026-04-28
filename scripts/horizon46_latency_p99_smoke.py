#!/usr/bin/env python3
"""Horizon 46: latency p99 vs ceiling — SLO percentile smoke.

Loads texts/horizon46_latency_p99_sample.json; p99 rank uses ceil(0.99*n)-1 on sorted ms.
Writes horizon46_latency_p99_run/1.0."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "texts" / "horizon46_latency_p99_sample.json"
_SCHEMA = "horizon46_latency_p99_run/1.0"
_OUT = _REPO / ".tmp" / "horizon46-latency-p99" / "run.json"


def percentile_99_ms(samples: list[float | int]) -> float:
    if not samples:
        return 0.0
    s = sorted(float(x) for x in samples)
    n = len(s)
    idx = max(0, min(n - 1, int(math.ceil(0.99 * n)) - 1))
    return s[idx]


def run_verify(path: Path) -> tuple[dict, bool]:
    m = json.loads(path.read_text(encoding="utf-8"))
    ceiling = float(m["max_p99_ms"])
    rows = []
    ok = True
    for i, sc in enumerate(m["scenarios"]):
        samples = sc["samples_ms"]
        exp_under = bool(sc["expect_under_budget"])
        p99 = percentile_99_ms(samples)
        under = p99 <= ceiling
        row_ok = under == exp_under
        ok = ok and row_ok
        rows.append(
            {
                "scenario_index": i,
                "sample_count": len(samples),
                "p99_ms": p99,
                "under_budget": under,
                "expect_under_budget": exp_under,
                "match": row_ok,
            }
        )
    body = {
        "manifest_path": str(path.relative_to(_REPO)) if path.is_relative_to(_REPO) else str(path),
        "max_p99_ms": ceiling,
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
        "horizon": 46,
        "schema": _SCHEMA,
        "mode": "latency_p99_smoke",
        "ok": ok,
        **body,
        "note": "Production adds HDR histograms, weighted tail budgets, and tenant slices.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon46 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon46 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
