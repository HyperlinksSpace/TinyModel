#!/usr/bin/env python3
"""Hybrid encoder + lexical RAG smoke over texts/hsp_program_corpus.md (needs torch).

Same golden cases as hsp_rag_smoke.py but ranks with TinyModelRuntime embeddings
plus lexical overlap (rag_faq_smoke hybrid pattern).

Examples:
  python scripts/hsp_rag_hybrid_smoke.py --verify
  python scripts/hsp_rag_hybrid_smoke.py --query "connect Telegram messages" --top-k 3
  python scripts/hsp_rag_hybrid_smoke.py --verify --model HyperlinksSpace/TinyModel1
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

from hsp_corpus_lib import (
    HSP_RAG_MIN_PASS,
    HSP_RAG_VERIFY_CASES,
    chunk_title,
    evaluate_rag_verify_cases,
    load_chunks,
)
from rag_faq_smoke import _pick_model, hybrid_retrieve

_CORPUS = _REPO / "texts" / "hsp_program_corpus.md"
_OUT = _REPO / ".tmp" / "hsp-rag-hybrid-smoke" / "run.json"
_SCHEMA = "hsp_rag_hybrid_smoke_run/1.0"
_PROG = "hsp_rag_hybrid_smoke"


def build_parser() -> argparse.ArgumentParser:
    epilog = (
        "Examples:\n"
        "  python scripts/hsp_rag_hybrid_smoke.py --verify\n"
        "  python scripts/hsp_rag_hybrid_smoke.py --query \"Shield security\" --top-k 2\n"
        "  python scripts/hsp_rag_hybrid_smoke.py --verify --model artifacts/phase1/runs/smoke/ag_news/scratch"
    )
    p = argparse.ArgumentParser(
        prog=_PROG,
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog,
    )
    p.add_argument(
        "--verify",
        action="store_true",
        help=f"Exit 0 when all {len(HSP_RAG_VERIFY_CASES)} golden queries pass with hybrid ranker.",
    )
    p.add_argument(
        "--model",
        type=str,
        default=None,
        help="Checkpoint dir or Hugging Face id (see rag_faq_smoke defaults).",
    )
    p.add_argument(
        "--semantic-only",
        action="store_true",
        help="Use encoder cosine only (stricter; may fail on short HSP chunks).",
    )
    p.add_argument("--query", type=str, default="", help="Ad-hoc hybrid retrieval demo.")
    p.add_argument("--top-k", type=int, default=3)
    p.add_argument("--output-json", type=str, default="", help=f"Write run JSON (default: {_OUT}).")
    return p


def main() -> None:
    args = build_parser().parse_args()
    if not _CORPUS.is_file():
        print(f"Missing {_CORPUS}", file=sys.stderr)
        raise SystemExit(1)

    model_id = _pick_model(args.model)
    if args.model is None:
        print(f"{_PROG}: using model {model_id!r}", file=sys.stderr)

    from tinymodel_runtime import TinyModelRuntime

    chunks = load_chunks(_CORPUS)
    titles = [chunk_title(c) for c in chunks]
    rt = TinyModelRuntime(model_id, device="cpu", max_length=128)

    def _rank(query: str, corpus_chunks: list[str], top_k: int) -> list[tuple[float, int, str]]:
        if args.semantic_only:
            hits = rt.retrieve(query, corpus_chunks, top_k=top_k)
            return [(float(h.score), int(h.index), h.text) for h in hits]
        return hybrid_retrieve(rt, query, corpus_chunks, top_k=top_k)

    if args.query.strip():
        q = args.query.strip()
        hits = _rank(q, chunks, top_k=max(1, args.top_k))
        mode = "semantic" if args.semantic_only else "hybrid"
        print(f"{_PROG}: mode={mode} model={model_id!r} query={q!r}\n")
        for rank, (score, idx, text) in enumerate(hits, 1):
            prev = text[:200].replace("\n", " ")
            print(f"  #{rank} idx={idx} score={score:.4f} title={titles[idx]!r}")
            print(f"       {prev}...")
        return

    verify_ok, case_rows, passed = evaluate_rag_verify_cases(chunks, _rank)
    artifact: dict[str, Any] = {
        "schema": _SCHEMA,
        "mode": "semantic" if args.semantic_only else "hybrid",
        "model": model_id,
        "corpus": str(_CORPUS),
        "chunk_count": len(chunks),
        "titles": titles,
        "cases_total": len(HSP_RAG_VERIFY_CASES),
        "cases_passed": passed,
        "min_pass_required": HSP_RAG_MIN_PASS,
        "ok": verify_ok,
        "cases": case_rows,
    }

    out_path = Path(args.output_json) if args.output_json else _OUT
    if args.verify or args.output_json:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {out_path}")

    print(f"{_PROG}: cases={passed}/{len(HSP_RAG_VERIFY_CASES)} ok={verify_ok}")
    if not verify_ok:
        for row in case_rows:
            if not row["ok"]:
                print(
                    f"{_PROG}: FAIL query={row['query']!r} "
                    f"expected~{row['expect_title']!r} got={row['top_title']!r}",
                    file=sys.stderr,
                )
        raise SystemExit(1)
    if args.verify:
        print(f"{_PROG} verify: OK")


if __name__ == "__main__":
    main()
