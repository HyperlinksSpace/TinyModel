#!/usr/bin/env python3
"""Stdlib smoke: Vercel AI transmitter reference modules present and complete.

Examples:
  python scripts/hsp_vercel_ai_transmitter_smoke.py --verify
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_REF = _REPO / "integrations" / "hsp" / "reference"
_PROG = "hsp_vercel_ai_transmitter_smoke"

_REQUIRED = (
    "integrations/hsp/reference/vercel-ai-client.ts",
    "integrations/hsp/reference/transmitter.ts",
)

_VERCEL_EXPORTS = (
    "resolveAiProvider",
    "isVercelAiConfigured",
    "buildVercelAiParams",
    "generateWithVercelAi",
)

_TRANSMITTER_EXPORTS = (
    "transmit",
    "transmitStream",
    "resolveComposerAvailability",
)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verify", action="store_true")
    return p


def run_verify() -> None:
    for rel in _REQUIRED:
        if not (_REPO / rel).is_file():
            raise ValueError(f"missing {rel}")

    vercel = (_REF / "vercel-ai-client.ts").read_text(encoding="utf-8")
    transmitter = (_REF / "transmitter.ts").read_text(encoding="utf-8")

    for name in _VERCEL_EXPORTS:
        if f"export function {name}" not in vercel and f"export async function {name}" not in vercel:
            raise ValueError(f"vercel-ai-client.ts missing export {name}")

    for name in _TRANSMITTER_EXPORTS:
        if f"export async function {name}" in transmitter or f"export function {name}" in transmitter:
            continue
        if name == "transmitStream" and "export async function* transmitStream" in transmitter:
            continue
        raise ValueError(f"transmitter.ts missing export {name}")

    if "legacyOpenAiTransmit" not in transmitter:
        raise ValueError("transmitter.ts must support legacyOpenAiTransmit migration path")
    if "streamText" not in transmitter or "generateText" not in transmitter:
        raise ValueError("transmitter.ts must reference Vercel AI SDK deps")
    if 'AI_PROVIDER=openai' not in transmitter and "openai" not in vercel:
        raise ValueError("vercel-ai-client must document legacy openai provider")


def main() -> None:
    args = build_parser().parse_args()
    try:
        run_verify()
    except ValueError as e:
        print(f"{_PROG}: FAIL {e}", file=sys.stderr)
        raise SystemExit(1) from e
    print(f"{_PROG}: files={len(_REQUIRED)} ok=True")
    if args.verify:
        print(f"{_PROG} verify: OK")


if __name__ == "__main__":
    main()
