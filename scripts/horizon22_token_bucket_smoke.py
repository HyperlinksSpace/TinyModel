#!/usr/bin/env python3
"""Horizon 22: token bucket rate limiting — refill ticks vs consume attempts.

Loads texts/horizon22_token_bucket_sample.json and checks expect_allow per step.
Writes horizon22_token_bucket_run/1.0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "texts" / "horizon22_token_bucket_sample.json"
_SCHEMA = "horizon22_token_bucket_run/1.0"
_OUT = _REPO / ".tmp" / "horizon22-token-bucket" / "run.json"


def simulate(path: Path) -> tuple[dict, bool]:
    m = json.loads(path.read_text(encoding="utf-8"))
    cap = int(m["capacity"])
    refill = int(m["refill_per_tick"])
    tokens = int(m["initial_tokens"])
    steps_out = []
    ok = True
    for step in m["steps"]:
        kind = step["kind"]
        if kind == "tick":
            tokens = min(cap, tokens + refill)
            steps_out.append({"kind": "tick", "tokens_after": tokens})
            continue
        if kind != "consume":
            raise ValueError(f"unknown step kind: {kind}")
        n = int(step["tokens"])
        expect = step["expect_allow"]
        allow = tokens >= n
        ok = ok and allow == expect
        if allow:
            tokens -= n
        steps_out.append(
            {
                "kind": "consume",
                "tokens": n,
                "expect_allow": expect,
                "got_allow": allow,
                "tokens_after": tokens,
                "match": allow == expect,
            }
        )
    body = {
        "manifest_path": str(path.relative_to(_REPO)) if path.is_relative_to(_REPO) else str(path),
        "capacity": cap,
        "steps": steps_out,
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
    body, ok = simulate(path)
    out = Path(a.output_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "horizon": 22,
        "schema": _SCHEMA,
        "mode": "token_bucket_smoke",
        "ok": ok,
        **body,
        "note": "Production adds wall-clock refill, distributed quotas, and per-tenant buckets.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon22 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon22 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
