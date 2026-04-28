#!/usr/bin/env python3
"""Horizon 62: protected-branch merge gate — approvals + CI on protected refs.

Loads texts/horizon62_branch_protect_sample.json; allow_merge iff branch not protected or (approvals and CI green).
Writes horizon62_branch_protect_run/1.0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "texts" / "horizon62_branch_protect_sample.json"
_SCHEMA = "horizon62_branch_protect_run/1.0"
_OUT = _REPO / ".tmp" / "horizon62-branch-protect" / "run.json"


def run_verify(path: Path) -> tuple[dict, bool]:
    m = json.loads(path.read_text(encoding="utf-8"))
    prot = {str(x).lower().strip() for x in m["protected_branches"]}
    rows = []
    ok = True
    for ch in m["checks"]:
        br = str(ch["branch"]).lower().strip()
        appr = bool(ch["min_approvals_met"])
        green = bool(ch["ci_green"])
        exp = bool(ch["expect_allow_merge"])
        needs = br in prot
        got = (not needs) or (appr and green)
        row_ok = got == exp
        ok = ok and row_ok
        rows.append(
            {
                "branch": br,
                "protected_ref": needs,
                "min_approvals_met": appr,
                "ci_green": green,
                "allow_merge": got,
                "expect_allow_merge": exp,
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
        "horizon": 62,
        "schema": _SCHEMA,
        "mode": "branch_protect_smoke",
        "ok": ok,
        **body,
        "note": "Production adds CODEOWNERS, required checks lists, and merge-queue semantics.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon62 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon62 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
