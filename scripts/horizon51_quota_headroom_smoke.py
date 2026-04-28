#!/usr/bin/env python3
"""Horizon 51: quota headroom — storage utilization ceiling.

Loads texts/horizon51_quota_headroom_sample.json; under_budget iff utilization_pct <= max_utilization_pct.
Writes horizon51_quota_headroom_run/1.0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "texts" / "horizon51_quota_headroom_sample.json"
_SCHEMA = "horizon51_quota_headroom_run/1.0"
_OUT = _REPO / ".tmp" / "horizon51-quota-headroom" / "run.json"


def run_verify(path: Path) -> tuple[dict, bool]:
    m = json.loads(path.read_text(encoding="utf-8"))
    ceiling = float(m["max_utilization_pct"])
    rows = []
    ok = True
    for ch in m["checks"]:
        util = float(ch["utilization_pct"])
        exp = bool(ch["expect_under_budget"])
        got = util <= ceiling
        row_ok = got == exp
        ok = ok and row_ok
        rows.append(
            {
                "utilization_pct": util,
                "under_budget": got,
                "expect_under_budget": exp,
                "match": row_ok,
            }
        )
    body = {
        "manifest_path": str(path.relative_to(_REPO)) if path.is_relative_to(_REPO) else str(path),
        "max_utilization_pct": ceiling,
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
        "horizon": 51,
        "schema": _SCHEMA,
        "mode": "quota_headroom_smoke",
        "ok": ok,
        **body,
        "note": "Production adds burst buffers, inode caps, cross-region replication headroom.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon51 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon51 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
