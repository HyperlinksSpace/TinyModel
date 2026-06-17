"""Shared HSP control-plane planning (intent router + classify + hybrid retrieval)."""

from __future__ import annotations

from typing import Any

from hsp_corpus_lib import chunk_title
from hsp_intent_router import actions_from_route_hint, infer_hsp_route_hint
from hsp_screen_context import build_screen_retrieval_query, infer_plan_intent
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
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return HSP-shaped plan: route hint, actions, classify probs, routing, optional retrieval."""
    ctx = context or {}
    route = ctx.get("route") if isinstance(ctx.get("route"), str) else None

    route_hint = infer_hsp_route_hint(text)
    actions = actions_from_route_hint(route_hint)
    probs = rt.classify([text])[0]
    routing = route_from_probs(probs, min_confidence=min_confidence, min_margin=min_margin)

    screen_query = build_screen_retrieval_query(text, route)
    retrieval: dict[str, Any] | None = None
    should_retrieve = (not route_hint and routing.fallback) or screen_query is not None
    if should_retrieve:
        query = screen_query if screen_query is not None else text
        hr = hybrid_retrieve(rt, query, chunks, top_k=top_k)
        if hr:
            score, idx, ch = hr[0]
            retrieval = {
                "top_idx": idx,
                "top_title": chunk_title(ch),
                "hybrid_score": score,
                "keyword_overlap": overlap_faithfulness(query, ch),
                "chunk_preview": ch[:400],
                "query_used": query if query != text else None,
            }

    intent = infer_plan_intent(
        route_hint=route_hint,
        screen_query=screen_query,
        routing_fallback=routing.fallback,
        retrieval=retrieval,
    )

    return {
        "text": text,
        "intent": intent,
        "context": ctx if ctx else None,
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
