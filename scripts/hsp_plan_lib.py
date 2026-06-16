"""Shared HSP control-plane planning (intent router + classify + hybrid retrieval)."""

from __future__ import annotations

from typing import Any

from hsp_corpus_lib import chunk_title
from hsp_intent_router import actions_from_route_hint, infer_hsp_route_hint
from rag_faq_smoke import hybrid_retrieve, overlap_faithfulness
from routing_policy import route_from_probs
from tinymodel_runtime import TinyModelRuntime


def plan_hsp_request(
    text: str,
    rt: TinyModelRuntime,
    chunks: list[str],
    *,
    min_confidence: float = 0.55,
    min_margin: float = 0.10,
    top_k: int = 2,
) -> dict[str, Any]:
    """Return HSP-shaped plan: route hint, actions, classify probs, routing, optional retrieval."""
    route_hint = infer_hsp_route_hint(text)
    actions = actions_from_route_hint(route_hint)
    probs = rt.classify([text])[0]
    routing = route_from_probs(probs, min_confidence=min_confidence, min_margin=min_margin)

    retrieval: dict[str, Any] | None = None
    if not route_hint and routing.fallback:
        hr = hybrid_retrieve(rt, text, chunks, top_k=top_k)
        if hr:
            score, idx, ch = hr[0]
            retrieval = {
                "top_idx": idx,
                "top_title": chunk_title(ch),
                "hybrid_score": score,
                "keyword_overlap": overlap_faithfulness(text, ch),
                "chunk_preview": ch[:400],
            }

    return {
        "text": text,
        "route_hint": route_hint,
        "actions": actions,
        "probs": probs,
        "routing": {
            "fallback": routing.fallback,
            "label": routing.label,
            "confidence": routing.confidence,
            "margin": routing.margin,
            "reason": routing.reason,
        },
        "retrieval": retrieval,
    }
