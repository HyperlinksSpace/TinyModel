#!/usr/bin/env python3
"""Horizon 69: vendor API host allow-list — subprocessor egress gate.

Loads texts/horizon69_vendor_host_sample.json; allow iff requested_host ∈ allowed_api_hosts (normalized).
Writes horizon69_vendor_host_run/1.0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "texts" / "horizon69_vendor_host_sample.json"
_SCHEMA = "horizon69_vendor_host_run/1.0"
_OUT = _REPO / ".tmp" / "horizon69-vendor-host" / "run.json"


def _norm(s: str) -> str:
    return str(s).lower().strip().rstrip(".")


def run_verify(path: Path) -> tuple[dict, bool]:
    m = json.loads(path.read_text(encoding="utf-8"))
    allowed = {_norm(x) for x in m["allowed_api_hosts"]}
    rows = []
    ok = True
    for ch in m["checks"]:
        host = _norm(ch["requested_host"])
        exp = bool(ch["expect_allow"])
        got = host in allowed
        row_ok = got == exp
        ok = ok and row_ok
        rows.append(
            {
                "requested_host": host,
                "allow": got,
                "expect_allow": exp,
                "match": row_ok,
            }
        )
    body = {
        "manifest_path": str(path.relative_to(_REPO)) if path.is_relative_to(_REPO) else str(path),
        "allowed_count": len(allowed),
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
        "horizon": 69,
        "schema": _SCHEMA,
        "mode": "vendor_host_smoke",
        "ok": ok,
        **body,
        "note": "Production adds wildcard suffix policies, mTLS pinning, and DPI egress proofs.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon69 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon69 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
