#!/usr/bin/env python3
"""Confidence-aware routing policy for classifier probability dicts.

Use with `TinyModelRuntime.classify(...)` output: each item is `dict[label, prob]`.
This module does **not** call the model; it only applies thresholds for triage / fallback.

Tune `min_confidence` and `min_margin` on your validation set (see
`texts/phase2-routing-threshold-scenario.md`).
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RoutingDecision:
    """Result of applying routing thresholds to one probability vector."""

    label: str | None
    """Chosen class label, or None if routed to fallback."""

    confidence: float
    """Probability of the top class."""

    second_probability: float
    """Probability of the runner-up class."""

    margin: float
    """Top minus second probability."""

    fallback: bool
    """True if abstaining (human queue, retrieval, etc.)."""

    reason: str
    """Short machine-readable reason code."""


def route_from_probs(
    probs: dict[str, float],
    *,
    min_confidence: float,
    min_margin: float,
) -> RoutingDecision:
    """Apply min-confidence and min-margin gates.

    - If top probability < `min_confidence` → fallback.
    - Else if (top - second) < `min_margin` → fallback (ambiguous between top two).
    - Else → accept top label.
    """
    if not probs:
        return RoutingDecision(
            label=None,
            confidence=0.0,
            second_probability=0.0,
            margin=0.0,
            fallback=True,
            reason="empty_probs",
        )
    sorted_items = sorted(probs.items(), key=lambda x: -x[1])
    top_label, top_p = sorted_items[0]
    second_p = sorted_items[1][1] if len(sorted_items) > 1 else 0.0
    margin = top_p - second_p

    if top_p < min_confidence:
        return RoutingDecision(
            label=None,
            confidence=top_p,
            second_probability=second_p,
            margin=margin,
            fallback=True,
            reason="below_min_confidence",
        )
    if margin < min_margin:
        return RoutingDecision(
            label=None,
            confidence=top_p,
            second_probability=second_p,
            margin=margin,
            fallback=True,
            reason="below_min_margin",
        )
    return RoutingDecision(
        label=top_label,
        confidence=top_p,
        second_probability=second_p,
        margin=margin,
        fallback=False,
        reason="accept",
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--demo",
        action="store_true",
        help="Print a small worked example (no model call).",
    )
    p.add_argument(
        "--probs-json",
        type=str,
        default=None,
        help='JSON object of label→probability, e.g. \'{"Sports":0.55,"World":0.45}\'',
    )
    p.add_argument("--min-confidence", type=float, default=0.55)
    p.add_argument("--min-margin", type=float, default=0.10)
    p.add_argument(
        "--from-eval-report",
        type=str,
        default=None,
        help=(
            "Optional path to eval_report.json; prints the top-level `routing` object if present "
            "(training scripts embed policy notes there; does not re-run the model)."
        ),
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    if args.from_eval_report:
        path = Path(args.from_eval_report)
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        routing = data.get("routing")
        if routing is None:
            print("No top-level `routing` key in eval_report (re-train with Phase 2 eval enabled).")
            raise SystemExit(1)
        print(json.dumps(routing, indent=2))
        return

    if args.demo:
        samples = [
            {"World": 0.7, "Sports": 0.1, "Business": 0.1, "Sci/Tech": 0.1},
            {"World": 0.4, "Sports": 0.38, "Business": 0.12, "Sci/Tech": 0.1},
            {"World": 0.51, "Sports": 0.49, "Business": 0.0, "Sci/Tech": 0.0},
        ]
        for i, pr in enumerate(samples, 1):
            d = route_from_probs(
                pr,
                min_confidence=args.min_confidence,
                min_margin=args.min_margin,
            )
            print(f"Example {i}: {d}")
        return

    if args.probs_json:
        pr = json.loads(args.probs_json)
        if not isinstance(pr, dict):
            raise SystemExit("--probs-json must be a JSON object")
        d = route_from_probs(
            {str(k): float(v) for k, v in pr.items()},
            min_confidence=args.min_confidence,
            min_margin=args.min_margin,
        )
        print(d)
        return

    raise SystemExit("Pass --demo, --probs-json '{...}', or --from-eval-report path")


if __name__ == "__main__":
    main()
