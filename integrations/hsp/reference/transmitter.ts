/**
 * Reference ai/transmitter.ts for Hyperlinks Space Program.
 *
 * Replaces the legacy single OpenAI path with:
 *   1. TinyModel composeTurn (control plane)
 *   2. Vercel AI SDK streamText / generateText (generation — priority)
 *   3. Legacy OpenAI only when AI_PROVIDER=openai (migration)
 *
 * Copy to HSP and inject real `streamText` from `import { streamText } from "ai"`.
 */

import type { ComposerAvailability, ComposerRequest, ComposerTurnPlan } from "./composer-types";
import { composeTurn, defaultComposerConfig, templateForNavigate } from "./composer";
import type { TinyModelAction } from "./tinymodel-types";
import {
  buildVercelAiParams,
  generateWithVercelAi,
  isLegacyOpenAiConfigured,
  isVercelAiConfigured,
  resolveAiProvider,
  type AiProviderMode,
  type GenerateTextFn,
  type StreamTextFn,
} from "./vercel-ai-client";
import { TinyModelHealthCache } from "./availability";

export interface TransmitRequest extends ComposerRequest {
  threadContext?: { messages?: { role: string; content: string }[] };
}

export interface TransmitMeta {
  intent: string;
  generator: string;
  provider: AiProviderMode;
  availability: ComposerAvailability;
  plan_used: boolean;
  fallback_used?: string;
  model?: string;
  tinymodel?: ComposerTurnPlan["meta"]["tinymodel"];
  token_info?: Record<string, unknown>;
}

export interface TransmitResponse {
  ok: boolean;
  output_text: string;
  actions: TinyModelAction[];
  meta: TransmitMeta;
}

export interface TransmitterDeps {
  /** From `import { streamText } from "ai"` — required for hybrid / vercel_ai modes. */
  streamText?: StreamTextFn;
  generateText?: GenerateTextFn;
  /** Legacy HSP OpenAI transmit — only used when AI_PROVIDER=openai. */
  legacyOpenAiTransmit?: (req: TransmitRequest) => Promise<TransmitResponse>;
  /** Swap.Coffee token facts for token_info lane. */
  fetchTokenInfo?: (symbol: string) => Promise<Record<string, unknown> | null>;
  healthCache?: TinyModelHealthCache;
}

export async function resolveComposerAvailability(
  deps: TransmitterDeps = {},
): Promise<ComposerAvailability> {
  const cache = deps.healthCache ?? new TinyModelHealthCache();
  const tinymodel = await cache.isAvailable();
  const vercel_ai = isVercelAiConfigured();
  const openai_legacy = isLegacyOpenAiConfigured();
  return {
    tinymodel,
    vercel_ai: vercel_ai || openai_legacy,
    ub: false,
    swap_coffee: true,
  };
}

function metaFromTurn(turn: ComposerTurnPlan, provider: AiProviderMode): TransmitMeta {
  return {
    intent: turn.intent,
    generator: turn.generator,
    provider,
    availability: turn.meta.availability,
    plan_used: turn.meta.plan_used,
    fallback_used: turn.meta.fallback_used,
    model: turn.meta.model,
    tinymodel: turn.meta.tinymodel,
  };
}

async function executeVercelAiTurn(
  turn: ComposerTurnPlan,
  req: TransmitRequest,
  deps: TransmitterDeps,
  extraSystem?: string,
): Promise<string> {
  const params = buildVercelAiParams(turn, req.input, extraSystem);
  if (!params) {
    if (turn.outputTemplate) return turn.outputTemplate;
    if (turn.systemContext) return turn.systemContext.slice(0, 500);
    return "I couldn't generate a reply right now.";
  }
  if (deps.generateText) {
    return generateWithVercelAi(turn, req.input, deps.generateText, extraSystem);
  }
  if (deps.streamText) {
    const result = await deps.streamText(params);
    return result.text ?? "";
  }
  throw new Error("TransmitterDeps requires streamText or generateText from Vercel AI SDK");
}

