#!/usr/bin/env python3
"""Horizon 41: geo-fence / data residency — region allow-list.

Loads texts/horizon41_geo_fence_sample.json; allowed iff region in allowed_regions.
Writes horizon41_geo_fence_run/1.0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "texts" / "horizon41_geo_fence_sample.json"
_SCHEMA = "horizon41_geo_fence_run/1.0"
_OUT = _REPO / ".tmp" / "horizon41-geo-fence" / "run.json"


def run_verify(path: Path) -> tuple[dict, bool]:
    m = json.loads(path.read_text(encoding="utf-8"))
    allowed = set(m["allowed_regions"])
    rows = []
    ok = True
    for ch in m["checks"]:
        reg = ch["region"]
        exp = bool(ch["expect_allowed"])
        got = reg in allowed
        row_ok = got == exp
        ok = ok and row_ok
        rows.append(
            {
                "region": reg,
                "allowed": got,
                "expect_allowed": exp,
                "match": row_ok,
            }
        )
    body = {
        "manifest_path": str(path.relative_to(_REPO)) if path.is_relative_to(_REPO) else str(path),
        "allowed_region_count": len(allowed),
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
        "horizon": 41,
        "schema": _SCHEMA,
        "mode": "geo_fence_smoke",
        "ok": ok,
        **body,
        "note": "Production adds private links, sovereignty, audits, and transfer impact assessments.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon41 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon41 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
