#!/usr/bin/env python3
"""Horizon 47: kill switch — global deny overrides policy allow.

Loads texts/horizon47_kill_switch_sample.json; allowed iff not engaged and policy_allow.
Writes horizon47_kill_switch_run/1.0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "texts" / "horizon47_kill_switch_sample.json"
_SCHEMA = "horizon47_kill_switch_run/1.0"
_OUT = _REPO / ".tmp" / "horizon47-kill-switch" / "run.json"


def run_verify(path: Path) -> tuple[dict, bool]:
    m = json.loads(path.read_text(encoding="utf-8"))
    scenarios_out = []
    ok = True
    for si, scen in enumerate(m["scenarios"]):
        engaged = bool(scen["kill_switch_engaged"])
        rows = []
        for ci, ch in enumerate(scen["checks"]):
            policy = bool(ch["policy_allow"])
            exp = bool(ch["expect_allowed"])
            got = (not engaged) and policy
            row_ok = got == exp
            ok = ok and row_ok
            rows.append(
                {
                    "check_index": ci,
                    "policy_allow": policy,
                    "allowed": got,
                    "expect_allowed": exp,
                    "match": row_ok,
                }
            )
        scenarios_out.append(
            {
                "scenario_index": si,
                "kill_switch_engaged": engaged,
                "checks": rows,
            }
        )
    body = {
        "manifest_path": str(path.relative_to(_REPO)) if path.is_relative_to(_REPO) else str(path),
        "scenarios": scenarios_out,
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
        "horizon": 47,
        "schema": _SCHEMA,
        "mode": "kill_switch_smoke",
        "ok": ok,
        **body,
        "note": "Production adds scoped incidents, regional drains, and audited flip workflows.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon47 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon47 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
