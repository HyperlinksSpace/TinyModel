#!/usr/bin/env python3
"""Horizon 33: purpose limitation matrix — legal basis vs processing purpose allow-list.

Loads texts/horizon33_purpose_matrix_sample.json; checks belong to allowed_pairs set.
Writes horizon33_purpose_matrix_run/1.0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "texts" / "horizon33_purpose_matrix_sample.json"
_SCHEMA = "horizon33_purpose_matrix_run/1.0"
_OUT = _REPO / ".tmp" / "horizon33-purpose-matrix" / "run.json"


def load_allowed(m: dict) -> set[tuple[str, str]]:
    out: set[tuple[str, str]] = set()
    for pair in m["allowed_pairs"]:
        out.add((pair[0], pair[1]))
    return out


def run_verify(path: Path) -> tuple[dict, bool]:
    m = json.loads(path.read_text(encoding="utf-8"))
    allowed = load_allowed(m)
    rows = []
    ok = True
    for ch in m["checks"]:
        lb = ch["legal_basis"]
        pp = ch["processing_purpose"]
        exp = bool(ch["expect_allowed"])
        got = (lb, pp) in allowed
        row_ok = got == exp
        ok = ok and row_ok
        rows.append(
            {
                "legal_basis": lb,
                "processing_purpose": pp,
                "allowed": got,
                "expect_allowed": exp,
                "match": row_ok,
            }
        )
    body = {
        "manifest_path": str(path.relative_to(_REPO)) if path.is_relative_to(_REPO) else str(path),
        "allowed_pair_count": len(allowed),
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
        "horizon": 33,
        "schema": _SCHEMA,
        "mode": "purpose_matrix_smoke",
        "ok": ok,
        **body,
        "note": "Legal review defines production matrices; DPIAs and jurisdictions extend beyond this toy.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon33 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon33 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
