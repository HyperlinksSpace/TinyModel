#!/usr/bin/env python3
"""Stdlib smoke: HSP TypeScript reference client files are present and complete.

Examples:
  python scripts/hsp_reference_client_smoke.py --verify
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_REF = _REPO / "integrations" / "hsp" / "reference"
_PROG = "hsp_reference_client_smoke"

_REQUIRED = (
    "integrations/hsp/reference/README.md",
    "integrations/hsp/reference/tinymodel-types.ts",
    "integrations/hsp/reference/tinymodel-client.ts",
)

_EXPORTS = (
    "getServiceMeta",
    "planRequest",
    "classifyTexts",
    "retrieveCandidates",
    "buildMetaTinyModel",
    "tinymodelBaseUrl",
)

_TYPES = (
    "PlanResponse",
    "MetaTinyModel",
    "ServiceMeta",
    "PlanContext",
    "PlanIntent",
)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verify", action="store_true")
    return p


def run_verify() -> None:
    for rel in _REQUIRED:
        path = _REPO / rel
        if not path.is_file():
            raise ValueError(f"missing {rel}")
    client = (_REF / "tinymodel-client.ts").read_text(encoding="utf-8")
    types = (_REF / "tinymodel-types.ts").read_text(encoding="utf-8")
    for name in _EXPORTS:
        if f"export async function {name}" not in client and f"export function {name}" not in client:
            raise ValueError(f"tinymodel-client.ts missing export {name}")
    for name in _TYPES:
        if name not in types:
            raise ValueError(f"tinymodel-types.ts missing type {name}")


def main() -> None:
    args = build_parser().parse_args()
    try:
        run_verify()
    except ValueError as e:
        print(f"{_PROG}: FAIL {e}", file=sys.stderr)
        raise SystemExit(1) from e
    print(f"{_PROG}: files={len(_REQUIRED)} exports={len(_EXPORTS)} ok=True")
    if args.verify:
        print(f"{_PROG} verify: OK")


if __name__ == "__main__":
    main()
