#!/usr/bin/env python3
"""Horizon 57: severity routing — pager required for critical severities.

Loads texts/horizon57_sev_pager_sample.json; compliant iff not requiring page or pager_sent.
Writes horizon57_sev_pager_run/1.0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "texts" / "horizon57_sev_pager_sample.json"
_SCHEMA = "horizon57_sev_pager_run/1.0"
_OUT = _REPO / ".tmp" / "horizon57-sev-pager" / "run.json"


def run_verify(path: Path) -> tuple[dict, bool]:
    m = json.loads(path.read_text(encoding="utf-8"))
    page_levels = {str(x).lower().strip() for x in m["severities_requiring_page"]}
    rows = []
    ok = True
    for ch in m["checks"]:
        sev = str(ch["severity"]).lower().strip()
        pager = bool(ch["pager_sent"])
        exp = bool(ch["expect_compliant"])
        needs = sev in page_levels
        got = (not needs) or pager
        row_ok = got == exp
        ok = ok and row_ok
        rows.append(
            {
                "severity": sev,
                "requires_page": needs,
                "pager_sent": pager,
                "compliant": got,
                "expect_compliant": exp,
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
        "horizon": 57,
        "schema": _SCHEMA,
        "mode": "sev_pager_smoke",
        "ok": ok,
        **body,
        "note": "Production adds escalation ladders, rotations, and customer comms bridges.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon57 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon57 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
