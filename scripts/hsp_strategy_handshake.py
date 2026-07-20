"""Strategy site ↔ TinyModel sidecar handshake (stdlib, no torch).

Used by POST /v1/plan so AI CORE can verify the Railway sidecar is the
source of a reply — without waiting on classify/retrieve.
"""

from __future__ import annotations

import re
from typing import Any

# Stable token Strategy asserts in output_text / meta.
HANDSHAKE_TOKEN = "TM1-SIDECAR-OK"
HANDSHAKE_INTENT = "strategy_handshake"
DEFAULT_MODEL = "HyperlinksSpace/TinyModel1"

_STRATEGY_HANDSHAKE = re.compile(
    r"(?:"
    r"\b(?:sidecar\s+)?(?:ping|handshake)\b.{0,80}\b(?:strategy|ai[\s\-]?core)\b"
    r"|"
    r"\b(?:strategy|ai[\s\-]?core)\b.{0,80}\b(?:sidecar\s+)?(?:ping|handshake)\b"
    r"|"
    r"\bsidecar\s+ping\b"
    r")",
    re.I | re.S,
)


def is_strategy_handshake(text: str) -> bool:
    return bool(_STRATEGY_HANDSHAKE.search(text or ""))


def build_handshake_reply(model_name: str | None = None) -> str:
    model = (model_name or DEFAULT_MODEL).strip() or DEFAULT_MODEL
    return (
        f"SIDECAR_OK · {HANDSHAKE_TOKEN} · {model} · "
        "tinymodel.hyperlinks.space · intent=strategy_handshake · "
        "pair=strategy-ai-core"
    )


def strategy_handshake_plan(
    text: str,
    *,
    context: dict[str, Any] | None = None,
    model_name: str | None = None,
) -> dict[str, Any]:
    """Return a full /v1/plan-shaped dict without calling the model."""
    reply = build_handshake_reply(model_name)
    ctx = context or {}
    return {
        "text": text,
        "intent": HANDSHAKE_INTENT,
        "reply_text": reply,
        "context": ctx if ctx else None,
        "route_hint": None,
        "actions": [],
        "probs": {
            "World": 0.0,
            "Sports": 0.0,
            "Business": 0.0,
            "Sci/Tech": 1.0,
        },
        "routing": {
            "fallback": False,
            "label": "Sci/Tech",
            "confidence": 1.0,
            "margin": 1.0,
            "reason": "strategy_handshake",
        },
        "retrieval": {
            "top_idx": -1,
            "top_title": "Strategy ↔ TinyModel handshake",
            "hybrid_score": 1.0,
            "keyword_overlap": 1.0,
            "chunk_preview": reply,
            "query_used": text,
        },
    }
