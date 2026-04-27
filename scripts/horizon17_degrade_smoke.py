#!/usr/bin/env python3
"""Horizon 17: graceful degradation ladder — map health score to service tier.

FULL / DEGRADED / MINIMAL / OFFLINE thresholds; used for UX and routing when dependencies fail.
Writes horizon17_degrade_run/1.0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_SCHEMA = "horizon17_degrade_run/1.0"
_OUT = _REPO / ".tmp" / "horizon17-degrade" / "run.json"


def tier_for_score(score: int) -> str:
    if score >= 90:
        return "FULL"
    if score >= 50:
        return "DEGRADED"
    if score >= 10:
        return "MINIMAL"
    return "OFFLINE"


def run_verify() -> tuple[dict, bool]:
    cases = [
        (100, "FULL"),
        (90, "FULL"),
        (89, "DEGRADED"),
        (50, "DEGRADED"),
        (49, "MINIMAL"),
        (10, "MINIMAL"),
        (9, "OFFLINE"),
        (0, "OFFLINE"),
    ]
    ok = True
    trace = []
    for score, want in cases:
        got = tier_for_score(score)
        step_ok = got == want
        ok = ok and step_ok
        trace.append({"score": score, "expect_tier": want, "got_tier": got, "ok": step_ok})
    return (
        {
            "thresholds": {"FULL_ge": 90, "DEGRADED_ge": 50, "MINIMAL_ge": 10, "OFFLINE_else": True},
            "cases": trace,
        },
        ok,
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verify", action="store_true")
    p.add_argument("--output-json", type=str, default=str(_OUT))
    return p.parse_args()


def main() -> int:
    a = parse_args()
    if not a.verify:
        print("Use --verify.", file=sys.stderr)
        return 2
    body, ok = run_verify()
    out = Path(a.output_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "horizon": 17,
        "schema": _SCHEMA,
        "mode": "degradation_tier_smoke",
        "ok": ok,
        **body,
        "note": "Tune thresholds per product; combine with H13 circuit breaker and H10 budgets.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon17 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon17 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
