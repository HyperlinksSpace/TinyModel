#!/usr/bin/env python3
"""Horizon 43: credential / session freshness — max age ceiling.

Loads texts/horizon43_credential_age_sample.json; valid iff age_seconds <= max_age_seconds.
Writes horizon43_credential_age_run/1.0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "texts" / "horizon43_credential_age_sample.json"
_SCHEMA = "horizon43_credential_age_run/1.0"
_OUT = _REPO / ".tmp" / "horizon43-credential-age" / "run.json"


def run_verify(path: Path) -> tuple[dict, bool]:
    m = json.loads(path.read_text(encoding="utf-8"))
    max_age = int(m["max_age_seconds"])
    rows = []
    ok = True
    for ch in m["checks"]:
        age = int(ch["age_seconds"])
        exp = bool(ch["expect_valid"])
        got = age <= max_age
        row_ok = got == exp
        ok = ok and row_ok
        rows.append(
            {
                "age_seconds": age,
                "valid": got,
                "expect_valid": exp,
                "match": row_ok,
            }
        )
    body = {
        "manifest_path": str(path.relative_to(_REPO)) if path.is_relative_to(_REPO) else str(path),
        "max_age_seconds": max_age,
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
        "horizon": 43,
        "schema": _SCHEMA,
        "mode": "credential_age_smoke",
        "ok": ok,
        **body,
        "note": "Production adds skew-safe timestamps, rotation webhooks, and revocations.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon43 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon43 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
