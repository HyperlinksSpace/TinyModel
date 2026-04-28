#!/usr/bin/env python3
"""Horizon 26: SLO error budget — observed errors vs allowed failures over window.

Loads texts/horizon26_error_budget_sample.json; max_errors = floor(window * (100-avail)/100).
Writes horizon26_error_budget_run/1.0."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "texts" / "horizon26_error_budget_sample.json"
_SCHEMA = "horizon26_error_budget_run/1.0"
_OUT = _REPO / ".tmp" / "horizon26-error-budget" / "run.json"


def max_allowed_errors(window_requests: int, availability_target_pct: float) -> int:
    """Failures allowed while meeting availability_target_pct success fraction."""
    bad_pct = max(0.0, 100.0 - float(availability_target_pct))
    return int(math.floor(float(window_requests) * bad_pct / 100.0 + 1e-9))


def within_budget(window_requests: int, availability_target_pct: float, errors_observed: int) -> bool:
    return errors_observed <= max_allowed_errors(window_requests, availability_target_pct)


def run_verify(path: Path) -> tuple[dict, bool]:
    m = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    ok = True
    for sc in m["scenarios"]:
        wr = int(sc["window_requests"])
        av = float(sc["availability_target_pct"])
        eo = int(sc["errors_observed"])
        exp = bool(sc["expect_within_budget"])
        max_e = max_allowed_errors(wr, av)
        got = within_budget(wr, av, eo)
        row_ok = got == exp
        ok = ok and row_ok
        rows.append(
            {
                "availability_target_pct": av,
                "window_requests": wr,
                "errors_observed": eo,
                "max_allowed_errors": max_e,
                "within_budget": got,
                "expect_within_budget": exp,
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
        "horizon": 26,
        "schema": _SCHEMA,
        "mode": "error_budget_smoke",
        "ok": ok,
        **body,
        "note": "Pairs with probes (H8), canary gates (H24), and incident reviews when budget is spent.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon26 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon26 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
