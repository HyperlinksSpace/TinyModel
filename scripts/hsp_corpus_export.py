#!/usr/bin/env python3
"""Export texts/hsp_program_corpus.md to JSON for HSP build-time corpus sync.

HSP can copy artifacts/hsp/hsp_program_corpus.json into its API bundle and pass
chunk texts to POST /v1/retrieve or rely on TinyModel /v1/plan with bundled corpus.

Examples:
  python scripts/hsp_corpus_export.py --verify
  python scripts/hsp_corpus_export.py --output artifacts/hsp/hsp_program_corpus.json
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

from hsp_corpus_lib import chunk_title, load_chunks

_CORPUS = _REPO / "texts" / "hsp_program_corpus.md"
_DEFAULT_OUT = _REPO / "artifacts" / "hsp" / "hsp_program_corpus.json"
_SCHEMA = "hsp_program_corpus/1.0"
_PROG = "hsp_corpus_export"
_MIN_CHUNKS = 8


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--corpus",
        type=str,
        default=str(_CORPUS),
        help="Source markdown corpus.",
    )
    p.add_argument(
        "--output",
        type=str,
        default=str(_DEFAULT_OUT),
        help=f"Output JSON path (default: {_DEFAULT_OUT}).",
    )
    p.add_argument(
        "--verify",
        action="store_true",
        help="Exit 0 when export schema and chunk count pass.",
    )
    return p


def export_corpus(corpus_path: Path) -> dict[str, Any]:
    if not corpus_path.is_file():
        raise ValueError(f"missing corpus {corpus_path}")
    chunks = load_chunks(corpus_path)
    if len(chunks) < _MIN_CHUNKS:
        raise ValueError(f"need >= {_MIN_CHUNKS} chunks, got {len(chunks)}")
    rows = [
        {"index": i, "title": chunk_title(text), "text": text}
        for i, text in enumerate(chunks)
    ]
    return {
        "schema": _SCHEMA,
        "source": str(corpus_path.resolve()),
        "chunk_count": len(chunks),
        "chunks": rows,
    }


def validate_export(body: Any) -> None:
    if not isinstance(body, dict):
        raise ValueError("export must be object")
    if body.get("schema") != _SCHEMA:
        raise ValueError(f"schema must be {_SCHEMA!r}")
    count = body.get("chunk_count")
    chunks = body.get("chunks")
    if not isinstance(count, int) or count < _MIN_CHUNKS:
        raise ValueError(f"chunk_count must be int >= {_MIN_CHUNKS}")
    if not isinstance(chunks, list) or len(chunks) != count:
        raise ValueError("chunks length must match chunk_count")
    for row in chunks:
        if not isinstance(row, dict):
            raise ValueError("chunk row must be object")
        idx = row.get("index")
        title = row.get("title")
        text = row.get("text")
        if not isinstance(idx, int) or idx < 0:
            raise ValueError("chunk.index must be non-negative int")
        if not isinstance(title, str) or not title.strip():
            raise ValueError("chunk.title must be non-empty string")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("chunk.text must be non-empty string")


def main() -> None:
    args = build_parser().parse_args()
    corpus_path = Path(args.corpus)
    out_path = Path(args.output)
    try:
        artifact = export_corpus(corpus_path)
        validate_export(artifact)
    except ValueError as e:
        print(f"{_PROG}: FAIL {e}", file=sys.stderr)
        raise SystemExit(1) from e

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out_path} ({artifact['chunk_count']} chunks)")

    if args.verify:
        print(f"{_PROG} verify: OK")


if __name__ == "__main__":
    main()
