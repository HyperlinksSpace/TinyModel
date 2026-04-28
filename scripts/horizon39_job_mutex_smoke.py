#!/usr/bin/env python3
"""Horizon 39: mutually exclusive jobs — mutex pairs cannot co-schedule.

Loads texts/horizon39_job_mutex_sample.json; conflict if both ends appear in schedule.
Writes horizon39_job_mutex_run/1.0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "texts" / "horizon39_job_mutex_sample.json"
_SCHEMA = "horizon39_job_mutex_run/1.0"
_OUT = _REPO / ".tmp" / "horizon39-job-mutex" / "run.json"


def has_conflict(scheduled_jobs: list[str], mutex_pairs: list[list[str]]) -> bool:
    S = set(scheduled_jobs)
    for pair in mutex_pairs:
        a, b = pair[0], pair[1]
        if a in S and b in S:
            return True
    return False


def run_verify(path: Path) -> tuple[dict, bool]:
    m = json.loads(path.read_text(encoding="utf-8"))
    mutex = m["mutex_pairs"]
    rows = []
    ok = True
    for sc in m["scenarios"]:
        jobs = list(sc["scheduled_jobs"])
        exp = bool(sc["expect_conflict"])
        got = has_conflict(jobs, mutex)
        row_ok = got == exp
        ok = ok and row_ok
        rows.append(
            {
                "scheduled_jobs": jobs,
                "conflict": got,
                "expect_conflict": exp,
                "match": row_ok,
            }
        )
    body = {
        "manifest_path": str(path.relative_to(_REPO)) if path.is_relative_to(_REPO) else str(path),
        "mutex_pair_count": len(mutex),
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
        "horizon": 39,
        "schema": _SCHEMA,
        "mode": "job_mutex_smoke",
        "ok": ok,
        **body,
        "note": "Production adds resources slots, calendars, and solver-backed schedules.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon39 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon39 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
