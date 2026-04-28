#!/usr/bin/env python3
"""Horizon 63: secret-scan sweep ceiling — zero-high-water policy gate.

Loads texts/horizon63_secret_sweep_sample.json; compliant iff open_secret_findings ≤ max.
Writes horizon63_secret_sweep_run/1.0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "texts" / "horizon63_secret_sweep_sample.json"
_SCHEMA = "horizon63_secret_sweep_run/1.0"
_OUT = _REPO / ".tmp" / "horizon63-secret-sweep" / "run.json"


def run_verify(path: Path) -> tuple[dict, bool]:
    m = json.loads(path.read_text(encoding="utf-8"))
    mx = int(m["max_open_secret_findings"])
    rows = []
    ok = True
    for ch in m["checks"]:
        n = int(ch["open_secret_findings"])
        exp = bool(ch["expect_compliant"])
        got = n <= mx
        row_ok = got == exp
        ok = ok and row_ok
        rows.append(
            {
                "open_secret_findings": n,
                "compliant": got,
                "expect_compliant": exp,
                "match": row_ok,
            }
        )
    body = {
        "manifest_path": str(path.relative_to(_REPO)) if path.is_relative_to(_REPO) else str(path),
        "max_open_secret_findings": mx,
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
        "horizon": 63,
        "schema": _SCHEMA,
        "mode": "secret_sweep_smoke",
        "ok": ok,
        **body,
        "note": "Production adds entropy detectors, KMS hints, and exempt workflows with expiry.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon63 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon63 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