async function executeSwapCoffeeHybrid(
  turn: ComposerTurnPlan,
  req: TransmitRequest,
  deps: TransmitterDeps,
): Promise<{ text: string; token_info?: Record<string, unknown> }> {
  const symbolMatch = req.input.match(/\$?([A-Za-z][A-Za-z0-9]{1,9})\b/);
  const symbol = symbolMatch?.[1]?.toUpperCase() ?? req.context?.selectedToken?.toUpperCase();
  let factsBlock = "";
  let token_info: Record<string, unknown> | undefined;
  if (symbol && deps.fetchTokenInfo) {
    token_info = (await deps.fetchTokenInfo(symbol)) ?? undefined;
    if (token_info) {
      factsBlock = `Token facts (Swap.Coffee, cite accurately):\n${JSON.stringify(token_info, null, 2)}`;
    }
  }
  if (!turn.meta.availability.vercel_ai) {
    return {
      text: factsBlock || "Token data is temporarily unavailable.",
      token_info,
    };
  }
  const text = await executeVercelAiTurn(turn, req, deps, factsBlock);
  return { text, token_info };
}

/**
 * Single-turn transmit — hybrid composer with Vercel AI priority.
 */
export async function transmit(
  req: TransmitRequest,
  deps: TransmitterDeps = {},
): Promise<TransmitResponse> {
  const provider = resolveAiProvider();

  if (provider === "openai") {
    if (!deps.legacyOpenAiTransmit) {
      throw new Error("AI_PROVIDER=openai requires legacyOpenAiTransmit adapter");
    }
    return deps.legacyOpenAiTransmit(req);
  }

  const avail = await resolveComposerAvailability(deps);
  const turn = await composeTurn(req, avail, defaultComposerConfig());

  if (turn.generator === "template") {
    const output_text =
      turn.outputTemplate ??
      (turn.intent === "navigate" ? templateForNavigate(turn.actions) : turn.systemContext.slice(0, 400));
    return {
      ok: true,
      output_text,
      actions: turn.actions,
      meta: metaFromTurn(turn, provider),
    };
  }

  if (turn.generator === "swap_coffee_hybrid") {
    const { text, token_info } = await executeSwapCoffeeHybrid(turn, req, deps);
    const meta = metaFromTurn(turn, provider);
    if (token_info) meta.token_info = token_info;
    return { ok: true, output_text: text, actions: turn.actions, meta };
  }

  if (turn.generator === "vercel_ai") {
    const output_text = await executeVercelAiTurn(turn, req, deps);
    return {
      ok: true,
      output_text,
      actions: turn.actions,
      meta: metaFromTurn(turn, provider),
    };
  }

  return {
    ok: true,
    output_text: turn.systemContext.slice(0, 500) || "Universal Brain path not configured.",
    actions: turn.actions,
    meta: { ...metaFromTurn(turn, provider), generator: "ub", fallback_used: "vercel_ai→ub" },
  };
}

/** Stream variant: yield meta + actions first, then token chunks (HSP /api/ai/stream). */
export async function* transmitStream(
  req: TransmitRequest,
  deps: TransmitterDeps = {},
): AsyncGenerator<
  | { type: "meta"; actions: TinyModelAction[]; meta: TransmitMeta }
  | { type: "text"; delta: string }
  | { type: "done"; output_text: string }
> {
  const provider = resolveAiProvider();

  if (provider === "openai" && deps.legacyOpenAiTransmit) {
    const legacy = await deps.legacyOpenAiTransmit(req);
    yield { type: "meta", actions: legacy.actions, meta: legacy.meta };
    yield { type: "text", delta: legacy.output_text };
    yield { type: "done", output_text: legacy.output_text };
    return;
  }

  const avail = await resolveComposerAvailability(deps);
  const turn = await composeTurn(req, avail, defaultComposerConfig());
  const meta = metaFromTurn(turn, provider);

  yield { type: "meta", actions: turn.actions, meta };

  if (turn.generator === "template") {
    const text =
      turn.outputTemplate ??
      (turn.intent === "navigate" ? templateForNavigate(turn.actions) : "");
    if (text) yield { type: "text", delta: text };
    yield { type: "done", output_text: text };
    return;
  }

  const params = buildVercelAiParams(turn, req.input);
  if (params && deps.streamText) {
    const result = await deps.streamText(params);
    if (result.textStream) {
      let full = "";
      for await (const delta of result.textStream) {
        full += delta;
        yield { type: "text", delta };
      }
      yield { type: "done", output_text: full };
      return;
    }
    const text = result.text ?? "";
    yield { type: "text", delta: text };
    yield { type: "done", output_text: text };
    return;
  }

  const fallback = await executeVercelAiTurn(turn, req, deps).catch(
    () => turn.outputTemplate ?? turn.systemContext.slice(0, 400),
  );
  yield { type: "text", delta: fallback };
  yield { type: "done", output_text: fallback };
}
