/**
 * Reference fetch client for TinyModel encoder sidecar (copy to HSP ai/tinymodel.ts).
 */

import type {
  MetaTinyModel,
  PlanContext,
  PlanResponse,
  ServiceMeta,
} from "./tinymodel-types";

const DEFAULT_BASE = "http://127.0.0.1:8765";

export function tinymodelBaseUrl(): string {
  return (
    (typeof process !== "undefined" &&
      process.env?.TINYMODEL_API_URL?.trim()) ||
    DEFAULT_BASE
  ).replace(/\/$/, "");
}

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${tinymodelBaseUrl()}${path}`);
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`TinyModel ${path} ${res.status}: ${detail}`);
  }
  return (await res.json()) as T;
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${tinymodelBaseUrl()}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`TinyModel ${path} ${res.status}: ${detail}`);
  }
  return (await res.json()) as T;
}

export async function getServiceMeta(): Promise<ServiceMeta> {
  return getJson<ServiceMeta>("/v1/meta");
}

export async function classifyTexts(texts: string[]): Promise<Record<string, number>[]> {
  const data = await postJson<{ items: { label_scores: Record<string, number> }[] }>(
    "/v1/classify",
    { texts },
  );
  return data.items.map((item) => item.label_scores);
}

export async function retrieveCandidates(
  query: string,
  candidates: string[],
  topK = 3,
): Promise<{ index: number; text: string; score: number }[]> {
  const data = await postJson<{ hits: { index: number; text: string; score: number }[] }>(
    "/v1/retrieve",
    { query, candidates, top_k: topK },
  );
  return data.hits;
}

export async function planRequest(
  text: string,
  options?: {
    context?: PlanContext;
    candidates?: string[];
    topK?: number;
    minConfidence?: number;
    minMargin?: number;
  },
): Promise<PlanResponse> {
  return postJson<PlanResponse>("/v1/plan", {
    text,
    context: options?.context,
    candidates: options?.candidates ?? [],
    top_k: options?.topK ?? 2,
    min_confidence: options?.minConfidence ?? 0.55,
    min_margin: options?.minMargin ?? 0.1,
  });
}

export function buildMetaTinyModel(plan: PlanResponse, model: string): MetaTinyModel {
  const entries = Object.entries(plan.probs);
  const top =
    entries.length > 0
      ? entries.reduce((a, b) => (b[1] > a[1] ? b : a))[0]
      : plan.routing.label;
  const meta: MetaTinyModel = {
    model,
    intent: plan.intent,
    route_hint: plan.route_hint,
    actions: plan.actions,
    routing: plan.routing,
    retrieval: plan.retrieval,
    classify_top_label: top ?? null,
  };
  if (plan.context) {
    meta.context = plan.context;
  }
  return meta;
}
