"""Screen context helpers for HSP explain_screen planning (stdlib, no torch)."""

from __future__ import annotations

import re
from typing import Any

# App route → expected top-1 corpus chunk title substring (texts/hsp_program_corpus.md).
ROUTE_SCREEN_TITLES: dict[str, str] = {
    "/": "AI and Search",
    "/swap": "Swap tokens",
    "/send": "Send and Get wallet",
    "/get": "Send and Get wallet",
    "/shield": "Shield",
    "/feed": "Feed",
    "/smart": "Smart layout",
    "/welcome": "Sign in and accounts",
    "/settings": "Sign in and accounts",
}

_EXPLAIN_SCREEN = re.compile(
    r"\b("
    r"what is this|explain this|this screen|this page|what does this|"
    r"help with this|what can i do here|what is here"
    r")\b",
    re.I,
)
_VAGUE_HELP = re.compile(r"^\s*(help|help me|what is this|explain)\s*[?.!]*\s*$", re.I)


def normalize_route(route: str | None) -> str | None:
    if route is None:
        return None
    r = route.strip().lower()
    if not r:
        return None
    if not r.startswith("/"):
        r = "/" + r
    base = r.split("?")[0].rstrip("/") or "/"
    return base


def screen_title_for_route(route: str | None) -> str | None:
    norm = normalize_route(route)
    if norm is None:
        return None
    return ROUTE_SCREEN_TITLES.get(norm)


def is_explain_screen_query(text: str) -> bool:
    t = text.strip()
    if not t:
        return False
    if _EXPLAIN_SCREEN.search(t):
        return True
    if _VAGUE_HELP.match(t):
        return True
    return False


def build_screen_retrieval_query(text: str, route: str | None) -> str | None:
    """When user is on a known screen and asks vaguely, bias retrieval toward that screen."""
    title = screen_title_for_route(route)
    if not title or not is_explain_screen_query(text):
        return None
    return f"{title} {text.strip()}"


def infer_plan_intent(
    *,
    route_hint: str | None,
    screen_query: str | None,
    routing_fallback: bool,
    retrieval: dict[str, Any] | None,
) -> str:
    if route_hint:
        return "navigate"
    if screen_query is not None:
        return "explain_screen"
    if routing_fallback and retrieval is not None:
        return "chat"
    return "chat"
