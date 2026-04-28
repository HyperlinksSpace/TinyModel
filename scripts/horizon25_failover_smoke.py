#!/usr/bin/env python3
"""Horizon 25: regional failover — first healthy route from preference list.

Loads texts/horizon25_failover_sample.json; selects first preference_order not in unhealthy.
Writes horizon25_failover_run/1.0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "texts" / "horizon25_failover_sample.json"
_SCHEMA = "horizon25_failover_run/1.0"
_OUT = _REPO / ".tmp" / "horizon25-failover" / "run.json"


def route(preference_order: list[str], unhealthy: list[str]) -> str | None:
    bad = set(unhealthy)
    for r in preference_order:
        if r not in bad:
            return r
    return None


def run_verify(path: Path) -> tuple[dict, bool]:
    m = json.loads(path.read_text(encoding="utf-8"))
    pref = list(m["preference_order"])
    rows = []
    ok = True
    for sc in m["scenarios"]:
        uh = list(sc["unhealthy"])
        exp = sc["expect_route"]
        got = route(pref, uh)
        row_ok = got == exp
        ok = ok and row_ok
        rows.append(
            {
                "unhealthy": uh,
                "expect_route": exp,
                "got_route": got,
                "match": row_ok,
            }
        )
    body = {
        "manifest_path": str(path.relative_to(_REPO)) if path.is_relative_to(_REPO) else str(path),
        "preference_order": pref,
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
        "horizon": 25,
        "schema": _SCHEMA,
        "mode": "failover_route_smoke",
        "ok": ok,
        **body,
        "note": "Extend with health probes, latency-weighted routing, and data residency rules.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon25 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon25 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
