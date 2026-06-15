"""Shared helpers for HSP program corpus chunking and stdlib lexical retrieval."""

from __future__ import annotations

import re
from pathlib import Path

_STOP = frozenset(
    "a an the to of and or for in on at is are was be as it with from by not"
    .split()
)


def load_chunks(corpus: Path) -> list[str]:
    text = corpus.read_text(encoding="utf-8")
    parts = re.split(r"(?m)^##\s+(.+)$", text)
    chunks: list[str] = []
    for idx in range(1, len(parts), 2):
        if idx + 1 >= len(parts):
            break
        title = parts[idx].strip()
        body = parts[idx + 1].strip()
        if body:
            chunks.append(f"{title}\n{body}")
    return chunks if chunks else [text.strip()]


def chunk_title(chunk: str) -> str:
    return chunk.split("\n", 1)[0].strip()


def tokenize(s: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[A-Za-z0-9']+", s) if w.lower() not in _STOP}


def overlap_faithfulness(query: str, chunk: str) -> float:
    q, c = tokenize(query), tokenize(chunk)
    if not q:
        return 0.0
    return len(q & c) / max(len(q), 1)


def lex_substring_score(query: str, chunk: str) -> float:
    """Fraction of 3+ char query tokens that appear as substrings in the chunk."""
    cl = chunk.lower()
    hit = tot = 0
    for w in re.findall(r"[a-z0-9]+", query.lower()):
        if len(w) < 3:
            continue
        tot += 1
        if w in cl:
            hit += 1
    return hit / max(tot, 1)


def lexical_rank(
    query: str,
    chunks: list[str],
    *,
    top_k: int = 3,
) -> list[tuple[float, int, str]]:
    """Rank corpus chunks by stdlib lexical overlap (no torch)."""
    if not chunks:
        return []
    ranked: list[tuple[float, int, str]] = []
    for i, ch in enumerate(chunks):
        lex = lex_substring_score(query, ch)
        overlap = overlap_faithfulness(query, ch)
        score = 0.55 * lex + 0.45 * overlap
        ranked.append((score, i, ch))
    ranked.sort(key=lambda x: (-x[0], x[1]))
    return ranked[: min(top_k, len(ranked))]
