#!/usr/bin/env python3
"""Stdlib smoke: HSP transmitter reference modules (fallback, availability, context).

Validates TypeScript reference files and Python/TS parity on hsp_intents golden rows.

Examples:
  python scripts/hsp_reference_transmitter_smoke.py --verify
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_scripts = Path(__file__).resolve().parent
_REPO = _scripts.parent
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))

from hsp_intent_router import score_hsp_intent_row

_REF = _REPO / "integrations" / "hsp" / "reference"
_GOLDEN = _REPO / "texts" / "golden-prompts" / "hsp_intents.jsonl"
_PROG = "hsp_reference_transmitter_smoke"

_REQUIRED = (
    "integrations/hsp/reference/fallback-router.ts",
    "integrations/hsp/reference/availability.ts",
    "integrations/hsp/reference/build-context.ts",
)

_FALLBACK_EXPORTS = (
    "inferHspRouteHint",
    "actionsFromRouteHint",
    "resolveFallbackIntent",
    "fallbackPlanFromText",
)

_AVAILABILITY_EXPORTS = (
    "probeTinyModelHealth",
    "TinyModelHealthCache",
)

_CONTEXT_EXPORTS = (
    "buildGeneratorContext",
    "toPlanContext",
)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verify", action="store_true")
    return p


def _load_intent_rows() -> list[dict]:
    if not _GOLDEN.is_file():
        raise ValueError(f"missing golden file {_GOLDEN}")
    rows: list[dict] = []
    for line in _GOLDEN.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def run_verify() -> dict:
    for rel in _REQUIRED:
        if not (_REPO / rel).is_file():
            raise ValueError(f"missing {rel}")

    fallback = (_REF / "fallback-router.ts").read_text(encoding="utf-8")
    availability = (_REF / "availability.ts").read_text(encoding="utf-8")
    context = (_REF / "build-context.ts").read_text(encoding="utf-8")

    for name in _FALLBACK_EXPORTS:
        if f"export function {name}" not in fallback:
            raise ValueError(f"fallback-router.ts missing export {name}")
    for name in _AVAILABILITY_EXPORTS:
        if name == "TinyModelHealthCache":
            if f"export class {name}" not in availability:
                raise ValueError("availability.ts missing TinyModelHealthCache")
        elif f"export async function {name}" not in availability and f"export function {name}" not in availability:
            raise ValueError(f"availability.ts missing export {name}")
    for name in _CONTEXT_EXPORTS:
        if f"export function {name}" not in context:
            raise ValueError(f"build-context.ts missing export {name}")

    rows = _load_intent_rows()
    failed: list[str] = []
    for row in rows:
        ok, detail, _ = score_hsp_intent_row(row)
        if not ok:
            failed.append(f"{row.get('id', '?')}: {detail}")
    if failed:
        raise ValueError(f"hsp_intents parity failed: {failed[:5]}")

    return {
        "files": len(_REQUIRED),
        "golden_rows": len(rows),
        "golden_ok": len(rows) - len(failed),
        "ok": True,
    }


def main() -> None:
    args = build_parser().parse_args()
    try:
        artifact = run_verify()
    except ValueError as e:
        print(f"{_PROG}: FAIL {e}", file=sys.stderr)
        raise SystemExit(1) from e
    print(
        f"{_PROG}: files={artifact['files']} golden={artifact['golden_ok']}/{artifact['golden_rows']} ok=True"
    )
    if args.verify:
        print(f"{_PROG} verify: OK")


if __name__ == "__main__":
    main()
