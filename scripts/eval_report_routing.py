#!/usr/bin/env python3
"""Read the Phase 2 **`routing`** object from a classifier checkpoint's **`eval_report.json`**.

Used by Horizon 1 glue, **rag_faq_smoke**, **embeddings_smoke_test**, **routing_policy** (**`--from-checkpoint`**), **horizon1_route_then_retrieve**, and training/report CLIs so training notes and runtime gates stay aligned."""

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


def format_checkpoint_tip_path(
    output_dir: str | Path,
    *,
    cwd: Path | None = None,
) -> str:
    """Return a repo-relative checkpoint path when ``output_dir`` is under ``cwd``."""
    p = Path(output_dir).resolve()
    base = (cwd if cwd is not None else Path.cwd()).resolve()
    try:
        return p.relative_to(base).as_posix()
    except ValueError:
        return p.as_posix()


def format_routing_policy_from_checkpoint_command(
    output_dir: str | Path,
    *,
    cwd: Path | None = None,
) -> str:
    """Full ``python scripts/routing_policy.py --from-checkpoint …`` line (no shell quoting)."""
    tip = format_checkpoint_tip_path(output_dir, cwd=cwd)
    return f"python scripts/routing_policy.py --from-checkpoint {tip}"


def print_routing_policy_from_checkpoint_tip(
    output_dir: str | Path,
    *,
    headline: str = "Tip: dump Phase 2 `routing` JSON (no model load):",
    cwd: Path | None = None,
) -> None:
    """Print a copy-paste **Tip:** for ``routing_policy`` (shared by train/compare/verify scripts)."""
    cmd = format_routing_policy_from_checkpoint_command(output_dir, cwd=cwd)
    print(f"{headline}\n  {cmd}", flush=True)


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
