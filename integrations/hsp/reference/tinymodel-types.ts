/** Types for TinyModel Phase 3 reference API (HSP sidecar). */

export type TinyModelAction =
  | { type: "navigate"; path: string }
  | { type: "feature"; id: string };

export type PlanIntent = "navigate" | "explain_screen" | "chat";

export interface PlanContext {
  route?: string;
  locale?: string;
  wallet_connected?: boolean;
}

export interface PlanRouting {
  fallback: boolean;
  label: string | null;
  confidence: number;
  margin: number;
  reason: string;
}

export interface PlanRetrieval {
  top_idx: number;
  top_title: string;
  hybrid_score: number;
  keyword_overlap: number;
  chunk_preview: string;
  query_used?: string | null;
}

export interface PlanResponse {
  text: string;
  intent: PlanIntent;
  context?: PlanContext | null;
  route_hint: string | null;
  actions: TinyModelAction[];
  probs: Record<string, number>;
  routing: PlanRouting;
  retrieval: PlanRetrieval | null;
}

export interface ServiceCorpusMeta {
  source: string;
  version: string;
  chunk_count: number;
}

export interface ServiceMeta {
  service: string;
  api_version: string;
  model: string;
  corpus: ServiceCorpusMeta;
  endpoints: Record<string, string>;
}

export interface MetaTinyModel {
  model: string;
  intent?: PlanIntent | null;
  route_hint?: string | null;
  actions: TinyModelAction[];
  routing: PlanRouting;
  retrieval?: PlanRetrieval | null;
  classify_top_label?: string | null;
  context?: PlanContext;
}

/** Logged when POST /v1/plan fails (plan/07-ai-transmitter.md). */
export interface MetaTinyModelError {
  error: string;
  fallback?: string;
}
