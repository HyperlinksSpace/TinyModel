#!/usr/bin/env python3
"""Horizon 45: payload size ceiling — max bytes ingress gate.

Loads texts/horizon45_payload_size_sample.json; allowed iff bytes <= max_bytes.
Writes horizon45_payload_size_run/1.0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "texts" / "horizon45_payload_size_sample.json"
_SCHEMA = "horizon45_payload_size_run/1.0"
_OUT = _REPO / ".tmp" / "horizon45-payload-size" / "run.json"


def run_verify(path: Path) -> tuple[dict, bool]:
    m = json.loads(path.read_text(encoding="utf-8"))
    max_b = int(m["max_bytes"])
    rows = []
    ok = True
    for ch in m["checks"]:
        nbytes = int(ch["bytes"])
        exp = bool(ch["expect_allowed"])
        got = nbytes <= max_b
        row_ok = got == exp
        ok = ok and row_ok
        rows.append(
            {
                "bytes": nbytes,
                "allowed": got,
                "expect_allowed": exp,
                "match": row_ok,
            }
        )
    body = {
        "manifest_path": str(path.relative_to(_REPO)) if path.is_relative_to(_REPO) else str(path),
        "max_bytes": max_b,
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
        "horizon": 45,
        "schema": _SCHEMA,
        "mode": "payload_size_smoke",
        "ok": ok,
        **body,
        "note": "Production adds streaming limits, chunked uploads, and per-tenant quotas.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon45 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon45 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
