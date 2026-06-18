"""Shared helpers for HSP program corpus chunking and stdlib lexical retrieval."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

_STOP = frozenset(
    "a an the to of and or for in on at is are was be as it with from by not"
    .split()
)

# Golden query → expected top-1 chunk title substring (shared by lexical + hybrid smokes).
HSP_RAG_VERIFY_CASES: list[tuple[str, str]] = [
    ("how does the bottom AI search bar work", "AI and Search"),
    ("compare swap slippage on TON", "Swap tokens"),
    ("send wallet recovery phrase backup", "Send and Get wallet"),
    ("sign in with Google or GitHub", "Sign in and accounts"),
    ("what is Shield protection settings", "Shield"),
    ("connect Telegram messages TDLib gateway", "Connect Telegram messages"),
    ("explain home feed NFT items", "Feed"),
    ("smart layout wide viewport panel", "Smart layout"),
    ("USDT token price and holders", "Token info mode"),
    ("switch UI to Russian language", "Languages"),
    ("Windows Electron Telegram Mini App", "Windows and Telegram Mini App"),
    ("never share seed phrase in AI chat", "Getting help safely"),
]

HSP_RAG_MIN_PASS = 10


def corpus_fingerprint(corpus: Path) -> str:
    """SHA-256 hex digest of corpus file bytes (for drift detection across repos)."""
    return hashlib.sha256(corpus.read_bytes()).hexdigest()


def corpus_meta(corpus: Path) -> dict[str, Any]:
    chunks = load_chunks(corpus)
    return {
        "source": str(corpus.resolve()),
        "version": corpus_fingerprint(corpus),
        "chunk_count": len(chunks),
    }


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


def evaluate_rag_verify_cases(
    chunks: list[str],
    rank_fn: Callable[[str, list[str], int], list[tuple[float, int, str]]],
    *,
    cases: list[tuple[str, str]] = HSP_RAG_VERIFY_CASES,
    min_pass: int = HSP_RAG_MIN_PASS,
) -> tuple[bool, list[dict[str, Any]], int]:
    """Score golden queries; rank_fn(query, chunks, top_k) returns (score, index, text) hits."""
    rows: list[dict[str, Any]] = []
    passed = 0
    for query, expect_title in cases:
        hits = rank_fn(query, chunks, 1)
        top_title = chunk_title(hits[0][2]) if hits else ""
        top_score = round(hits[0][0], 4) if hits else 0.0
        ok = expect_title.lower() in top_title.lower()
        if ok:
            passed += 1
        rows.append(
            {
                "query": query,
                "expect_title": expect_title,
                "top_title": top_title,
                "top_score": top_score,
                "ok": ok,
            }
        )
    ok_all = passed >= min_pass and passed == len(cases)
    return ok_all, rows, passed
