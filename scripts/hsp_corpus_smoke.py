#!/usr/bin/env python3
"""Smoke-check texts/hsp_program_corpus.md chunking (stdlib-only --verify)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_scripts = Path(__file__).resolve().parent
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))

from hsp_corpus_lib import load_chunks

_REPO = _scripts.parent
_CORPUS = _REPO / "texts" / "hsp_program_corpus.md"
_OUT = _REPO / ".tmp" / "hsp-corpus-smoke" / "run.json"
_SCHEMA = "hsp_corpus_smoke_run/1.0"
_MIN_CHUNKS = 8


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verify", action="store_true", help="Exit 0 when corpus loads with enough chunks.")
    p.add_argument("--output-json", type=str, default="", help=f"Write run JSON (default: {_OUT}).")
    p.add_argument("--query", type=str, default="", help="Optional keyword overlap demo on chunks.")
    return p


def main() -> None:
    args = build_parser().parse_args()
    if not _CORPUS.is_file():
        print(f"Missing {_CORPUS}", file=sys.stderr)
        raise SystemExit(1)

    chunks = load_chunks(_CORPUS)
    ok = len(chunks) >= _MIN_CHUNKS
    titles = [c.split("\n", 1)[0] for c in chunks]

    demo_hits: list[dict[str, object]] = []
    if args.query.strip():
        from hsp_corpus_lib import lexical_rank

        q = args.query.strip()
        for score, i, ch in lexical_rank(q, chunks, top_k=len(chunks)):
            if score <= 0:
                continue
            demo_hits.append(
                {"index": i, "title": titles[i], "score": round(score, 4), "preview": ch[:120]}
            )
            if len(demo_hits) >= 5:
                break

    artifact = {
        "schema": _SCHEMA,
        "corpus": str(_CORPUS),
        "chunk_count": len(chunks),
        "titles": titles,
        "min_chunks_required": _MIN_CHUNKS,
        "ok": ok,
        "query": args.query or None,
        "demo_hits": demo_hits or None,
    }

    out_path = Path(args.output_json) if args.output_json else _OUT
    if args.verify or args.output_json:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {out_path}")

    print(f"hsp_corpus: chunks={len(chunks)} ok={ok}")
    if not ok:
        print(f"hsp_corpus: FAIL need >= {_MIN_CHUNKS} chunks", file=sys.stderr)
        raise SystemExit(1)
    if args.verify:
        print("hsp_corpus verify: OK")


if __name__ == "__main__":
    main()
