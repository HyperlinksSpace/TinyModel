#!/usr/bin/env python3
"""Horizon 21: data retention tiers — purge eligibility vs category TTL.

Loads texts/horizon21_retention_sample.json; compares age to retention_days at as_of.
Writes horizon21_retention_run/1.0."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "texts" / "horizon21_retention_sample.json"
_SCHEMA = "horizon21_retention_run/1.0"
_OUT = _REPO / ".tmp" / "horizon21-retention" / "run.json"


def eligible_for_purge(
    category: str,
    created_iso: str,
    tiers: dict[str, int],
    as_of: date,
) -> bool:
    """True when record age in whole days >= retention for category."""
    ret = tiers[category]
    created = date.fromisoformat(created_iso)
    age_days = (as_of - created).days
    return age_days >= ret


def run_verify(path: Path) -> tuple[dict, bool]:
    m = json.loads(path.read_text(encoding="utf-8"))
    as_of = date.fromisoformat(m["as_of"])
    tiers = {t["category"]: int(t["retention_days"]) for t in m["tiers"]}
    rows = []
    ok = True
    for rec in m["records"]:
        cat = rec["category"]
        got = eligible_for_purge(cat, rec["created"], tiers, as_of)
        exp = rec["expect_eligible"]
        row_ok = got == exp
        ok = ok and row_ok
        rows.append(
            {
                "id": rec["id"],
                "category": cat,
                "created": rec["created"],
                "expect_eligible": exp,
                "got_eligible": got,
                "match": row_ok,
            }
        )
    body = {
        "manifest_path": str(path.relative_to(_REPO)) if path.is_relative_to(_REPO) else str(path),
        "as_of": m["as_of"],
        "records_evaluated": rows,
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
        "horizon": 21,
        "schema": _SCHEMA,
        "mode": "retention_purge_eligibility_smoke",
        "ok": ok,
        **body,
        "note": "Legal holds and jurisdiction overrides belong in production policy layers.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon21 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon21 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
