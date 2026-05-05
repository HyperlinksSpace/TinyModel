#!/usr/bin/env python3
"""Compare TinyModel classification behavior between a local checkpoint and a Hub model.

Writes a JSON report with per-query probability deltas and aggregate metrics.
Intended for the open parity check in ``plan.txt`` (Hub vs local).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tinymodel_runtime import TinyModelRuntime


DEFAULT_QUERIES = [
    "Breaking: Central bank hints at tighter monetary policy after inflation data.",
    "The team won in overtime after a dramatic final-minute goal.",
    "Scientists announced a new battery chemistry with longer lifespan.",
    "Parliament debated trade sanctions following regional conflict updates.",
]


def _top_label(prob: dict[str, float]) -> tuple[str, float, float]:
    pairs = sorted(prob.items(), key=lambda kv: kv[1], reverse=True)
    label, conf = pairs[0]
    second = pairs[1][1] if len(pairs) > 1 else 0.0
    return label, float(conf), float(conf - second)


def _l1_distance(a: dict[str, float], b: dict[str, float]) -> float:
    keys = set(a) | set(b)
    return float(sum(abs(a.get(k, 0.0) - b.get(k, 0.0)) for k in keys))


def parse_args() -> argparse.Namespace:
    epilog = (
        "Example (from repo root, after training to artifacts/parity-smoke):\n"
        "  python scripts/parity_check_hub_vs_local.py \\\n"
        "    --local-model artifacts/parity-smoke \\\n"
        "    --hub-model HyperlinksSpace/TinyModel1 \\\n"
        "    --output .tmp/parity-check/hub-vs-local.json"
    )
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog,
    )
    p.add_argument(
        "--local-model",
        default="artifacts/parity-smoke",
        help="Local checkpoint path (default: artifacts/parity-smoke).",
    )
    p.add_argument(
        "--hub-model",
        default="HyperlinksSpace/TinyModel1",
        help="Hub model id (default: HyperlinksSpace/TinyModel1).",
    )
    p.add_argument(
        "--query",
        action="append",
        default=[],
        help="Query text to compare (repeatable). If omitted, uses built-in set.",
    )
    p.add_argument(
        "--output",
        default=".tmp/parity-check/hub-vs-local.json",
        help="Output JSON path.",
    )
    p.add_argument(
        "--device",
        default=None,
        help="Optional runtime device (cpu/cuda). Default: auto.",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    queries = args.query if args.query else list(DEFAULT_QUERIES)
    if not queries:
        raise SystemExit("No queries provided.")

    local = TinyModelRuntime(args.local_model, device=args.device)
    hub = TinyModelRuntime(args.hub_model, device=args.device)
    local_probs = local.classify(queries)
    hub_probs = hub.classify(queries)
    if len(local_probs) != len(queries) or len(hub_probs) != len(queries):
        raise RuntimeError(
            "Parity classify output length mismatch: "
            f"queries={len(queries)} local={len(local_probs)} hub={len(hub_probs)}"
        )

    rows: list[dict[str, object]] = []
    label_match_count = 0
    avg_l1 = 0.0
    avg_conf_delta = 0.0
    avg_margin_delta = 0.0

    for q, lp, hp in zip(queries, local_probs, hub_probs):
        l_label, l_conf, l_margin = _top_label(lp)
        h_label, h_conf, h_margin = _top_label(hp)
        label_match = l_label == h_label
        if label_match:
            label_match_count += 1

        l1 = _l1_distance(lp, hp)
        conf_delta = abs(l_conf - h_conf)
        margin_delta = abs(l_margin - h_margin)

        avg_l1 += l1
        avg_conf_delta += conf_delta
        avg_margin_delta += margin_delta

        rows.append(
            {
                "query": q,
                "local_top": {"label": l_label, "confidence": l_conf, "margin": l_margin},
                "hub_top": {"label": h_label, "confidence": h_conf, "margin": h_margin},
                "top_label_match": label_match,
                "l1_probability_distance": l1,
                "top_confidence_delta_abs": conf_delta,
                "top_margin_delta_abs": margin_delta,
                "local_probs": lp,
                "hub_probs": hp,
            }
        )

    n = float(len(rows))
    summary = {
        "n_queries": len(rows),
        "top_label_match_rate": label_match_count / n,
        "avg_l1_probability_distance": avg_l1 / n,
        "avg_top_confidence_delta_abs": avg_conf_delta / n,
        "avg_top_margin_delta_abs": avg_margin_delta / n,
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "tinymodel_hub_local_parity/1.0",
        "local_model": args.local_model,
        "hub_model": args.hub_model,
        "queries": queries,
        "summary": summary,
        "comparisons": rows,
    }
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote parity report: {out}")
    print(
        "Summary: "
        f"match_rate={summary['top_label_match_rate']:.3f} "
        f"avg_l1={summary['avg_l1_probability_distance']:.4f} "
        f"avg_conf_delta={summary['avg_top_confidence_delta_abs']:.4f}",
        flush=True,
    )


if __name__ == "__main__":
    main()
