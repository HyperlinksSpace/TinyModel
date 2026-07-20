/**
 * Vercel AI SDK wiring for the HSP composer (copy to ai/vercel-ai-client.ts).
 *
 * Priority: all LLM generation goes through the `ai` package + AI Gateway model strings
 * (e.g. openai/gpt-4.1-mini), not direct OpenAI SDK calls — same role OpenAI had in
 * legacy ai/transmitter.ts, but unified via Vercel AI.
 */

import type { ComposerModelRoute, ComposerTurnPlan, GatewayRouteOptions } from "./composer-types";

/** Params passed to `streamText` / `generateText` from the `ai` package. */
export interface VercelAiCallParams {
  model: string;
  system: string;
  prompt: string;
  maxOutputTokens?: number;
  providerOptions?: {
    gateway?: GatewayRouteOptions;
  };
}

/** Minimal shape of streamText result (HSP imports real type from `ai`). */
export interface VercelAiTextResult {
  text: string;
}

export type StreamTextFn = (
  params: VercelAiCallParams,
) => Promise<VercelAiTextResult & { textStream?: AsyncIterable<string> }>;

export type GenerateTextFn = (params: VercelAiCallParams) => Promise<VercelAiTextResult>;

export type AiProviderMode = "hybrid" | "vercel_ai" | "openai";

const LEGACY_OPENAI = "openai";

/**
 * Resolve server provider mode.
 * - hybrid (default): TinyModel plan + Vercel AI generation (priority)
 * - vercel_ai: plan optional + Vercel AI only
 * - openai: legacy direct OpenAI path (migrate off this)
 */
export function resolveAiProvider(): AiProviderMode {
  const raw = (
    typeof process !== "undefined" ? process.env?.AI_PROVIDER?.trim().toLowerCase() : ""
  ) || "hybrid";
  if (raw === LEGACY_OPENAI) return LEGACY_OPENAI;
  if (raw === "vercel_ai" || raw === "vercel") return "vercel_ai";
  return "hybrid";
}

/** True when Vercel AI Gateway / AI SDK can run (Vercel OIDC or explicit gateway key). */
export function isVercelAiConfigured(): boolean {
  if (typeof process === "undefined") return false;
  const env = process.env;
  if (env.AI_GATEWAY_API_KEY?.trim()) return true;
  if (env.VERCEL === "1" || env.VERCEL_ENV) return true;
  if (env.AI_SDK_DEFAULT_PROVIDER?.trim()) return true;
  return false;
}

/** Legacy OpenAI direct SDK — only when explicitly enabled for migration window. */
export function isLegacyOpenAiConfigured(): boolean {
  if (typeof process === "undefined") return false;
  return Boolean(process.env.OPENAI_API_KEY?.trim());
}

export function buildVercelAiParams(
  turn: ComposerTurnPlan,
  userPrompt: string,
  extraSystem?: string,
): VercelAiCallParams | null {
  if (!turn.modelRoute) return null;
  const system = extraSystem
    ? `${turn.systemContext}\n\n${extraSystem}`.trim()
    : turn.systemContext;
  return {
    model: turn.modelRoute.model,
    system,
    prompt: userPrompt,
    maxOutputTokens: turn.modelRoute.maxOutputTokens,
    providerOptions: turn.modelRoute.gateway
      ? { gateway: turn.modelRoute.gateway }
      : undefined,
  };
}

/** Execute non-streaming generation via injected AI SDK adapter. */
export async function generateWithVercelAi(
  turn: ComposerTurnPlan,
  userPrompt: string,
  generateText: GenerateTextFn,
  extraSystem?: string,
): Promise<string> {
  const params = buildVercelAiParams(turn, userPrompt, extraSystem);
  if (!params) {
    throw new Error("composer turn has no modelRoute for vercel_ai");
  }
  const result = await generateText(params);
  return result.text;
}

/** Map ComposerModelRoute to plain object for logging / meta. */
export function modelRouteMeta(route: ComposerModelRoute | undefined): {
  model?: string;
  gateway?: GatewayRouteOptions;
  stream?: boolean;
} {
  if (!route) return {};
  return {
    model: route.model,
    gateway: route.gateway,
    stream: route.stream,
  };
}
