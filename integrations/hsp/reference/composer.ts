/**
 * AI Composer — TinyModel plan + intent → Vercel AI SDK model route (reference).
 * Copy to HSP `ai/composer.ts`; wire with `ai` package generateText/streamText.
 *
 * Does not call Vercel or OpenAI directly (no API keys in TinyModel repo).
 */

import { buildGeneratorContext, type AiRequestLike } from "./build-context";
import { fallbackPlanFromText } from "./fallback-router";
import type {
  ComposerAvailability,
  ComposerConfig,
  ComposerGenerator,
  ComposerLane,
  ComposerModelRoute,
  ComposerRequest,
  ComposerTurnPlan,
  GatewayRouteOptions,
  ResolvedIntent,
} from "./composer-types";
import { buildMetaTinyModel, buildMetaTinyModelError, planRequest } from "./tinymodel-client";
import type { PlanResponse } from "./tinymodel-types";

const DEFAULT_QUALITY = "openai/gpt-4.1-mini";
const DEFAULT_FAST = "openai/gpt-4.1-nano";
const DEFAULT_GATEWAY_ORDER = ["openai", "anthropic", "google"];
const DEFAULT_GATEWAY_FALLBACKS = ["google/gemini-2.0-flash", "anthropic/claude-3-5-haiku-latest"];

export function defaultComposerConfig(): ComposerConfig {
  const env = typeof process !== "undefined" ? process.env : undefined;
  const navigateRaw = env?.AI_COMPOSER_NAVIGATE_ACK?.trim() || "template";
  return {
    qualityModel: env?.AI_COMPOSER_QUALITY_MODEL?.trim() || DEFAULT_QUALITY,
    fastModel: env?.AI_COMPOSER_FAST_MODEL?.trim() || DEFAULT_FAST,
    navigateAck: navigateRaw === "template" ? "template" : navigateRaw,
    gatewayOrder: (env?.AI_GATEWAY_ORDER || DEFAULT_GATEWAY_ORDER.join(","))
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean),
    gatewayFallbackModels: (env?.AI_GATEWAY_FALLBACK_MODELS || DEFAULT_GATEWAY_FALLBACKS.join(","))
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean),
    preferFastForGrounded: env?.AI_COMPOSER_PREFER_FAST_GROUNDED === "true",
    planTimeoutMs: Number(env?.TINYMODEL_PLAN_TIMEOUT_MS || "8000"),
    preferVercelAi: env?.AI_PROVIDER?.trim().toLowerCase() !== "openai",
  };
}

export function detectTokenSymbol(text: string): string | null {
  const m = text.match(/\$([A-Za-z][A-Za-z0-9]{1,9})\b/);
  if (m) return m[1].toUpperCase();
  const words = text.toLowerCase();
  if (/\b(usdt|ton|not|btc|eth)\b/.test(words) && /\b(price|holders|market|cap|token)\b/.test(words)) {
    const hit = words.match(/\b(usdt|ton|not|btc|eth)\b/);
    return hit ? hit[1].toUpperCase() : null;
  }
  return null;
}

export function detectTokenInfoIntent(text: string, mode?: ComposerRequest["mode"]): boolean {
  if (mode === "token_info") return true;
  if (detectTokenSymbol(text)) return true;
  return /\b(price|holders|market cap|fdv|verified)\b/i.test(text) && /\b(token|jetton|coin)\b/i.test(text);
}

export function detectSoftIntent(text: string): boolean {
  return /\b(summarize|summary|rephrase|reformulate|shorter|brief version)\b/i.test(text);
}

export function resolveIntent(
  input: string,
  mode: ComposerRequest["mode"],
  plan: PlanResponse | null,
): ResolvedIntent {
  if (mode === "token_info" || detectTokenInfoIntent(input, mode)) {
    return "token_info";
  }
  if (plan?.intent) {
    if (plan.intent === "navigate" || plan.intent === "explain_screen") {
      return plan.intent;
    }
  }
  if (/\b(swap|exchange)\b/i.test(input) && /\b\d+\s*(ton|usdt|jetton)\b/i.test(input)) {
    return "swap_hint";
  }
  const fb = fallbackPlanFromText(input);
  if (fb.intent === "navigate") return "navigate";
  return plan?.intent ?? "chat";
}

export function buildGatewayOptions(config: ComposerConfig): GatewayRouteOptions {
  return {
    order: config.gatewayOrder,
    models: config.gatewayFallbackModels,
  };
}

export function pickModelRoute(
  intent: ResolvedIntent,
  lane: ComposerLane,
  config: ComposerConfig,
  avail: ComposerAvailability,
): ComposerModelRoute | undefined {
  if (!avail.vercel_ai) return undefined;
  const gateway = buildGatewayOptions(config);
  if (lane === "control" && config.navigateAck !== "template") {
    return { model: config.navigateAck, gateway, maxOutputTokens: 120, stream: true };
  }
  if (lane === "facts") {
    return { model: config.qualityModel, gateway, maxOutputTokens: 800, stream: true };
  }
  if (lane === "soft") {
    return { model: config.fastModel, gateway, maxOutputTokens: 600, stream: true };
  }
  const model = config.preferFastForGrounded ? config.fastModel : config.qualityModel;
  return { model, gateway, maxOutputTokens: 1200, stream: true };
}

