#!/usr/bin/env python3
"""Classifier gates + FAQ retrieval on fallback (Horizon 1 «route then retrieve» glue).

Runs **TinyModelRuntime.classify** -> **routing_policy.route_from_probs**. When the policy
**abstains** (low confidence or ambiguous margin), runs the same **hybrid** ranker as
`rag_faq_smoke.py` over `texts/rag_faq_corpus.md` so support-style queries still get a
citation-style chunk index.

This is the short missing link between [`routing_policy.py`](routing_policy.py) and
[`rag_faq_smoke.py`](rag_faq_smoke.py) without pulling in Horizon 2 chat/LM deps."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_scripts = Path(__file__).resolve().parent
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))

from eval_report_routing import load_routing_from_eval_report, maybe_print_routing_section  # noqa: E402
from rag_faq_smoke import (  # noqa: E402
    _pick_model,
    hybrid_retrieve,
    load_chunks,
    overlap_faithfulness,
)
from routing_policy import RoutingDecision, route_from_probs  # noqa: E402
from tinymodel_runtime import TinyModelRuntime  # noqa: E402

_PROG = "horizon1_route_then_retrieve"


def build_parser() -> argparse.ArgumentParser:
    epilog = (
        "Examples:\n"
        "  python scripts/horizon1_route_then_retrieve.py --demo\n"
        "  python scripts/horizon1_route_then_retrieve.py --verify "
        "--model artifacts/phase1/runs/smoke/ag_news/scratch\n"
        "  python scripts/horizon1_route_then_retrieve.py "
        '--query "How do I get a refund?" --top-k 3\n'
        "See the README Route-to-RAG quick checklist for --model defaults."
    )
    p = argparse.ArgumentParser(
        prog=_PROG,
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog,
    )
    p.add_argument("--model", type=str, default=None, help="Checkpoint dir or Hub id (see rag_faq_smoke).")
    p.add_argument(
        "--corpus",
        type=str,
        default="texts/rag_faq_corpus.md",
        help="FAQ markdown with ## sections.",
    )
    p.add_argument("--top-k", type=int, default=2, help="Top-k when retrieval runs.")
    p.add_argument("--min-confidence", type=float, default=0.55)
    p.add_argument("--min-margin", type=float, default=0.10)
    p.add_argument(
        "--query",
        type=str,
        default=None,
        help="Single user message; print routing + optional retrieval.",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Emit one JSON object per line (machine-readable).",
    )
    p.add_argument(
        "--demo",
        action="store_true",
        help="Run a few illustrative queries with default thresholds (prints human text).",
    )
    p.add_argument(
        "--verify",
        action="store_true",
        help="Exit 0 only if forced-fallback RAG and always-accept classify checks pass.",
    )
    p.add_argument(
        "--show-train-routing",
        action="store_true",
        help=(
            "If --model is a local checkpoint dir with eval_report.json, print the top-level "
            "`routing` section (Phase 2 training notes) before --demo / --query output."
        ),
    )
    return p


def parse_args() -> argparse.Namespace:
    return build_parser().parse_args()


def _print_human(
    text: str,
    probs: dict[str, float],
    d: RoutingDecision,
    *,
    top_k: int,
    rt: TinyModelRuntime,
    chunks: list[str],
) -> None:
    top3 = sorted(probs.items(), key=lambda x: -x[1])[:3]
    print(f"text: {text[:120]!r}{'...' if len(text) > 120 else ''}")
    print(f"  top_probs: {top3}")
    print(f"  routing: fallback={d.fallback} label={d.label!r} reason={d.reason}")
    if d.fallback:
        hr = hybrid_retrieve(rt, text, chunks, top_k=top_k)
        if not hr:
            print("  retrieval: (no chunks)")
            return
        score, idx, ch = hr[0]
        ov = overlap_faithfulness(text, ch)
        prev = ch[:220].replace("\n", " ")
        print(f"  retrieval[0]: idx={idx} hybrid={score:.4f} keyword_overlap={ov:.3f}")
        print(f"    {prev!r}...")
    else:
        print(f"  action: use label {d.label!r} (no FAQ retrieval).")


def _json_line(
    text: str,
    probs: dict[str, float],
    d: RoutingDecision,
    *,
    model_id: str,
    top_k: int,
    rt: TinyModelRuntime,
    chunks: list[str],
) -> dict:
    row: dict = {
        "text": text,
        "probs": probs,
        "train_routing": load_routing_from_eval_report(model_id),
        "routing": {
            "fallback": d.fallback,
            "label": d.label,
            "confidence": d.confidence,
            "margin": d.margin,
            "reason": d.reason,
        },
        "retrieval": None,
    }
    if d.fallback:
        hr = hybrid_retrieve(rt, text, chunks, top_k=top_k)
        if hr:
            score, idx, ch = hr[0]
            row["retrieval"] = {
                "top_idx": idx,
                "hybrid_score": score,
                "keyword_overlap": overlap_faithfulness(text, ch),
                "chunk_preview": ch[:400],
            }
    return row


def run_verify(model_id: str, corpus: Path, chunks: list[str], rt: TinyModelRuntime) -> None:
    """Two-axis check: (1) forced fallback → RAG passes same cheap gates as rag_faq_smoke."""
    faq_samples: list[tuple[str, str]] = [
        ("How do I get a refund for my order?", "refund"),
        ("I see an unauthorized login on my account", "password"),
        ("My package tracking says exception, what do I do?", "exception"),
    ]
    # Impossible confidence floor → every classify path abstains → retrieval must cite.
    mc, mm = 1.01, 0.0
    for q, must in faq_samples:
        probs = rt.classify([q])[0]
        d = route_from_probs(probs, min_confidence=mc, min_margin=mm)
        if not d.fallback:
            print(f"verify: expected fallback for forced thresholds, got {d}", file=sys.stderr)
            raise SystemExit(1)
        hr = hybrid_retrieve(rt, q, chunks, top_k=2)
        if not hr:
            print("verify: empty retrieval", file=sys.stderr)
            raise SystemExit(1)
        _s, _i, top_text = hr[0]
        f = overlap_faithfulness(q, top_text)
        cited = must.lower() in top_text.lower()
        ok = cited or f >= 0.12
        if not ok:
            print(f"verify: RAG failed for {q!r}", file=sys.stderr)
            raise SystemExit(1)

    # Always-accept path: loose thresholds — label must be chosen.
    probs = rt.classify(["The national team won the championship in overtime."])[0]
    d = route_from_probs(probs, min_confidence=0.0, min_margin=0.0)
    if d.fallback or d.label is None:
        print(f"verify: expected accept with zero thresholds, got {d}", file=sys.stderr)
        raise SystemExit(1)

    print("horizon1_route_then_retrieve: verify OK")


def main() -> None:
    args = parse_args()
    model_id = _pick_model(args.model)
    if args.model is None:
        print(f"horizon1_route_then_retrieve: using --model {model_id!r}", file=sys.stderr)

    corpus = Path(args.corpus)
    if not corpus.is_file():
        print(f"Corpus not found: {corpus}", file=sys.stderr)
        raise SystemExit(1)
    chunks = load_chunks(corpus)
    rt = TinyModelRuntime(model_id, device="cpu", max_length=128)

    if args.verify:
        run_verify(model_id, corpus, chunks, rt)
        return

    if args.query is not None:
        q = args.query.strip()
        maybe_print_routing_section(
            model_id, enabled=args.show_train_routing, prog=_PROG,
        )
        probs = rt.classify([q])[0]
        d = route_from_probs(
            probs,
            min_confidence=args.min_confidence,
            min_margin=args.min_margin,
        )
        if args.json:
            print(
                json.dumps(
                    _json_line(
                        q,
                        probs,
                        d,
                        model_id=model_id,
                        top_k=args.top_k,
                        rt=rt,
                        chunks=chunks,
                    ),
                ),
            )
        else:
            _print_human(q, probs, d, top_k=args.top_k, rt=rt, chunks=chunks)
        return

    if args.demo:
        maybe_print_routing_section(
            model_id, enabled=args.show_train_routing, prog=_PROG,
        )
        samples = [
            "Federal regulators approved the merger after markets closed.",
            "How do I get a refund for my order?",
            "Quarterfinal match ended in a penalty shootout.",
        ]
        print("=== route -> (retrieve if fallback) ===\n")
        for q in samples:
            probs = rt.classify([q])[0]
            d = route_from_probs(
                probs,
                min_confidence=args.min_confidence,
                min_margin=args.min_margin,
            )
            _print_human(q, probs, d, top_k=args.top_k, rt=rt, chunks=chunks)
            print()
        return

    build_parser().print_help()
    print(
        "\nPass --demo, --query \"...\", or --verify (see README Route-to-RAG checklist).",
        file=sys.stderr,
    )
    raise SystemExit(2)


if __name__ == "__main__":
    main()
