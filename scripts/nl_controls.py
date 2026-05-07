"""Natural-language control phrases for Universal Brain chat.

This is a lightweight, deterministic pre-router for actions that should not depend on
LLM JSON routing (and should work without requiring users to remember slash commands).

It is intentionally conservative: it only triggers on fairly explicit phrasing.
"""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class ControlAction:
    name: str
    value: str | None = None


_WS = re.compile(r"\s+")


def _norm(s: str) -> str:
    return _WS.sub(" ", (s or "").strip().lower())


def parse_control_action(message: str) -> ControlAction | None:
    """Return a ControlAction if the message is a natural-language control request."""
    m = _norm(message)
    if not m:
        return None

    # "What mode is this? What session/scope am I in?"
    if re.search(r"\b(what|show)\b.*\b(my )?(session|scope|settings|mode|status)\b", m) or re.search(
        r"\bwhich\b.*\b(scope|session)\b", m
    ):
        return ControlAction("show_session")

    # Start a fresh private session (new scope key).
    if re.search(r"\b(new|fresh)\b.*\b(private )?(session|scope)\b", m) or re.search(
        r"\b(start|begin)\b.*\b(private )?(session|scope)\b", m
    ):
        return ControlAction("new_private_session")

    # Switch to a named scope in chat, e.g. "use scope abc-123" / "switch to session foo".
    m2 = re.search(r"\b(use|switch to|set)\b.*\b(scope|session)\b\s*[:=]?\s*([a-z0-9][a-z0-9_.:-]{1,63})\b", m)
    if m2:
        return ControlAction("set_scope", m2.group(3))

    # Memory controls (order matters: list/show before export/download)
    if re.search(
        r"\b(show|list)\b.*\b(my )?(data|memory|memories|notes)\b",
        m,
    ):
        return ControlAction("list_memories")
    if re.search(
        r"\b(export|download)\b.*\b(my )?(data|memory|memories|notes)\b",
        m,
    ):
        return ControlAction("export_memory")
    if re.search(r"\b(clear|wipe|delete|forget)\b.*\b(session)\b.*\b(memory|memories|notes)?\b", m):
        return ControlAction("clear_session")
    if re.search(r"\b(forget|delete|erase|wipe)\b.*\b(all|everything)\b.*\b(memory|memories|notes|data)\b", m) or re.search(
        r"\b(delete|erase)\b.*\b(my )?(data|account data|data for this chat)\b", m
    ):
        return ControlAction("forget_scope")

    # Session toggles (chat UX)
    if re.search(r"\b(turn on|enable|show)\b.*\b(trace|brain trace|debug)\b", m):
        return ControlAction("set_trace", "on")
    if re.search(r"\b(turn off|disable|hide)\b.*\b(trace|brain trace|debug)\b", m):
        return ControlAction("set_trace", "off")

    if re.search(r"\b(turn on|enable)\b.*\b(smart routing|auto routing|router)\b", m):
        return ControlAction("set_smart_route", "on")
    if re.search(r"\b(turn off|disable)\b.*\b(smart routing|auto routing|router)\b", m):
        return ControlAction("set_smart_route", "off")

    if re.search(r"\b(turn on|enable)\b.*\b(faq|rag|retrieval)\b", m):
        return ControlAction("set_rag", "on")
    if re.search(r"\b(turn off|disable)\b.*\b(faq|rag|retrieval)\b", m):
        return ControlAction("set_rag", "off")

    # Reply style for the generative model (short lines only to avoid hijacking real questions).
    if len(m) <= 140 and (
        re.search(r"\breset\b.*\b(reply |answer )?(style|format|length)\b", m)
        or re.search(r"\b(default|normal)\b.*\b(reply |answer )?(style|format)\b", m)
    ):
        return ControlAction("reset_reply_style")

    if len(m) <= 96 and re.search(
        r"\b(be brief|stay brief|keep it short|short answers|answer briefly|concise replies)\b",
        m,
    ):
        return ControlAction("set_verbosity", "brief")

    if len(m) <= 120 and re.search(
        r"\b(more detail|go deeper|in greater detail|explain thoroughly|longer answers|detailed answers)\b",
        m,
    ):
        return ControlAction("set_verbosity", "detailed")

    if len(m) <= 100 and re.search(
        r"\b(normal (answer )?length|default length|balanced length)\b",
        m,
    ):
        return ControlAction("set_verbosity", "normal")

    if len(m) <= 110 and re.search(r"\b(use|prefer)\b", m) and re.search(
        r"\b(bullet points?|numbered lists?)\b",
        m,
    ):
        return ControlAction("set_reply_format", "bullets")

    if len(m) <= 100 and re.search(
        r"\b(no bullets|plain paragraphs?|prose only|stop using lists)\b",
        m,
    ):
        return ControlAction("set_reply_format", "prose")

    # FAQ / RAG grounding hints for the assistant (short control lines).
    if len(m) <= 100 and re.search(
        r"\b(strict faq|faq only|stick to (the )?faq|only use (the )?faq|only trust (the )?faq)\b",
        m,
    ):
        return ControlAction("set_faq_grounding", "strict")

    if len(m) <= 115 and re.search(
        r"\b(balanced faq|normal faq|default faq(\s+grounding)?|default faq mode)\b",
        m,
    ):
        return ControlAction("set_faq_grounding", "normal")

    if len(m) <= 130 and re.search(
        r"\b(relaxed faq|faq plus general knowledge|general knowledge(\s+is)?\s+ok|mix faq and general knowledge)\b",
        m,
    ):
        return ControlAction("set_faq_grounding", "relaxed")

    return None

