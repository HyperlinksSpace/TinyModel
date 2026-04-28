#!/usr/bin/env python3
"""Horizon 30: time-bounded leases — active iff check in [acquired, acquired + ttl).

Loads texts/horizon30_lease_sample.json. ISO-8601 times; Z as UTC.
Writes horizon30_lease_run/1.0."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "texts" / "horizon30_lease_sample.json"
_SCHEMA = "horizon30_lease_run/1.0"
_OUT = _REPO / ".tmp" / "horizon30-lease" / "run.json"


def parse_iso(s: str) -> datetime:
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


def lease_active(acquired_iso: str, ttl_sec: int, check_iso: str) -> bool:
    acquired = parse_iso(acquired_iso)
    check = parse_iso(check_iso)
    if check.tzinfo is None:
        check = check.replace(tzinfo=timezone.utc)
    if acquired.tzinfo is None:
        acquired = acquired.replace(tzinfo=timezone.utc)
    if check < acquired:
        return False
    expires = acquired + timedelta(seconds=int(ttl_sec))
    return check < expires


def run_verify(path: Path) -> tuple[dict, bool]:
    m = json.loads(path.read_text(encoding="utf-8"))
    out_scenarios = []
    ok = True
    for sc in m["scenarios"]:
        check_at = sc["check_at"]
        active_ids = []
        for L in sc["leases"]:
            if lease_active(L["acquired_at"], L["ttl_sec"], check_at):
                active_ids.append(L["id"])
        got = sorted(active_ids)
        exp = list(sc["expect_active_ids_sorted"])
        row_ok = got == exp
        ok = ok and row_ok
        out_scenarios.append(
            {
                "check_at": check_at,
                "got_active_ids_sorted": got,
                "expect_active_ids_sorted": exp,
                "match": row_ok,
            }
        )
    body = {
        "manifest_path": str(path.relative_to(_REPO)) if path.is_relative_to(_REPO) else str(path),
        "scenarios": out_scenarios,
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
        "horizon": 30,
        "schema": _SCHEMA,
        "mode": "lease_ttl_smoke",
        "ok": ok,
        **body,
        "note": "Production adds fencing tokens, renewed leases, and clock-skew budgets.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon30 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon30 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
