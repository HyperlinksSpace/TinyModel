#!/usr/bin/env python3
"""Horizon 35: crypto suite policy — algorithm allow-list plus minimum key length.

Loads texts/horizon35_crypto_suite_sample.json; claim allowed iff suite matches bits floor.
Writes horizon35_crypto_suite_run/1.0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "texts" / "horizon35_crypto_suite_sample.json"
_SCHEMA = "horizon35_crypto_suite_run/1.0"
_OUT = _REPO / ".tmp" / "horizon35-crypto-suite" / "run.json"


def claim_allowed(
    algorithm: str,
    key_bits: int,
    allowed_suites: list[dict[str, str | int]],
) -> bool:
    kb = int(key_bits)
    for su in allowed_suites:
        if su["algorithm"] == algorithm and kb >= int(su["key_bits_min"]):
            return True
    return False


def run_verify(path: Path) -> tuple[dict, bool]:
    m = json.loads(path.read_text(encoding="utf-8"))
    suites = m["allowed_suites"]
    rows = []
    ok = True
    for cl in m["claims"]:
        algo = cl["algorithm"]
        kb = int(cl["key_bits"])
        exp = bool(cl["expect_allowed"])
        got = claim_allowed(algo, kb, suites)
        row_ok = got == exp
        ok = ok and row_ok
        rows.append(
            {
                "algorithm": algo,
                "key_bits": kb,
                "allowed": got,
                "expect_allowed": exp,
                "match": row_ok,
            }
        )
    body = {
        "manifest_path": str(path.relative_to(_REPO)) if path.is_relative_to(_REPO) else str(path),
        "claims": rows,
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
        "horizon": 35,
        "schema": _SCHEMA,
        "mode": "crypto_suite_policy_smoke",
        "ok": ok,
        **body,
        "note": "Extend with AEAD negotiation, post-quantum profiles, and HSM attestations.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon35 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon35 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
