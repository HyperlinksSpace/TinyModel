#!/usr/bin/env python3
"""Horizon 77: legal-hold mutation gate — litigation preservation fence.

Loads texts/horizon77_legal_hold_sample.json; allow_mutate iff not legal_hold or counsel_override.
Writes horizon77_legal_hold_run/1.0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "texts" / "horizon77_legal_hold_sample.json"
_SCHEMA = "horizon77_legal_hold_run/1.0"
_OUT = _REPO / ".tmp" / "horizon77-legal-hold" / "run.json"


def run_verify(path: Path) -> tuple[dict, bool]:
    m = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    ok = True
    for ch in m["checks"]:
        hold = bool(ch["legal_hold_active"])
        ov = bool(ch["counsel_override"])
        exp = bool(ch["expect_allow_mutate"])
        got = (not hold) or ov
        row_ok = got == exp
        ok = ok and row_ok
        rows.append(
            {
                "legal_hold_active": hold,
                "counsel_override": ov,
                "allow_mutate": got,
                "expect_allow_mutate": exp,
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
        "horizon": 77,
        "schema": _SCHEMA,
        "mode": "legal_hold_smoke",
        "ok": ok,
        **body,
        "note": "Production adds custodian workflows, chain-of-custody logs, and e-discovery bridges.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon77 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon77 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
