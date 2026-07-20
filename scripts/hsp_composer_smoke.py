#!/usr/bin/env python3
"""Verify AI Composer routing (stdlib mirror of integrations/hsp/reference/composer.ts).

Examples:
  python scripts/hsp_composer_smoke.py --verify
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_scripts = Path(__file__).resolve().parent
_REPO = _scripts.parent
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))

from hsp_composer_lib import ComposerAvailability, compose_turn_plan

_GOLDEN = _REPO / "texts" / "golden-prompts" / "hsp_composer_routes.jsonl"
_COMPOSER_TS = _REPO / "integrations" / "hsp" / "reference" / "composer.ts"
_PROG = "hsp_composer_smoke"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verify", action="store_true")
    return p


def _load_rows() -> list[dict[str, Any]]:
    if not _GOLDEN.is_file():
        raise ValueError(f"missing {_GOLDEN}")
    rows: list[dict[str, Any]] = []
    for line in _GOLDEN.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _validate_ts_exports() -> None:
    if not _COMPOSER_TS.is_file():
        raise ValueError("missing integrations/hsp/reference/composer.ts")
    text = _COMPOSER_TS.read_text(encoding="utf-8")
    for name in (
        "composeTurn",
        "resolveIntent",
        "defaultComposerConfig",
        "detectTokenInfoIntent",
        "pickModelRoute",
    ):
        if f"export function {name}" not in text and f"export async function {name}" not in text:
            raise ValueError(f"composer.ts missing export {name}")


def run_verify() -> dict[str, Any]:
    _validate_ts_exports()
    rows = _load_rows()
    failed: list[str] = []
    for row in rows:
        avail = ComposerAvailability(
            tinymodel=True,
            vercel_ai=row.get("vercel_ai", True),
            ub=row.get("ub", False),
            swap_coffee=row.get("swap_coffee", True),
        )
        plan = None
        if row.get("context_route"):
            plan = {
                "intent": "explain_screen",
                "actions": [],
                "route_hint": None,
            }
        turn = compose_turn_plan(
            row["input"],
            mode=row.get("mode"),
            plan=plan,
            avail=avail,
        )
        if turn.intent != row["expect_intent"]:
            failed.append(f"{row['id']} intent got {turn.intent!r}")
            continue
        if turn.lane != row["expect_lane"]:
            failed.append(f"{row['id']} lane got {turn.lane!r}")
            continue
        if turn.generator != row["expect_generator"]:
            failed.append(f"{row['id']} generator got {turn.generator!r}")
            continue
        path = row.get("expect_actions_path")
        if path:
            nav = next((a for a in turn.actions if a.get("type") == "navigate"), None)
            if not nav or nav.get("path") != path:
                failed.append(f"{row['id']} actions missing navigate {path!r}")
    if failed:
        raise ValueError(f"composer golden failed: {failed}")
    return {"rows": len(rows), "ok": True}


def main() -> None:
    args = build_parser().parse_args()
    try:
        artifact = run_verify()
    except ValueError as e:
        print(f"{_PROG}: FAIL {e}", file=sys.stderr)
        raise SystemExit(1) from e
    print(f"{_PROG}: golden={artifact['rows']}/{artifact['rows']} ok=True")
    if args.verify:
        print(f"{_PROG} verify: OK")


if __name__ == "__main__":
    main()
