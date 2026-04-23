#!/usr/bin/env python3
"""Minimal RAG-style retrieval + simple faithfulness check (Horizon 1 short-term C).

Chunks a FAQ markdown corpus by `##` sections, embeds with TinyModelRuntime, retrieves top
matches for a query, and reports **keyword overlap** in the top hit as a cheap faithfulness
proxy (not neural entailment)."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_scripts = Path(__file__).resolve().parent
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))

from tinymodel_runtime import TinyModelRuntime

_STOP = frozenset(
    "a an the to of and or for in on at is are was be as it with from by not"
    .split()
)

_REPO = Path(__file__).resolve().parent.parent
# When --model is omitted, first existing dir wins; else published Hub weights.
_DEFAULT_MODEL_DIRS = (
    "artifacts/horizon1/three-tasks/ag_news",
    "artifacts/phase1/runs/smoke/ag_news/scratch",
    ".tmp/TinyModel-local",
    ".tmp/horizon1-verify-a",
)
_DEFAULT_HUB = "HyperlinksSpace/TinyModel1"


def _pick_model(explicit: str | None) -> str:
    """Resolve local checkpoint dir, or a Hugging Face model id (namespace/name)."""
    if explicit is None:
        for rel in _DEFAULT_MODEL_DIRS:
            d = _REPO / rel
            if (d / "config.json").is_file():
                return str(d.resolve())
        return _DEFAULT_HUB
    p = Path(explicit)
    for d in (p.resolve(), (_REPO / explicit).resolve()):
        if d.is_dir() and (d / "config.json").is_file():
            return str(d)
    if p.exists() or (_REPO / explicit).exists():
        print(
            f"Not a model directory (expected config.json): {explicit!r}\n"
            "Train first, e.g.:\n"
            "  python scripts/train_tinymodel1_agnews.py --output-dir .tmp/rag-encoder "
            "--max-train-samples 200 --max-eval-samples 100 --epochs 1 --batch-size 8 --seed 42",
            file=sys.stderr,
        )
        raise SystemExit(1)
    return explicit  # Hub id, e.g. HyperlinksSpace/TinyModel1


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--model",
        type=str,
        default=None,
        help=(
            "Trained checkpoint directory or Hugging Face model id. "
            f"If omitted, uses the first of {_DEFAULT_MODEL_DIRS} that contains config.json, "
            f"else {_DEFAULT_HUB!r}."
        ),
    )
    p.add_argument(
        "--corpus",
        type=str,
        default="texts/rag_faq_corpus.md",
        help="Markdown file with ##-delimited chunks.",
    )
    p.add_argument("--top-k", type=int, default=2)
    p.add_argument(
        "--semantic-only",
        action="store_true",
        help="Use only TinyModelRuntime.retrieve (stricter; tiny encoders may fail on short FAQ chunks).",
    )
    return p.parse_args()


def load_chunks(corpus: Path) -> list[str]:
    text = corpus.read_text(encoding="utf-8")
    # `re.split` with a capture: [preamble, title1, body1, title2, body2, ...]
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


def tokenize(s: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[A-Za-z0-9']+", s) if w.lower() not in _STOP}


def overlap_faithfulness(query: str, chunk: str) -> float:
    q, c = tokenize(query), tokenize(chunk)
    if not q:
        return 0.0
    return len(q & c) / max(len(q), 1)


def lex_substring_score(query: str, chunk: str) -> float:
    """Cheap overlap: fraction of 3+ char alphanumeric query tokens that appear as substrings."""
    cl = chunk.lower()
    hit = tot = 0
    for w in re.findall(r"[a-z0-9]+", query.lower()):
        if len(w) < 3:
            continue
        tot += 1
        if w in cl:
            hit += 1
    return hit / max(tot, 1)


def hybrid_retrieve(
    rt: TinyModelRuntime,
    query: str,
    chunks: list[str],
    *,
    top_k: int,
    embed_weight: float = 0.45,
) -> list[tuple[float, int, str]]:
    """Combine cosine (encoder) + lexical overlap so tiny scratch encoders still rank sensible FAQ chunks."""
    if not chunks:
        return []
    texts = [query, *chunks]
    embs = rt.embed(texts, normalize=True)
    qe = embs[0:1]
    ce = embs[1:]
    cos = (qe @ ce.T).squeeze(0)
    ranked: list[tuple[float, int]] = []
    for i, ch in enumerate(chunks):
        lex = lex_substring_score(query, ch)
        s = embed_weight * float(cos[i]) + (1.0 - embed_weight) * lex
        ranked.append((s, i))
    ranked.sort(key=lambda x: -x[0])
    out: list[tuple[float, int, str]] = []
    for s, i in ranked[:top_k]:
        out.append((s, i, chunks[i]))
    return out


def main() -> None:
    args = parse_args()
    model_id = _pick_model(args.model)
    if args.model is None:
        print(f"rag_faq_smoke: using --model {model_id!r} (set explicitly to override).", file=sys.stderr)

    corpus = Path(args.corpus)
    if not corpus.is_file():
        print(f"Corpus not found: {corpus}", file=sys.stderr)
        raise SystemExit(1)

    chunks = load_chunks(corpus)
    rt = TinyModelRuntime(model_id, device="cpu", max_length=128)
    print("=== RAG FAQ smoke (retrieval) ===\n")
    # (query, substring that must appear in top-1 chunk for a pass — citation-style check)
    samples: list[tuple[str, str]] = [
        ("How do I get a refund for my order?", "refund"),
        ("I see an unauthorized login on my account", "password"),
        ('My package tracking says exception, what do I do?', "exception"),
    ]
    all_ok = True
    for q, must in samples:
        if args.semantic_only:
            hits = rt.retrieve(q, chunks, top_k=args.top_k)
            top_text = hits[0].text
            top_score = hits[0].score
        else:
            hr = hybrid_retrieve(rt, q, chunks, top_k=args.top_k)
            top_score, _idx, top_text = hr[0]
        f = overlap_faithfulness(q, top_text)
        cited = must.lower() in top_text.lower()
        ok = cited or f >= 0.12
        if not ok:
            all_ok = False
        status = "ok" if ok else "fail"
        print(f"Q: {q}")
        print(
            f"  top hybrid/semantic score={top_score:.4f}  keyword_overlap={f:.2f}  "
            f"contains({must!r})={cited}  [{status}]"
        )
        safe = top_text[:200].replace(chr(10), " ").encode("ascii", "replace").decode("ascii")
        print(f"  chunk preview: {safe}...")
        print()
    if all_ok:
        print(
            "RAG FAQ smoke: passed (default: hybrid lexical + encoder; use --semantic-only to stress pure embedding retrieval).",
        )
    else:
        print(
            "RAG smoke failed: re-train the encoder, use a larger/HF model, or add training pairs.",
            file=sys.stderr,
        )
        raise SystemExit(1)


if __name__ == "__main__":
    main()
