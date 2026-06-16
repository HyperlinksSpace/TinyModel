"""Map HSP /api/ai meta.tinymodel debug payloads (Phase 2 wiring contract)."""

from __future__ import annotations

from typing import Any


def classify_top_label(probs: dict[str, float]) -> str | None:
    if not probs:
        return None
    return max(probs.items(), key=lambda x: x[1])[0]


def build_meta_tinymodel(plan: dict[str, Any], model: str) -> dict[str, Any]:
    """Build meta.tinymodel from plan_hsp_request / POST /v1/plan response."""
    routing = plan.get("routing") or {}
    label = routing.get("label")
    probs = plan.get("probs") or {}
    if not label and isinstance(probs, dict):
        label = classify_top_label(probs)
    return {
        "model": model,
        "route_hint": plan.get("route_hint"),
        "actions": list(plan.get("actions") or []),
        "routing": routing,
        "retrieval": plan.get("retrieval"),
        "classify_top_label": label,
    }


def validate_meta_tinymodel(meta: Any) -> None:
    """Validate meta.tinymodel object shape (stdlib, no torch)."""
    if not isinstance(meta, dict):
        raise ValueError("meta.tinymodel must be object")
    model = meta.get("model")
    if not isinstance(model, str) or not model.strip():
        raise ValueError("meta.tinymodel.model must be non-empty string")
    route_hint = meta.get("route_hint")
    if route_hint is not None and not isinstance(route_hint, str):
        raise ValueError("meta.tinymodel.route_hint must be string or null")
    actions = meta.get("actions")
    if not isinstance(actions, list):
        raise ValueError("meta.tinymodel.actions must be list")
    for action in actions:
        if not isinstance(action, dict) or not isinstance(action.get("type"), str):
            raise ValueError("meta.tinymodel action must be object with string type")
    routing = meta.get("routing")
    if not isinstance(routing, dict):
        raise ValueError("meta.tinymodel.routing must be object")
    if not isinstance(routing.get("fallback"), bool):
        raise ValueError("meta.tinymodel.routing.fallback must be bool")
    if routing.get("label") is not None and not isinstance(routing.get("label"), str):
        raise ValueError("meta.tinymodel.routing.label must be string or null")
    for key in ("confidence", "margin"):
        if not isinstance(routing.get(key), (int, float)):
            raise ValueError(f"meta.tinymodel.routing.{key} must be number")
    if not isinstance(routing.get("reason"), str):
        raise ValueError("meta.tinymodel.routing.reason must be string")
    top_label = meta.get("classify_top_label")
    if top_label is not None and not isinstance(top_label, str):
        raise ValueError("meta.tinymodel.classify_top_label must be string or null")
    retrieval = meta.get("retrieval")
    if retrieval is not None:
        if not isinstance(retrieval, dict):
            raise ValueError("meta.tinymodel.retrieval must be object or null")
        if not isinstance(retrieval.get("top_title"), str):
            raise ValueError("meta.tinymodel.retrieval.top_title must be string")
