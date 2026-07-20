"""AI Composer routing (stdlib mirror of integrations/hsp/reference/composer.ts)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

from hsp_intent_router import actions_from_route_hint, infer_hsp_route_hint

ResolvedIntent = Literal["navigate", "explain_screen", "chat", "token_info", "swap_hint"]
ComposerLane = Literal["control", "facts", "grounded", "soft"]
ComposerGenerator = Literal["template", "vercel_ai", "ub", "swap_coffee_hybrid"]

_TOKEN_SYMBOL = re.compile(r"\$([A-Za-z][A-Za-z0-9]{1,9})\b")
_SOFT = re.compile(r"\b(summarize|summary|rephrase|reformulate|shorter|brief version)\b", re.I)


@dataclass(frozen=True)
class ComposerConfig:
    quality_model: str = "openai/gpt-4.1-mini"
    fast_model: str = "openai/gpt-4.1-nano"
    navigate_ack: str = "template"
    gateway_order: tuple[str, ...] = ("openai", "anthropic", "google")
    gateway_fallback_models: tuple[str, ...] = (
        "google/gemini-2.0-flash",
        "anthropic/claude-3-5-haiku-latest",
    )
    prefer_fast_for_grounded: bool = False


@dataclass(frozen=True)
class ComposerAvailability:
    tinymodel: bool = True
    vercel_ai: bool = True
    ub: bool = False
    swap_coffee: bool = True


@dataclass
class ComposerModelRoute:
    model: str
    stream: bool = True
    max_output_tokens: int = 1200
    gateway_order: tuple[str, ...] | None = None
    gateway_models: tuple[str, ...] | None = None


@dataclass
class ComposerTurnPlan:
    intent: ResolvedIntent
    lane: ComposerLane
    generator: ComposerGenerator
    actions: list[dict[str, str]]
    model: str | None = None
    output_template: str | None = None


def detect_token_symbol(text: str) -> str | None:
    m = _TOKEN_SYMBOL.search(text)
    if m:
        return m.group(1).upper()
    lower = text.lower()
    if re.search(r"\b(usdt|ton|not|btc|eth)\b", lower) and re.search(
        r"\b(price|holders|market|cap|token)\b", lower
    ):
        hit = re.search(r"\b(usdt|ton|not|btc|eth)\b", lower)
        return hit.group(1).upper() if hit else None
    return None


def detect_token_info_intent(text: str, mode: str | None = None) -> bool:
    if mode == "token_info":
        return True
    if detect_token_symbol(text):
        return True
    return bool(
        re.search(r"\b(price|holders|market cap|fdv|verified)\b", text, re.I)
        and re.search(r"\b(token|jetton|coin)\b", text, re.I)
    )


def detect_soft_intent(text: str) -> bool:
    return bool(_SOFT.search(text))


def resolve_intent(
    text: str,
    mode: str | None,
    plan: dict[str, Any] | None,
) -> ResolvedIntent:
    if detect_token_info_intent(text, mode):
        return "token_info"
    if plan and isinstance(plan.get("intent"), str):
        pi = plan["intent"]
        if pi in ("navigate", "explain_screen", "chat"):
            if pi != "chat":
                return pi  # type: ignore[return-value]
    if re.search(r"\b(swap|exchange)\b", text, re.I) and re.search(
        r"\b\d+\s*(ton|usdt|jetton)\b", text, re.I
    ):
        return "swap_hint"
    hint = infer_hsp_route_hint(text)
    if hint:
        return "navigate"
    if plan and plan.get("intent") == "chat":
        return "chat"
    return "chat"


def _gateway(config: ComposerConfig) -> tuple[str, ...]:
    return config.gateway_order


def pick_model_route(
    lane: ComposerLane,
    config: ComposerConfig,
    avail: ComposerAvailability,
) -> ComposerModelRoute | None:
    if not avail.vercel_ai:
        return None
    gw = _gateway(config)
    fallbacks = config.gateway_fallback_models
    if lane == "control" and config.navigate_ack != "template":
        return ComposerModelRoute(
            model=config.navigate_ack,
            max_output_tokens=120,
            gateway_order=gw,
            gateway_models=fallbacks,
        )
    if lane == "facts":
        return ComposerModelRoute(
            model=config.quality_model,
            max_output_tokens=800,
            gateway_order=gw,
            gateway_models=fallbacks,
        )
    if lane == "soft":
        return ComposerModelRoute(
            model=config.fast_model,
            max_output_tokens=600,
            gateway_order=gw,
            gateway_models=fallbacks,
        )
    model = config.fast_model if config.prefer_fast_for_grounded else config.quality_model
    return ComposerModelRoute(
        model=model,
        max_output_tokens=1200,
        gateway_order=gw,
        gateway_models=fallbacks,
    )


def resolve_lane_and_generator(
    intent: ResolvedIntent,
    text: str,
    config: ComposerConfig,
    avail: ComposerAvailability,
) -> tuple[ComposerLane, ComposerGenerator, ComposerModelRoute | None]:
    if intent == "navigate":
        if config.navigate_ack == "template" or not avail.vercel_ai:
            return "control", "template", None
        route = pick_model_route("control", config, avail)
        return "control", "vercel_ai", route

    if intent == "token_info":
        if avail.swap_coffee and avail.vercel_ai:
            return "facts", "swap_coffee_hybrid", pick_model_route("facts", config, avail)
        if avail.vercel_ai:
            return "facts", "vercel_ai", pick_model_route("facts", config, avail)
        return "facts", "template", None

    if intent in ("swap_hint", "explain_screen"):
        if avail.vercel_ai:
            return "grounded", "vercel_ai", pick_model_route("grounded", config, avail)
        if avail.ub:
            return "grounded", "ub", None
        return "grounded", "template", None

    if intent == "chat" and detect_soft_intent(text):
        if avail.ub and not avail.vercel_ai:
            return "soft", "ub", None
        if avail.vercel_ai:
            return "soft", "vercel_ai", pick_model_route("soft", config, avail)
        return "soft", "template", None

    if avail.vercel_ai:
        return "grounded", "vercel_ai", pick_model_route("grounded", config, avail)
    if avail.ub:
        return "grounded", "ub", None
    return "grounded", "template", None


def template_for_navigate(actions: list[dict[str, str]]) -> str:
    for action in actions:
        if action.get("type") == "navigate" and action.get("path", "").startswith("/"):
            label = action["path"].lstrip("/").replace("-", " ") or "that screen"
            return f"Opening {label}…"
        if action.get("type") == "feature" and action.get("id"):
            return f"Opening {action['id'].replace('_', ' ')}…"
    return "Done."


def compose_turn_plan(
    text: str,
    *,
    mode: str | None = None,
    plan: dict[str, Any] | None = None,
    config: ComposerConfig | None = None,
    avail: ComposerAvailability | None = None,
) -> ComposerTurnPlan:
    cfg = config or ComposerConfig()
    availability = avail or ComposerAvailability()
    intent = resolve_intent(text, mode, plan)
    actions = list(plan.get("actions") or []) if plan else actions_from_route_hint(infer_hsp_route_hint(text))
    lane, generator, route = resolve_lane_and_generator(intent, text, cfg, availability)
    output_template = None
    if generator == "template" and intent == "navigate":
        output_template = template_for_navigate(actions)
    return ComposerTurnPlan(
        intent=intent,
        lane=lane,
        generator=generator,
        actions=actions,
        model=route.model if route else None,
        output_template=output_template,
    )
