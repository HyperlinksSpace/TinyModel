#!/usr/bin/env python3
"""Read the Phase 2 **`routing`** object from a classifier checkpoint's **`eval_report.json`**.

Used by Horizon 1 glue and smoke scripts so training notes and runtime gates stay aligned."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def load_routing_from_eval_report(model_path: str | Path) -> dict | None:
    """Return the top-level ``routing`` dict if ``model_path`` is a dir with a valid report."""
    p = Path(model_path)
    if not p.is_dir():
        return None
    er = p / "eval_report.json"
    if not er.is_file():
        return None
    try:
        data = json.loads(er.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    r = data.get("routing")
    return r if isinstance(r, dict) else None


def maybe_print_routing_section(model_path: str, *, enabled: bool, prog: str) -> None:
    """If ``enabled``, print ``routing`` JSON or a stderr hint (``prog`` labels the caller)."""
    if not enabled:
        return
    notes = load_routing_from_eval_report(model_path)
    if notes is None:
        print(
            f"{prog}: no eval_report.json with top-level `routing` "
            "(Hub id or missing artifact).",
            file=sys.stderr,
        )
        return
    print("=== eval_report.json routing (Phase 2 training notes) ===\n")
    print(json.dumps(notes, indent=2))
    print()
