"""Deterministic Hyperlinks Space Program intent hints (mirrors HSP ai/tinymodel.ts)."""

from __future__ import annotations

import re
from typing import Any


def infer_hsp_route_hint(text: str) -> str | None:
    """Return a route hint string or None when no navigational intent is detected."""
    m = text.strip().lower()
    if not m:
        return None
    if re.search(r"\b(open|go to|show|navigate)\b.*\bswap\b", m) or re.search(
        r"\bswap page\b", m
    ):
        return "navigate:/swap"
    if re.search(r"\b(send|transfer)\b", m) and re.search(
        r"\bton|jetton|token|wallet\b", m
    ):
        return "navigate:/send"
    if re.search(r"\b(receive|wallet address|get wallet)\b", m):
        return "navigate:/get"
    if re.search(r"\b(connect telegram|telegram messages)\b", m):
        return "feature:connect_telegram"
    if re.search(r"\b(shield|security settings)\b", m):
        return "feature:shield"
    return None


def actions_from_route_hint(route_hint: str | None) -> list[dict[str, str]]:
    """Map route hints to structured actions (same contract as HSP ai/intentActions.ts)."""
    if not route_hint:
        return []
    if route_hint.startswith("navigate:"):
        path = route_hint[len("navigate:") :].strip()
        if path.startswith("/"):
            return [{"type": "navigate", "path": path}]
    if route_hint.startswith("feature:"):
        feature_id = route_hint[len("feature:") :].strip()
        if feature_id:
            return [{"type": "feature", "id": feature_id}]
    return []


def score_hsp_intent_row(row: dict[str, Any]) -> tuple[bool, str, str | None]:
    """Score one golden row; returns (ok, detail, detected_route)."""
    prompt = str(row.get("prompt", ""))
    expect = row.get("expect_route")
    if expect is not None and not isinstance(expect, str):
        expect = str(expect)
    detected = infer_hsp_route_hint(prompt)
    if expect is None:
        ok = detected is None
        detail = "ok" if ok else f"unexpected route {detected!r}"
    else:
        ok = detected == expect
        detail = "ok" if ok else f"got {detected!r}, expected {expect!r}"
    return ok, detail, detected
