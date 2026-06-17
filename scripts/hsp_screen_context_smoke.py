#!/usr/bin/env python3
"""Stdlib smoke for HSP screen-context explain_screen helpers.

Examples:
  python scripts/hsp_screen_context_smoke.py --verify
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_scripts = Path(__file__).resolve().parent
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))

from hsp_screen_context import (
    build_screen_retrieval_query,
    infer_plan_intent,
    is_explain_screen_query,
    screen_title_for_route,
)

_OUT = Path(__file__).resolve().parent.parent / ".tmp" / "hsp-screen-context-smoke" / "run.json"
_SCHEMA = "hsp_screen_context_smoke_run/1.0"
_PROG = "hsp_screen_context_smoke"

_QUERY_CASES: list[tuple[str, str, str | None]] = [
    ("/shield", "what is this", "Shield"),
    ("/swap", "explain this screen", "Swap tokens"),
    ("/feed", "help with this page", "Feed"),
    ("/get", "what does this do", "Send and Get wallet"),
    ("/unknown", "what is this", None),
    ("/shield", "open swap page", None),
]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verify", action="store_true")
    p.add_argument("--output-json", type=str, default="")
    return p


def run_verify() -> tuple[bool, dict]:
    rows: list[dict] = []
    for route, text, expect_title in _QUERY_CASES:
        title = screen_title_for_route(route)
        explain = is_explain_screen_query(text)
        query = build_screen_retrieval_query(text, route)
        ok = True
        detail = "ok"
        if expect_title is None:
            if query is not None:
                ok = False
                detail = f"unexpected query {query!r}"
        else:
            if query is None or expect_title.lower() not in query.lower():
                ok = False
                detail = f"query={query!r}"
        rows.append(
            {
                "route": route,
                "text": text,
                "screen_title": title,
                "explain_screen": explain,
                "query": query,
                "expect_title": expect_title,
                "ok": ok,
                "detail": detail,
            }
        )
        if not ok:
            raise ValueError(f"case {route!r}+{text!r}: {detail}")

    intent = infer_plan_intent(
        route_hint=None,
        screen_query="Shield what is this",
        routing_fallback=False,
        retrieval={"top_title": "Shield"},
    )
    if intent != "explain_screen":
        raise ValueError(f"expected explain_screen intent, got {intent!r}")

    return True, {"schema": _SCHEMA, "cases": rows, "ok": True}


def main() -> None:
    args = build_parser().parse_args()
    try:
        ok, artifact = run_verify()
    except ValueError as e:
        print(f"{_PROG}: FAIL {e}", file=sys.stderr)
        raise SystemExit(1) from e

    out = Path(args.output_json) if args.output_json else _OUT
    if args.verify or args.output_json:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {out}")

    print(f"{_PROG}: cases={len(artifact['cases'])} ok={ok}")
    if args.verify:
        print(f"{_PROG} verify: OK")


if __name__ == "__main__":
    main()
