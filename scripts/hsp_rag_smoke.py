#!/usr/bin/env python3
"""Stdlib lexical retrieval smoke over texts/hsp_program_corpus.md (Phase 0 RAG gate).

Examples:
  python scripts/hsp_rag_smoke.py --verify
  python scripts/hsp_rag_smoke.py --query "How do I connect Telegram messages?"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_scripts = Path(__file__).resolve().parent
_REPO = _scripts.parent
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))

from hsp_corpus_lib import (
    HSP_RAG_MIN_PASS,
    HSP_RAG_VERIFY_CASES,
    chunk_title,
    evaluate_rag_verify_cases,
    lexical_rank,
    load_chunks,
)

_CORPUS = _REPO / "texts" / "hsp_program_corpus.md"
_OUT = _REPO / ".tmp" / "hsp-rag-smoke" / "run.json"
_SCHEMA = "hsp_rag_smoke_run/1.0"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--verify",
        action="store_true",
        help=f"Exit 0 when all {len(HSP_RAG_VERIFY_CASES)} golden queries rank the expected chunk first.",
    )
    p.add_argument("--query", type=str, default="", help="Ad-hoc retrieval demo (prints top-k).")
    p.add_argument("--top-k", type=int, default=3, help="Hits to return (default: 3).")
    p.add_argument("--output-json", type=str, default="", help=f"Write run JSON (default: {_OUT}).")
    return p


def main() -> None:
    args = build_parser().parse_args()
    if not _CORPUS.is_file():
        print(f"Missing {_CORPUS}", file=sys.stderr)
        raise SystemExit(1)

    chunks = load_chunks(_CORPUS)
    titles = [chunk_title(c) for c in chunks]

    if args.query.strip():
        q = args.query.strip()
        hits = lexical_rank(q, chunks, top_k=max(1, args.top_k))
        print(f"hsp_rag: query={q!r} corpus_chunks={len(chunks)}\n")
        for rank, (score, idx, text) in enumerate(hits, 1):
            prev = text[:200].replace("\n", " ")
            print(f"  #{rank} idx={idx} score={score:.4f} title={titles[idx]!r}")
            print(f"       {prev}...")
        return

    def _lex_rank(query: str, corpus_chunks: list[str], top_k: int) -> list[tuple[float, int, str]]:
        return lexical_rank(query, corpus_chunks, top_k=top_k)

    verify_ok, case_rows, passed = evaluate_rag_verify_cases(chunks, _lex_rank)
    artifact = {
        "schema": _SCHEMA,
        "mode": "lexical",
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

    print(f"hsp_rag: cases={passed}/{len(HSP_RAG_VERIFY_CASES)} ok={verify_ok}")
    if not verify_ok:
        for row in case_rows:
            if not row["ok"]:
                print(
                    f"hsp_rag: FAIL query={row['query']!r} "
                    f"expected~{row['expect_title']!r} got={row['top_title']!r}",
                    file=sys.stderr,
                )
        raise SystemExit(1)
    if args.verify:
        print("hsp_rag verify: OK")


if __name__ == "__main__":
    main()
