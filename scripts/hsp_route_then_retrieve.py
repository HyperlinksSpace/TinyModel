#!/usr/bin/env python3
"""HSP control-plane glue: intent router + classify gates + hybrid program corpus retrieval.

Mirrors [`horizon1_route_then_retrieve.py`](horizon1_route_then_retrieve.py) for Hyperlinks
Space Program: deterministic navigational hints first, then encoder classify/routing, then
hybrid FAQ retrieval over [`texts/hsp_program_corpus.md`](texts/hsp_program_corpus.md).

This is the TinyModel-side template for HSP `ai/transmitter.ts` hybrid provider wiring
(no HSP UI changes required).

Examples:
  python scripts/hsp_route_then_retrieve.py --demo
  python scripts/hsp_route_then_retrieve.py --verify
  python scripts/hsp_route_then_retrieve.py --query "open swap page"
  python scripts/hsp_route_then_retrieve.py --query "what is Shield?" --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_scripts = Path(__file__).resolve().parent
_REPO = _scripts.parent
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))

from eval_report_routing import load_routing_from_eval_report, maybe_print_routing_section  # noqa: E402
from hsp_corpus_lib import (  # noqa: E402
    HSP_RAG_MIN_PASS,
    HSP_RAG_VERIFY_CASES,
    chunk_title,
    evaluate_rag_verify_cases,
    load_chunks,
)
from hsp_intent_router import score_hsp_intent_row  # noqa: E402
from hsp_plan_lib import plan_hsp_request  # noqa: E402
from rag_faq_smoke import _pick_model, hybrid_retrieve  # noqa: E402
from routing_policy import RoutingDecision, route_from_probs  # noqa: E402
from tinymodel_runtime import TinyModelRuntime  # noqa: E402

_CORPUS = _REPO / "texts" / "hsp_program_corpus.md"
_INTENTS = _REPO / "texts" / "golden-prompts" / "hsp_intents.jsonl"
_OUT = _REPO / ".tmp" / "hsp-route-then-retrieve" / "run.json"
_SCHEMA = "hsp_route_then_retrieve_run/1.0"
_PROG = "hsp_route_then_retrieve"


def build_parser() -> argparse.ArgumentParser:
    epilog = (
        "Examples:\n"
        "  python scripts/hsp_route_then_retrieve.py --demo\n"
        "  python scripts/hsp_route_then_retrieve.py --verify\n"
        "  python scripts/hsp_route_then_retrieve.py --verify --model .tmp/phase3-smoke\n"
        '  python scripts/hsp_route_then_retrieve.py --query "connect Telegram messages"'
    )
    p = argparse.ArgumentParser(
        prog=_PROG,
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog,
    )
    p.add_argument("--model", type=str, default=None, help="Checkpoint dir or Hub id.")
    p.add_argument("--top-k", type=int, default=2, help="Top-k when hybrid retrieval runs.")
    p.add_argument("--min-confidence", type=float, default=0.55)
    p.add_argument("--min-margin", type=float, default=0.10)
    p.add_argument("--query", type=str, default=None, help="Single user message.")
    p.add_argument("--json", action="store_true", help="Emit one JSON object.")
    p.add_argument("--demo", action="store_true", help="Illustrative mixed-intent samples.")
    p.add_argument(
        "--verify",
        action="store_true",
        help="Exit 0 when intent golden rows, hybrid RAG cases, and classify gate pass.",
    )
    p.add_argument(
        "--show-train-routing",
        action="store_true",
        help="Print eval_report.json routing section before --demo / --query output.",
    )
    p.add_argument("--output-json", type=str, default="", help=f"Write verify artifact (default: {_OUT}).")
    return p


def parse_args() -> argparse.Namespace:
    return build_parser().parse_args()


def _load_intent_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in _INTENTS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _print_human(plan: dict[str, Any]) -> None:
    text = plan["text"]
    print(f"text: {text[:120]!r}{'...' if len(text) > 120 else ''}")
    if plan["route_hint"]:
        print(f"  route_hint: {plan['route_hint']!r}")
        print(f"  actions: {plan['actions']}")
    routing = plan["routing"]
    top3 = sorted(plan["probs"].items(), key=lambda x: -x[1])[:3]
    print(f"  top_probs: {top3}")
    print(
        f"  routing: fallback={routing['fallback']} label={routing['label']!r} "
        f"reason={routing['reason']}"
    )
    if plan["retrieval"]:
        r = plan["retrieval"]
        print(
            f"  retrieval[0]: idx={r['top_idx']} title={r['top_title']!r} "
            f"hybrid={r['hybrid_score']:.4f} keyword_overlap={r['keyword_overlap']:.3f}"
        )
        prev = r["chunk_preview"][:220].replace("\n", " ")
        print(f"    {prev!r}...")
    elif not plan["route_hint"]:
        print("  retrieval: (skipped — routing accepted label)")


def run_verify(model_id: str, chunks: list[str], rt: TinyModelRuntime) -> dict[str, Any]:
    """Three-axis verify: golden intents, hybrid RAG cases, classify always-accept."""
    intent_rows = _load_intent_rows()
    intent_results: list[dict[str, Any]] = []
    intent_passed = 0
    for row in intent_rows:
        ok, detail, detected = score_hsp_intent_row(row)
        if ok:
            intent_passed += 1
        intent_results.append(
            {
                "id": row.get("id"),
                "prompt": row.get("prompt"),
                "expect_route": row.get("expect_route"),
                "detected_route": detected,
                "ok": ok,
                "detail": detail,
            }
        )
    if intent_passed != len(intent_rows):
        failed = [r for r in intent_results if not r["ok"]]
        print(f"{_PROG}: intent FAIL {len(failed)}/{len(intent_rows)}", file=sys.stderr)
        for r in failed[:5]:
            print(f"  {r['prompt']!r}: {r['detail']}", file=sys.stderr)
        raise SystemExit(1)

    def _rank(query: str, corpus_chunks: list[str], top_k: int) -> list[tuple[float, int, str]]:
        return hybrid_retrieve(rt, query, corpus_chunks, top_k=top_k)

    rag_ok, rag_rows, rag_passed = evaluate_rag_verify_cases(chunks, _rank)
    if not rag_ok:
        print(
            f"{_PROG}: hybrid RAG FAIL {rag_passed}/{len(HSP_RAG_VERIFY_CASES)} "
            f"(min {HSP_RAG_MIN_PASS})",
            file=sys.stderr,
        )
        for row in rag_rows:
            if not row["ok"]:
                print(
                    f"  query={row['query']!r} expected~{row['expect_title']!r} "
                    f"got={row['top_title']!r}",
                    file=sys.stderr,
                )
        raise SystemExit(1)

    probs = rt.classify(["The national team won the championship in overtime."])[0]
    d = route_from_probs(probs, min_confidence=0.0, min_margin=0.0)
    if d.fallback or d.label is None:
        print(f"{_PROG}: classify gate FAIL expected accept, got {d}", file=sys.stderr)
        raise SystemExit(1)

    return {
        "schema": _SCHEMA,
        "model": model_id,
        "corpus": str(_CORPUS),
        "chunk_count": len(chunks),
        "intent_cases_total": len(intent_rows),
        "intent_cases_passed": intent_passed,
        "rag_cases_total": len(HSP_RAG_VERIFY_CASES),
        "rag_cases_passed": rag_passed,
        "rag_min_pass_required": HSP_RAG_MIN_PASS,
        "classify_gate": "always_accept_zero_thresholds",
        "ok": True,
        "intent_cases": intent_results,
        "rag_cases": rag_rows,
    }


def main() -> None:
    args = parse_args()
    if not _CORPUS.is_file():
        print(f"Missing corpus {_CORPUS}", file=sys.stderr)
        raise SystemExit(1)

    model_id = _pick_model(args.model)
    if args.model is None:
        print(f"{_PROG}: using model {model_id!r}", file=sys.stderr)

    chunks = load_chunks(_CORPUS)
    rt = TinyModelRuntime(model_id, device="cpu", max_length=128)

    if args.verify:
        artifact = run_verify(model_id, chunks, rt)
        out_path = Path(args.output_json) if args.output_json else _OUT
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {out_path}")
        print(
            f"{_PROG}: intents={artifact['intent_cases_passed']}/{artifact['intent_cases_total']} "
            f"rag={artifact['rag_cases_passed']}/{artifact['rag_cases_total']} ok=True"
        )
        print(f"{_PROG} verify: OK")
        return

    if args.query is not None:
        q = args.query.strip()
        maybe_print_routing_section(model_id, enabled=args.show_train_routing, prog=_PROG)
        plan = plan_hsp_request(
            q,
            rt,
            chunks,
            min_confidence=args.min_confidence,
            min_margin=args.min_margin,
            top_k=args.top_k,
        )
        if args.json:
            plan["train_routing"] = load_routing_from_eval_report(model_id)
            print(json.dumps(plan))
        else:
            _print_human(plan)
        return

    if args.demo:
        maybe_print_routing_section(model_id, enabled=args.show_train_routing, prog=_PROG)
        samples = [
            "open swap page",
            "what is Shield protection settings",
            "connect Telegram messages TDLib gateway",
            "Explain gas fees on TON",
        ]
        print("=== HSP route hint -> classify -> (retrieve if fallback) ===\n")
        for q in samples:
            plan = plan_hsp_request(
                q,
                rt,
                chunks,
                min_confidence=args.min_confidence,
                min_margin=args.min_margin,
                top_k=args.top_k,
            )
            _print_human(plan)
            print()
        return

    build_parser().print_help()
    print(
        "\nPass --demo, --query \"...\", or --verify.",
        file=sys.stderr,
    )
    raise SystemExit(2)


if __name__ == "__main__":
    main()
