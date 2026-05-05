#!/usr/bin/env python3
"""Product-shaped smoke test for TinyModelRuntime: classification, similarity, retrieval.

Scenario (support / triage): given a short customer message, route to the closest
known intent bucket via embedding similarity, and show classifier probabilities.
With **--routing**, each classify block also prints **`routing_policy.route_from_probs`**
(min-confidence / min-margin gates) so the same thresholds as Horizon 1 glue are visible
in one script. **--show-train-routing** prints the checkpoint's **`eval_report.json`**
**`routing`** section first (same helper as **`horizon1_route_then_retrieve`**).

Requires a checkpoint directory or Hub id. On very small / undertrained checkpoints,
similarity scores can look nearly flat; that is expected for a smoke run—use more data
epochs or the published Hub model for meaningful retrieval behavior.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_scripts = Path(__file__).resolve().parent
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))

from eval_report_routing import maybe_print_routing_section
from routing_policy import route_from_probs
from tinymodel_runtime import TinyModelRuntime

_PROG = "embeddings_smoke_test"


def _looks_like_hub_id(s: str) -> bool:
    s = s.replace("\\", "/")
    parts = [p for p in s.split("/") if p]
    return len(parts) == 2 and ".." not in parts and not Path(parts[0]).is_absolute()


def build_parser() -> argparse.ArgumentParser:
    epilog = (
        "Examples:\n"
        "  python scripts/embeddings_smoke_test.py --model artifacts/eval-smoke\n"
        "  python scripts/embeddings_smoke_test.py --model HyperlinksSpace/TinyModel1\n"
        "  python scripts/embeddings_smoke_test.py --model artifacts/eval-smoke "
        "--routing --show-train-routing\n"
        "Train artifacts/eval-smoke first (see README: Embeddings smoke test) if the path is missing."
    )
    p = argparse.ArgumentParser(
        prog=_PROG,
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog,
    )
    p.add_argument(
        "--model",
        type=str,
        default="artifacts/eval-smoke",
        help="Path or Hub id to a TinyModel1-style classification checkpoint.",
    )
    p.add_argument(
        "--routing",
        action="store_true",
        help="After each classify query, print RoutingDecision from route_from_probs (Horizon 1 thresholds).",
    )
    p.add_argument("--min-confidence", type=float, default=0.55)
    p.add_argument("--min-margin", type=float, default=0.10)
    p.add_argument(
        "--show-train-routing",
        action="store_true",
        help="Print eval_report.json top-level routing (Phase 2 notes) before classification output.",
    )
    return p


def parse_args() -> argparse.Namespace:
    return build_parser().parse_args()


def main() -> None:
    args = parse_args()
    p = Path(args.model)
    if not p.exists() and not _looks_like_hub_id(args.model):
        print(
            f"Checkpoint {args.model!r} not found. Train locally first, e.g.:\n"
            "  python scripts/train_tinymodel1_classifier.py "
            "--output-dir artifacts/eval-smoke --max-train-samples 120 "
            "--max-eval-samples 80 --epochs 1 --batch-size 8 --seed 42\n"
            "Or pass a Hub id like HyperlinksSpace/TinyModel1.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    rt = TinyModelRuntime(args.model)
    maybe_print_routing_section(
        args.model, enabled=args.show_train_routing, prog=_PROG,
    )

    queries = [
        "Stock markets rallied after the central bank statement.",
        "The national team won the championship in overtime.",
    ]
    candidates = [
        "Parliament debated the new tax bill in the capital.",
        "Equities rose on strong earnings from tech giants.",
        "The striker scored twice in the derby match.",
    ]

    print("=== Classification (routing scores) ===")
    for q in queries:
        probs = rt.classify([q])[0]
        top = sorted(probs.items(), key=lambda x: -x[1])[:3]
        print(f"Query: {q[:70]!r}...")
        print(f"  top labels: {top}")
        if args.routing:
            d = route_from_probs(
                probs,
                min_confidence=args.min_confidence,
                min_margin=args.min_margin,
            )
            print(f"  routing_policy: {d}")

    print("\n=== Semantic similarity (pairwise) ===")
    a = "Inflation cooled more than economists expected."
    b = "Price growth slowed faster than forecasters predicted."
    c = "The football club signed a new goalkeeper."
    print(f"similarity(a,b)={rt.similarity(a, b):.4f}  (related economic wording)")
    print(f"similarity(a,c)={rt.similarity(a, c):.4f}  (unrelated topic)")

    print("\n=== Retrieval (triage: nearest FAQs / macros) ===")
    query = "My order arrived damaged; I want a refund."
    hits = rt.retrieve(query, candidates, top_k=2)
    print(f"Query: {query!r}")
    for h in hits:
        print(f"  [{h.index}] score={h.score:.4f}  {h.text!r}")

    print("\nEmbeddings smoke test completed.")


if __name__ == "__main__":
    main()
