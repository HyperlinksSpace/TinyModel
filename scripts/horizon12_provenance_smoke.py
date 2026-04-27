#!/usr/bin/env python3
"""Horizon 12: provenance manifest — SHA-256 fingerprints of pinned repo texts.

Writes horizon12_provenance_run/1.0 for supply-chain / reproducibility-shaped checks.
Not cryptographic signing — hashes only."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_SCHEMA = "horizon12_provenance_run/1.0"
_OUT = _REPO / ".tmp" / "horizon12-provenance" / "run.json"

# Small, stable committed files (adjust if renamed).
_PINNED_REL = (
    "texts/horizon9_policy_sample.json",
    "texts/horizon10_budget_sample.json",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def run_verify() -> tuple[dict, bool]:
    entries = []
    ok = True
    for rel in _PINNED_REL:
        p = _REPO / rel
        if not p.is_file():
            ok = False
            entries.append({"path": rel, "error": "missing_file"})
            continue
        digest = sha256_file(p)
        entries.append({"path": rel, "sha256": digest, "bytes": p.stat().st_size})
    return (
        {
            "pinned_files": entries,
            "algorithm": "sha256",
        },
        ok,
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verify", action="store_true")
    p.add_argument("--output-json", type=str, default=str(_OUT))
    return p.parse_args()


def main() -> int:
    a = parse_args()
    if not a.verify:
        print("Use --verify.", file=sys.stderr)
        return 2
    body, ok = run_verify()
    out = Path(a.output_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "horizon": 12,
        "schema": _SCHEMA,
        "mode": "provenance_manifest",
        "ok": ok,
        **body,
        "note": "Extend with sigstore/cosign or in-toto in product; this is hash capture only.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon12 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon12 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