export function pickLaneAndGenerator(
  intent: ResolvedIntent,
  config: ComposerConfig,
  avail: ComposerAvailability,
): { lane: ComposerLane; generator: ComposerGenerator; modelRoute?: ComposerModelRoute } {
  if (intent === "navigate") {
    if (config.navigateAck === "template" || !avail.vercel_ai) {
      return { lane: "control", generator: "template" };
    }
    return {
      lane: "control",
      generator: "vercel_ai",
      modelRoute: pickModelRoute(intent, "control", config, avail),
    };
  }
  if (intent === "token_info") {
    if (!avail.swap_coffee) {
      return avail.vercel_ai
        ? {
            lane: "facts",
            generator: "vercel_ai",
            modelRoute: pickModelRoute(intent, "facts", config, avail),
          }
        : { lane: "facts", generator: "template" };
    }
    if (avail.vercel_ai) {
      return {
        lane: "facts",
        generator: "swap_coffee_hybrid",
        modelRoute: pickModelRoute(intent, "facts", config, avail),
      };
    }
    return { lane: "facts", generator: "template" };
  }
  if (intent === "swap_hint") {
    if (avail.vercel_ai) {
      return {
        lane: "grounded",
        generator: "vercel_ai",
        modelRoute: pickModelRoute(intent, "grounded", config, avail),
      };
    }
    if (avail.ub) return { lane: "grounded", generator: "ub" };
    return { lane: "grounded", generator: "template" };
  }
  if (intent === "explain_screen") {
    if (avail.vercel_ai) {
      return {
        lane: "grounded",
        generator: "vercel_ai",
        modelRoute: pickModelRoute(intent, "grounded", config, avail),
      };
    }
    if (avail.ub) return { lane: "grounded", generator: "ub" };
    return { lane: "grounded", generator: "template" };
  }
  if (avail.vercel_ai) {
    return {
      lane: "grounded",
      generator: "vercel_ai",
      modelRoute: pickModelRoute(intent, "grounded", config, avail),
    };
  }
  if (avail.ub) return { lane: "grounded", generator: "ub" };
  return { lane: "grounded", generator: "template" };
}

export function resolveLaneForInput(
  intent: ResolvedIntent,
  input: string,
  config: ComposerConfig,
  avail: ComposerAvailability,
): { lane: ComposerLane; generator: ComposerGenerator; modelRoute?: ComposerModelRoute } {
  if (intent === "chat" && detectSoftIntent(input)) {
    if (avail.ub && !avail.vercel_ai) {
      return { lane: "soft", generator: "ub" };
    }
    if (avail.vercel_ai) {
      return {
        lane: "soft",
        generator: "vercel_ai",
        modelRoute: pickModelRoute(intent, "soft", config, avail),
      };
    }
    return { lane: "soft", generator: "template" };
  }
  return pickLaneAndGenerator(intent, config, avail);
}

export function templateForNavigate(actions: ComposerTurnPlan["actions"]): string {
  const nav = actions.find((a) => a.type === "navigate");
  if (nav && nav.type === "navigate") {
    const label = nav.path.replace(/^\//, "").replace(/-/g, " ") || "that screen";
    return `Opening ${label}…`;
  }
  const feat = actions.find((a) => a.type === "feature");
  if (feat && feat.type === "feature") {
    return `Opening ${feat.id.replace(/_/g, " ")}…`;
  }
  return "Done.";
}

export async function fetchPlanWithFallback(
  req: ComposerRequest,
  avail: ComposerAvailability,
  config: ComposerConfig,
): Promise<{ plan: PlanResponse | null; planUsed: boolean; fallbackUsed?: string }> {
  if (!avail.tinymodel) {
    return { plan: null, planUsed: false, fallbackUsed: "plan→heuristic" };
  }
  try {
    const plan = await planRequest(req.input, {
      context: req.context
        ? {
            route: req.context.route,
            locale: req.context.locale,
            wallet_connected: req.context.walletConnected,
          }
        : undefined,
    });
    return { plan, planUsed: true };
  } catch {
    return { plan: null, planUsed: false, fallbackUsed: "plan→heuristic" };
  }
}

/** Compose one turn: plan + lane + Vercel AI model route (no generation). */
export async function composeTurn(
  req: ComposerRequest,
  avail: ComposerAvailability,
  config: ComposerConfig = defaultComposerConfig(),
  options?: { plan?: PlanResponse | null; planUsed?: boolean; fallbackUsed?: string },
): Promise<ComposerTurnPlan> {
  let plan: PlanResponse | null = options?.plan ?? null;
  let planUsed = options?.planUsed ?? Boolean(plan);
  let fallbackUsed = options?.fallbackUsed;

  if (options?.plan === undefined) {
    const fetched = await fetchPlanWithFallback(req, avail, config);
    plan = fetched.plan;
    planUsed = fetched.planUsed;
    fallbackUsed = fetched.fallbackUsed;
  }

  const intent = resolveIntent(req.input, req.mode ?? null, plan);
  const actions = plan?.actions?.length
    ? plan.actions
    : fallbackPlanFromText(req.input).actions;

  const { lane, generator, modelRoute } = resolveLaneForInput(intent, req.input, config, avail);

  const ctxReq: AiRequestLike = {
    input: req.input,
    context: req.context,
  };
  const systemContext = buildGeneratorContext(ctxReq, plan);

  const tinymodelMeta = plan
    ? buildMetaTinyModel(plan, "HyperlinksSpace/TinyModel1")
    : buildMetaTinyModelError("plan_unavailable", { fallback: fallbackUsed });

  const turn: ComposerTurnPlan = {
    intent,
    actions,
    lane,
    generator,
    modelRoute,
    systemContext,
    meta: {
      intent,
      lane,
      generator,
      availability: avail,
      plan_used: planUsed,
      fallback_used: fallbackUsed,
      tinymodel: tinymodelMeta,
      model: modelRoute?.model,
      gateway: modelRoute?.gateway,
    },
  };

  if (generator === "template" && intent === "navigate") {
    turn.outputTemplate = templateForNavigate(actions);
  }

  return turn;
}
