/**
 * Generator context assembly for hybrid transmitter (plan/07-ai-transmitter.md Step 5).
 */

import type { PlanContext, PlanResponse } from "./tinymodel-types";

export type AiRequestContext = {
  route?: string;
  locale?: string;
  walletConnected?: boolean;
};

export type AiRequestLike = {
  input: string;
  context?: AiRequestContext;
};

export function buildGeneratorContext(
  req: AiRequestLike,
  plan: PlanResponse | null,
): string {
  const parts: string[] = [];

  if (plan?.retrieval?.chunk_preview) {
    parts.push(
      `Help excerpt (cite when relevant):\n${plan.retrieval.chunk_preview}`,
    );
  }

  if (req.context?.route) {
    parts.push(`User is on app route: ${req.context.route}`);
  }

  if (req.context?.locale) {
    parts.push(`UI locale: ${req.context.locale}`);
  }

  if (req.context?.walletConnected === false) {
    parts.push("Wallet not connected; do not imply they can send yet.");
  }

  parts.push(
    "Safety: never ask for seed phrase or private keys; confirm sends on screen.",
  );

  return parts.join("\n\n");
}

/** Map HSP camelCase screen context to TinyModel plan context. */
export function toPlanContext(ctx?: AiRequestContext): PlanContext | undefined {
  if (!ctx) return undefined;
  const out: PlanContext = {};
  if (ctx.route) out.route = ctx.route;
  if (ctx.locale) out.locale = ctx.locale;
  if (ctx.walletConnected !== undefined) out.wallet_connected = ctx.walletConnected;
  return Object.keys(out).length > 0 ? out : undefined;
}
