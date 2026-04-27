#!/usr/bin/env python3
"""Horizon 19: append-only audit hash chain — tamper-evident event log (lite).

Computes consecutive SHA-256 links over synthetic audit lines; verifies that altering
any payload breaks verification from that point onward. Writes horizon19_audit_chain_run/1.0."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_SCHEMA = "horizon19_audit_chain_run/1.0"
_OUT = _REPO / ".tmp" / "horizon19-audit-chain" / "run.json"

GENESIS = "0" * 64


def link(prev_hex: str, payload: str) -> str:
    raw = (prev_hex + "\n" + payload).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def build_chain(events: list[str]) -> list[str]:
    h = GENESIS
    out = [h]
    for e in events:
        h = link(h, e)
        out.append(h)
    return out


def verify_chain(chain_hex: list[str], events: list[str]) -> bool:
    if chain_hex[0] != GENESIS:
        return False
    x = GENESIS
    for i, e in enumerate(events):
        expect = link(x, e)
        if chain_hex[i + 1] != expect:
            return False
        x = expect
    return True


def run_verify() -> tuple[dict, bool]:
    events = [
        '{"action":"policy_update","who":"admin"}',
        '{"action":"memory_put","scope":"org:a"}',
        '{"action":"model_rollout","pct":25}',
    ]
    chain = build_chain(events)
    intact = verify_chain(chain, events)

    tampered_events = list(events)
    tampered_events[1] = '{"action":"memory_put","scope":"org:evil"}'
    tampered_ok = verify_chain(chain, tampered_events)

    ok = intact and not tampered_ok
    return (
        {
            "genesis": GENESIS,
            "events_count": len(events),
            "chain_tail": chain[-1],
            "verify_original_chain_ok": intact,
            "tampered_middle_detected": not tampered_ok,
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
        "horizon": 19,
        "schema": _SCHEMA,
        "mode": "audit_hash_chain_smoke",
        "ok": ok,
        **body,
        "note": "Production uses Merkle trees, signing keys, or WORM storage; this is an integrity toy.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon19 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon19 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
