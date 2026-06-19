/**
 * Local fallback routing when TinyModel plan is unavailable (copy to HSP ai/).
 * Mirrors scripts/hsp_intent_router.py — keep in sync with golden hsp_intents.jsonl.
 */

import type { PlanIntent, TinyModelAction } from "./tinymodel-types";

export function inferHspRouteHint(text: string): string | null {
  const m = text.trim().toLowerCase();
  if (!m) return null;
  if (
    /\b(open|go to|show|navigate)\b.*\bswap\b/.test(m) ||
    /\bswap page\b/.test(m)
  ) {
    return "navigate:/swap";
  }
  if (/\b(send|transfer)\b/.test(m) && /\bton|jetton|token|wallet\b/.test(m)) {
    return "navigate:/send";
  }
  if (/\b(receive|wallet address|get wallet)\b/.test(m)) {
    return "navigate:/get";
  }
  if (/\b(connect telegram|telegram messages)\b/.test(m)) {
    return "feature:connect_telegram";
  }
  if (/\b(shield|security settings)\b/.test(m)) {
    return "feature:shield";
  }
  return null;
}

export function actionsFromRouteHint(routeHint: string | null): TinyModelAction[] {
  if (!routeHint) return [];
  if (routeHint.startsWith("navigate:")) {
    const path = routeHint.slice("navigate:".length).trim();
    if (path.startsWith("/")) return [{ type: "navigate", path }];
  }
  if (routeHint.startsWith("feature:")) {
    const id = routeHint.slice("feature:".length).trim();
    if (id) return [{ type: "feature", id }];
  }
  return [];
}

/** Heuristic intent when POST /v1/plan fails (plan/07-ai-transmitter.md Step 3). */
export function resolveFallbackIntent(text: string): PlanIntent {
  const hint = inferHspRouteHint(text);
  if (hint?.startsWith("navigate:") || hint?.startsWith("feature:")) {
    return "navigate";
  }
  return "chat";
}

export function fallbackPlanFromText(text: string): {
  intent: PlanIntent;
  route_hint: string | null;
  actions: TinyModelAction[];
} {
  const route_hint = inferHspRouteHint(text);
  return {
    intent: resolveFallbackIntent(text),
    route_hint,
    actions: actionsFromRouteHint(route_hint),
  };
}
