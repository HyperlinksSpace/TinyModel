/** Types for HSP AI Composer (TinyModel plan → Vercel AI SDK routing). */

import type { MetaTinyModel, MetaTinyModelError, PlanIntent, PlanResponse, TinyModelAction } from "./tinymodel-types";

/** Full intent set after mode + plan + heuristics (plan/07-ai-transmitter.md). */
export type ResolvedIntent = PlanIntent | "token_info" | "swap_hint";

export type ComposerLane = "control" | "facts" | "grounded" | "soft";

export type ComposerGenerator = "template" | "vercel_ai" | "ub" | "swap_coffee_hybrid";

/** Mirrors Vercel AI Gateway providerOptions.gateway (AI SDK v4+). */
export interface GatewayRouteOptions {
  order?: string[];
  only?: string[];
  /** Fallback models when primary fails (creator/model format). */
  models?: string[];
  sort?: "cost" | "ttft";
}

/** Model selection for `generateText` / `streamText` from the `ai` package. */
export interface ComposerModelRoute {
  model: string;
  gateway?: GatewayRouteOptions;
  maxOutputTokens?: number;
  stream: boolean;
}

export interface ComposerConfig {
  /** Long-form chat, explain_screen, token narration. */
  qualityModel: string;
  /** Short acks, simple grounded replies. */
  fastModel: string;
  /** Navigate ack: "template" skips LLM entirely. */
  navigateAck: "template" | string;
  gatewayOrder: string[];
  gatewayFallbackModels: string[];
  /** When true, grounded lane prefers fastModel over qualityModel. */
  preferFastForGrounded: boolean;
  planTimeoutMs: number;
  /** Prefer Vercel AI SDK over legacy direct OpenAI (always true in hybrid mode). */
  preferVercelAi: boolean;
}

export type AiRequestMode = "chat" | "token_info" | null;

export interface ComposerRequestContext {
  route?: string;
  locale?: string;
  walletConnected?: boolean;
  selectedToken?: string;
}

export interface ComposerRequest {
  input: string;
  mode?: AiRequestMode;
  context?: ComposerRequestContext;
}

export interface ComposerAvailability {
  tinymodel: boolean;
  /** Vercel AI SDK + Gateway — primary generation path (priority over legacy OpenAI). */
  vercel_ai: boolean;
  ub: boolean;
  swap_coffee: boolean;
}

export interface ComposerTurnPlan {
  intent: ResolvedIntent;
  actions: TinyModelAction[];
  lane: ComposerLane;
  generator: ComposerGenerator;
  /** Set when generator is vercel_ai. */
  modelRoute?: ComposerModelRoute;
  systemContext: string;
  outputTemplate?: string;
  meta: {
    intent: ResolvedIntent;
    lane: ComposerLane;
    generator: ComposerGenerator;
    availability: ComposerAvailability;
    plan_used: boolean;
    fallback_used?: string;
    tinymodel?: MetaTinyModel | MetaTinyModelError;
    model?: string;
    gateway?: GatewayRouteOptions;
  };
}
