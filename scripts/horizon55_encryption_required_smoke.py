#!/usr/bin/env python3
"""Horizon 55: encryption required for sensitive tier.

Loads texts/horizon55_encryption_required_sample.json; allow iff not sensitive_tier or encryption_at_rest_enabled.
Writes horizon55_encryption_required_run/1.0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "texts" / "horizon55_encryption_required_sample.json"
_SCHEMA = "horizon55_encryption_required_run/1.0"
_OUT = _REPO / ".tmp" / "horizon55-encryption-required" / "run.json"


def run_verify(path: Path) -> tuple[dict, bool]:
    m = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    ok = True
    for ch in m["checks"]:
        sens = bool(ch["sensitive_tier"])
        enc = bool(ch["encryption_at_rest_enabled"])
        exp = bool(ch["expect_allow"])
        got = (not sens) or enc
        row_ok = got == exp
        ok = ok and row_ok
        rows.append(
            {
                "sensitive_tier": sens,
                "encryption_at_rest_enabled": enc,
                "allow": got,
                "expect_allow": exp,
                "match": row_ok,
            }
        )
    body = {
        "manifest_path": str(path.relative_to(_REPO)) if path.is_relative_to(_REPO) else str(path),
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
        "horizon": 55,
        "schema": _SCHEMA,
        "mode": "encryption_required_smoke",
        "ok": ok,
        **body,
        "note": "Production adds KMS boundaries, CMKs, and BYOK attestations.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon55 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon55 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
