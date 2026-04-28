#!/usr/bin/env python3
"""Horizon 70: major-incident backlog ceiling — ops hygiene gate.

Loads texts/horizon70_incident_backlog_sample.json; compliant iff open_major_incidents ≤ max.
Writes horizon70_incident_backlog_run/1.0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "texts" / "horizon70_incident_backlog_sample.json"
_SCHEMA = "horizon70_incident_backlog_run/1.0"
_OUT = _REPO / ".tmp" / "horizon70-incident-backlog" / "run.json"


def run_verify(path: Path) -> tuple[dict, bool]:
    m = json.loads(path.read_text(encoding="utf-8"))
    mx = int(m["max_open_major_incidents"])
    rows = []
    ok = True
    for ch in m["checks"]:
        n = int(ch["open_major_incidents"])
        exp = bool(ch["expect_compliant"])
        got = n <= mx
        row_ok = got == exp
        ok = ok and row_ok
        rows.append(
            {
                "open_major_incidents": n,
                "compliant": got,
                "expect_compliant": exp,
                "match": row_ok,
            }
        )
    body = {
        "manifest_path": str(path.relative_to(_REPO)) if path.is_relative_to(_REPO) else str(path),
        "max_open_major_incidents": mx,
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
        "horizon": 70,
        "schema": _SCHEMA,
        "mode": "incident_backlog_smoke",
        "ok": ok,
        **body,
        "note": "Production adds severity rubrics, executive dashboards, and burn-down drills.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon70 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon70 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
