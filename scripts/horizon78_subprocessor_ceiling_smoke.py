#!/usr/bin/env python3
"""Horizon 78: active subprocessors ceiling — privacy/vendor roster discipline.

Loads texts/horizon78_subprocessor_ceiling_sample.json; compliant iff active ≤ max.
Writes horizon78_subprocessor_ceiling_run/1.0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "texts" / "horizon78_subprocessor_ceiling_sample.json"
_SCHEMA = "horizon78_subprocessor_ceiling_run/1.0"
_OUT = _REPO / ".tmp" / "horizon78-subprocessor-ceiling" / "run.json"


def run_verify(path: Path) -> tuple[dict, bool]:
    m = json.loads(path.read_text(encoding="utf-8"))
    mx = int(m["max_active_subprocessors"])
    rows = []
    ok = True
    for ch in m["checks"]:
        n = int(ch["active_subprocessors"])
        exp = bool(ch["expect_compliant"])
        got = n <= mx
        row_ok = got == exp
        ok = ok and row_ok
        rows.append(
            {
                "active_subprocessors": n,
                "compliant": got,
                "expect_compliant": exp,
                "match": row_ok,
            }
        )
    body = {
        "manifest_path": str(path.relative_to(_REPO)) if path.is_relative_to(_REPO) else str(path),
        "max_active_subprocessors": mx,
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
        "horizon": 78,
        "schema": _SCHEMA,
        "mode": "subprocessor_ceiling_smoke",
        "ok": ok,
        **body,
        "note": "Production adds DPIAs, SCC chains, and vendor tiering—not only counts.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon78 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon78 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
