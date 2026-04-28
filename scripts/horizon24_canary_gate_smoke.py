#!/usr/bin/env python3
"""Horizon 24: canary regression gate — baseline vs candidate metrics.

Loads texts/horizon24_canary_gate_sample.json; checks regression vs max_regression_pct.
Writes horizon24_canary_gate_run/1.0."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "texts" / "horizon24_canary_gate_sample.json"
_SCHEMA = "horizon24_canary_gate_run/1.0"
_OUT = _REPO / ".tmp" / "horizon24-canary-gate" / "run.json"


def regression_pct(baseline: float, candidate: float, worse_direction: str) -> float:
    """Non-negative regression percentage when candidate is worse than baseline; else 0."""
    if worse_direction == "up":
        if candidate <= baseline:
            return 0.0
        if baseline == 0.0:
            return math.inf if candidate > baseline else 0.0
        return (candidate - baseline) / abs(baseline) * 100.0
    if worse_direction == "down":
        if candidate >= baseline:
            return 0.0
        if baseline == 0.0:
            return math.inf if candidate < baseline else 0.0
        return (baseline - candidate) / abs(baseline) * 100.0
    raise ValueError(f"worse_direction: {worse_direction}")


def run_verify(path: Path) -> tuple[dict, bool]:
    m = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    ok = True
    for g in m["gates"]:
        base = float(g["baseline"])
        cand = float(g["candidate"])
        wd = g["worse_direction"]
        max_pct = float(g["max_regression_pct"])
        exp_pass = bool(g["expect_pass"])
        pct = regression_pct(base, cand, wd)
        gate_ok = pct <= max_pct + 1e-9  # float tolerance
        row_ok = gate_ok == exp_pass
        ok = ok and row_ok
        rows.append(
            {
                "metric": g["metric"],
                "baseline": base,
                "candidate": cand,
                "worse_direction": wd,
                "regression_pct": pct if math.isfinite(pct) else None,
                "max_regression_pct": max_pct,
                "gate_ok": gate_ok,
                "expect_pass": exp_pass,
                "match": row_ok,
            }
        )
    body = {
        "manifest_path": str(path.relative_to(_REPO)) if path.is_relative_to(_REPO) else str(path),
        "gates_evaluated": len(rows),
        "gates": rows,
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
        "horizon": 24,
        "schema": _SCHEMA,
        "mode": "canary_regression_gate_smoke",
        "ok": ok,
        **body,
        "note": "Production ties CI benchmark JSON and deployment hooks to automated promotion gates.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon24 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon24 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
