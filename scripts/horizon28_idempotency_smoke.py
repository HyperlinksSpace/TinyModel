#!/usr/bin/env python3
"""Horizon 28: idempotency ledger — dedupe keyed side-effect requests.

Loads texts/horizon28_idempotency_sample.json; first key wins; count suppressed repeats.
Writes horizon28_idempotency_run/1.0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "texts" / "horizon28_idempotency_sample.json"
_SCHEMA = "horizon28_idempotency_run/1.0"
_OUT = _REPO / ".tmp" / "horizon28-idempotency" / "run.json"


def simulate(events: list[dict]) -> tuple[list[str], int]:
    seen: set[str] = set()
    order: list[str] = []
    suppressed = 0
    for ev in events:
        k = ev["idempotency_key"]
        if k in seen:
            suppressed += 1
        else:
            seen.add(k)
            order.append(k)
    return order, suppressed


def run_verify(path: Path) -> tuple[dict, bool]:
    m = json.loads(path.read_text(encoding="utf-8"))
    events = m["events"]
    order, suppressed = simulate(events)
    exp_order = list(m["expect_unique_order"])
    exp_sup = int(m["expect_suppressed_duplicates"])
    ok = order == exp_order and suppressed == exp_sup
    body = {
        "manifest_path": str(path.relative_to(_REPO)) if path.is_relative_to(_REPO) else str(path),
        "events_total": len(events),
        "unique_order": order,
        "expect_unique_order": exp_order,
        "suppressed_duplicates": suppressed,
        "expect_suppressed_duplicates": exp_sup,
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
        "horizon": 28,
        "schema": _SCHEMA,
        "mode": "idempotency_ledger_smoke",
        "ok": ok,
        **body,
        "note": "Production adds TTL stores, conflict detection on mismatched payloads, and durable logs.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon28 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon28 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
