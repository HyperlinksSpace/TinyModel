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

    return None

