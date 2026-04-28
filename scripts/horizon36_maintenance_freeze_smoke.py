#!/usr/bin/env python3
"""Horizon 36: maintenance freeze windows — block changes inside declared UTC intervals.

Loads texts/horizon36_maintenance_freeze_sample.json; frozen iff start <= at < end for some interval.
Writes horizon36_maintenance_freeze_run/1.0."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "texts" / "horizon36_maintenance_freeze_sample.json"
_SCHEMA = "horizon36_maintenance_freeze_run/1.0"
_OUT = _REPO / ".tmp" / "horizon36-maintenance-freeze" / "run.json"


def parse_iso(s: str) -> datetime:
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def is_frozen(at_iso: str, intervals: list[dict[str, str]]) -> bool:
    at = parse_iso(at_iso)
    for iv in intervals:
        start = parse_iso(iv["start"])
        end = parse_iso(iv["end"])
        if start <= at < end:
            return True
    return False


def run_verify(path: Path) -> tuple[dict, bool]:
    m = json.loads(path.read_text(encoding="utf-8"))
    intervals = m["freeze_intervals"]
    rows = []
    ok = True
    for ch in m["checks"]:
        exp = bool(ch["expect_frozen"])
        got = is_frozen(ch["at"], intervals)
        row_ok = got == exp
        ok = ok and row_ok
        rows.append(
            {
                "at": ch["at"],
                "frozen": got,
                "expect_frozen": exp,
                "match": row_ok,
            }
        )
    body = {
        "manifest_path": str(path.relative_to(_REPO)) if path.is_relative_to(_REPO) else str(path),
        "freeze_interval_count": len(intervals),
        "checks": rows,
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
        "horizon": 36,
        "schema": _SCHEMA,
        "mode": "maintenance_freeze_smoke",
        "ok": ok,
        **body,
        "note": "Integrate with deploy pipelines, calendars, and emergency break-glass overrides.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon36 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon36 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
