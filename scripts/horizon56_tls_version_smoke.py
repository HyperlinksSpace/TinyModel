#!/usr/bin/env python3
"""Horizon 56: TLS version allow-list — ingress handshake gate.

Loads texts/horizon56_tls_version_sample.json; allow iff offered_tls_version is in allowed_tls_versions (case-insensitive).
Writes horizon56_tls_version_run/1.0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "texts" / "horizon56_tls_version_sample.json"
_SCHEMA = "horizon56_tls_version_run/1.0"
_OUT = _REPO / ".tmp" / "horizon56-tls-version" / "run.json"


def run_verify(path: Path) -> tuple[dict, bool]:
    m = json.loads(path.read_text(encoding="utf-8"))
    allowed = {str(x).lower().strip() for x in m["allowed_tls_versions"]}
    rows = []
    ok = True
    for ch in m["checks"]:
        off = str(ch["offered_tls_version"]).lower().strip()
        exp = bool(ch["expect_allow"])
        got = off in allowed
        row_ok = got == exp
        ok = ok and row_ok
        rows.append(
            {
                "offered_tls_version": off,
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
        "horizon": 56,
        "schema": _SCHEMA,
        "mode": "tls_version_smoke",
        "ok": ok,
        **body,
        "note": "Production adds cipher suites, HSTS, and cert transparency monitoring.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon56 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon56 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
