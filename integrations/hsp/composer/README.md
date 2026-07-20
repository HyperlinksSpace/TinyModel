# HSP AI Composer — plan and reference

**Role:** TinyModel acts as a **composer** in Hyperlinks Space Program: it **plans** each user turn (intent, `actions[]`, RAG), then **routes generation** across backends—including **multiple models via the Vercel AI SDK and AI Gateway**—without the mobile client choosing providers.

**Status (TinyModel repo):** reference implementation + stdlib verify gates. **HSP wiring:** not started (copy modules when ready).

**Related:** [`plan/07-ai-transmitter.md`](../../../plan/07-ai-transmitter.md) · [`../reference/composer.ts`](../reference/composer.ts) · [`texts/tinymodel-functionality-scope-and-roadmap.md`](../../../texts/tinymodel-functionality-scope-and-roadmap.md)

---

## 1. Problem

HSP today uses a single OpenAI path in `ai/transmitter.ts`. Production needs:

| Need | Why one model is not enough |
| ---- | --------------------------- |
| **Navigate** | No LLM required—template ack + `actions[]` |
| **Token facts** | Swap.Coffee for data + small LLM for narration |
| **Explain screen** | Grounded RAG + quality model |
| **Summarize / soft chat** | Cheaper or alternate model |
| **Resilience** | Gateway fallbacks when a provider is down |

The **composer** sits between `/api/ai` and generators: **TinyModel sidecar decides structure**; **Vercel AI SDK executes text generation** with per-turn model selection.

---

## 2. Architecture

```text
User (GlobalBottomBar / chat)
    → HSP POST /api/ai
        → composeTurn()                    ← ai/composer.ts (this reference)
            1. POST tinymodel.hyperlinks.space/v1/plan
            2. resolveIntent(mode, plan, heuristics)
            3. pick lane + generator + modelRoute
        → execute generator:
            • template          — navigate ack, no API call
            • swap_coffee_hybrid — facts + streamText
            • vercel_ai         — streamText / generateText (AI SDK)
            • ub                — optional Universal Brain HTTP
    ← { output_text, actions[], meta }
    → client applyAiActions()
```

### Two-layer routing

| Layer | Owner | Output |
| ----- | ----- | ------ |
| **Control plane** | TinyModel sidecar (`/v1/plan`) | `intent`, `actions[]`, `retrieval`, `route_hint` |
| **Generation plane** | Composer + Vercel AI SDK | `model`, `gateway` fallbacks, `stream`, token limits |

TinyModel **does not** replace Vercel AI—it **directs** which model(s) Vercel AI calls for each turn.

---

## 3. Composer lanes

| Lane | Intents | Generator | Vercel model typical |
| ---- | ------- | --------- | -------------------- |
| **control** | `navigate` | `template` or `vercel_ai` (short ack) | `fast` or skip LLM |
| **facts** | `token_info` | `swap_coffee_hybrid` | `quality` for narration |
| **grounded** | `explain_screen`, `chat`, `swap_hint` | `vercel_ai` or `ub` | `quality` or `fast` |
| **soft** | summarize / rephrase | `vercel_ai` or `ub` | `fast` |

Resolved intents (after mode + plan + heuristics):

`navigate` · `explain_screen` · `chat` · `token_info` · `swap_hint`

---

## 4. Vercel AI integration (priority over legacy OpenAI)

HSP today calls OpenAI directly in `ai/transmitter.ts`. The composer **replaces that path** with the [Vercel AI SDK](https://sdk.vercel.ai) + [AI Gateway](https://vercel.com/docs/ai-gateway/models-and-providers) — same reply quality tier, but multi-model fallbacks and unified observability on Vercel.

### Provider modes

| `AI_PROVIDER` | Behavior |
| ------------- | -------- |
| **`hybrid`** (default) | TinyModel `composeTurn` + **Vercel AI `streamText`** (priority) |
| **`vercel_ai`** | Skip optional plan tuning; Vercel AI generation only |
| **`openai`** | Legacy: existing OpenAI transmitter (migration only — remove after cutover) |

### Reference modules (copy to HSP)

| TinyModel | HSP | Role |
| --------- | --- | ---- |
| `reference/transmitter.ts` | `ai/transmitter.ts` | Drop-in replacement for OpenAI-only transmit |
| `reference/vercel-ai-client.ts` | `ai/vercel-ai-client.ts` | Build AI SDK params from composer turn |
| `reference/composer.ts` | `ai/composer.ts` | Plan + lane + model route |

### Wire in HSP (same slot as OpenAI today)

```typescript
import { streamText } from "ai";
import { transmit, transmitStream } from "./transmitter";

// In /api/ai handler — inject real streamText from `ai` package:
const response = await transmit(request, {
  streamText: (params) =>
    streamText({
      model: params.model,
      system: params.system,
      prompt: params.prompt,
      maxOutputTokens: params.maxOutputTokens,
      providerOptions: params.providerOptions,
    }),
  fetchTokenInfo: existingSwapCoffeeFn,
  legacyOpenAiTransmit: oldTransmit, // only if AI_PROVIDER=openai
});
```

Install deps: see [`../reference/package.reference.json`](../reference/package.reference.json).

```bash
npm install ai
# Gateway model strings work on Vercel without @ai-sdk/openai
```

### Per-turn generation (after `composeTurn`)

```typescript
import { streamText } from "ai";
import { transmit } from "./transmitter";

const response = await transmit(request, {
  streamText: (params) =>
    streamText({
      model: params.model,
      system: params.system,
      prompt: params.prompt,
      maxOutputTokens: params.maxOutputTokens,
      providerOptions: params.providerOptions,
    }),
});
// response: { output_text, actions[], meta: { provider: "hybrid", generator: "vercel_ai", ... } }
```

### AI Gateway fallbacks

Use [Vercel AI Gateway](https://vercel.com/docs/ai-gateway/models-and-providers) so one `model` string can cascade across providers:

```typescript
providerOptions: {
  gateway: {
    order: ["openai", "anthropic", "google"],
    models: ["google/gemini-2.0-flash", "anthropic/claude-3-5-haiku-latest"],
    sort: "cost", // optional: "ttft" for latency
  },
}
```

Composer defaults (override via env):

| Env | Default | Purpose |
| --- | ------- | ------- |
| **`AI_PROVIDER`** | **`hybrid`** | **`hybrid` = plan + Vercel AI (priority)**; `openai` = legacy only |
| `AI_COMPOSER_QUALITY_MODEL` | `openai/gpt-4.1-mini` | Grounded chat, token narration |
| `AI_COMPOSER_FAST_MODEL` | `openai/gpt-4.1-nano` | Soft tasks, optional grounded |
| `AI_COMPOSER_NAVIGATE_ACK` | `template` | Skip LLM for navigate (`template` or model id) |
| `AI_GATEWAY_ORDER` | `openai,anthropic,google` | Provider try order |
| `AI_GATEWAY_FALLBACK_MODELS` | `google/gemini-2.0-flash,...` | Model fallback chain |
| `AI_COMPOSER_PREFER_FAST_GROUNDED` | `false` | Cost vs quality for explain/chat |
| `TINYMODEL_API_URL` | `https://tinymodel.hyperlinks.space` | Control plane |
| `TINYMODEL_PLAN_TIMEOUT_MS` | `8000` | Plan timeout |

On Vercel, AI Gateway auth is automatic when using the AI SDK with gateway model ids (`creator/model-name`).

---

## 5. Reference modules (copy to HSP)

| TinyModel path | HSP target |
| -------------- | ---------- |
| `integrations/hsp/reference/composer.ts` | `ai/composer.ts` |
| `integrations/hsp/reference/composer-types.ts` | `ai/composer-types.ts` |
| `integrations/hsp/reference/vercel-ai-client.ts` | `ai/vercel-ai-client.ts` |
| `integrations/hsp/reference/transmitter.ts` | `ai/transmitter.ts` |
| `integrations/hsp/reference/tinymodel-client.ts` | `ai/tinymodel.ts` |
| `integrations/hsp/reference/fallback-router.ts` | `ai/fallback-router.ts` |
| `integrations/hsp/reference/availability.ts` | `ai/availability.ts` |
| `integrations/hsp/reference/build-context.ts` | `ai/build-context.ts` |

**Main API:** `composeTurn(req, availability, config?)` → `ComposerTurnPlan` (no network except optional `planRequest` inside).

---

## 6. TinyModel-side deliverables (done in this repo)

| Item | Location |
| ---- | -------- |
| Composer reference (TS) | `integrations/hsp/reference/composer.ts` |
| Types | `integrations/hsp/reference/composer-types.ts` |
| Python mirror (stdlib tests) | `scripts/hsp_composer_lib.py` |
| Golden routing cases | `texts/golden-prompts/hsp_composer_routes.jsonl` |
| Verify gate | `python scripts/hsp_composer_smoke.py --verify` |
| Vercel AI transmitter | `python scripts/hsp_vercel_ai_transmitter_smoke.py --verify` |
| Production sidecar | `https://tinymodel.hyperlinks.space/v1/plan` |

```bash
python scripts/hsp_integration_smoke.py --verify          # includes composer gate
python scripts/hsp_composer_smoke.py --verify
```

---

## 7. HSP implementation checklist (when UI is ready)

### Phase A — Composer shell (no UI change)

- [ ] Copy reference modules to `ai/`
- [ ] Add `npm` deps: `ai`, provider packages or gateway-only strings
- [ ] Implement `getAvailability()` merging TinyModel health + assume Vercel AI up until 5xx
- [ ] Unit-test `composeTurn` with mocked plan responses
- [ ] Log `meta.lane`, `meta.model`, `meta.gateway` on every `/api/ai` response

### Phase B — Wire generation (Vercel AI priority)

- [ ] Replace `ai/transmitter.ts` body with reference `transmit` / `transmitStream`
- [ ] Inject `streamText` from `import { streamText } from "ai"`
- [ ] Set `AI_PROVIDER=hybrid` on Vercel (remove single-model OpenAI default)
- [ ] Keep `legacyOpenAiTransmit` adapter until `AI_PROVIDER=openai` is deleted
- [ ] Emit **first SSE chunk** with `actions[]` + meta before tokens

### Phase C — Product face

- [ ] GlobalBottomBar → `/api/ai` with full `context`
- [ ] `applyAiActions()` for navigate / feature
- [ ] Real chat panel (`app/(app)/ai.tsx`)

### Phase D — Hardening

- [ ] Dashboard: AI Gateway usage / fallbacks (Vercel observability)
- [ ] Alert when `meta.fallback_used` rate spikes
- [ ] Pin `tinymodelCorpusVersion` from `GET /v1/meta`
- [ ] Expand `hsp_composer_routes.jsonl` as new flows ship

---

## 8. Fallback matrix

| Condition | Composer behavior |
| --------- | ----------------- |
| TinyModel down | Heuristic intent + actions; `meta.tinymodel.error` |
| Vercel AI down | `ub` if up, else `template` (+ RAG text if plan succeeded) |
| Swap.Coffee down | `vercel_ai` with disclaimer; no fabricated prices |
| Navigate + all LLMs down | Still return `actions[]`; template ack |
| Gateway primary fails | AI SDK tries `gateway.models` chain automatically |

---

## 9. Example turns

| Input | Plan intent | Lane | Generator | Model (typical) |
| ----- | ----------- | ---- | --------- | --------------- |
| open swap page | navigate | control | template | — |
| what is this (on /shield) | explain_screen | grounded | vercel_ai | quality + gateway fallbacks |
| $USDT price | token_info | facts | swap_coffee_hybrid | quality |
| summarize swap help | chat | soft | vercel_ai | fast |
| swap 10 TON to USDT | swap_hint | grounded | vercel_ai | quality |

Automated: `texts/golden-prompts/hsp_composer_routes.jsonl` + `hsp_composer_smoke.py`.

---

## 10. Anti-patterns

| Avoid | Prefer |
| ----- | ------ |
| Client picks OpenAI vs Anthropic | Server `composeTurn` + env defaults |
| Same model for navigate and chat | `control` lane + template |
| Skip plan when sidecar is up | Always plan first in hybrid mode |
| Hardcode one OpenAI model id | Gateway + `AI_COMPOSER_*_MODEL` env |
| Block navigate on LLM failure | Return `actions[]` regardless |

---

## 11. Next steps (TinyModel only, no HSP PR)

1. Keep golden composer routes green when router/corpus changes.
2. Add composer scenarios when new intents ship (prefill, token_info action).
3. Optional: live integration test that mocks Vercel AI (HSP repo).
4. Optional: UB deploy with HSP corpus for `ub` generator tier.

**Next steps (HSP):** Phase A checklist above—copy modules and wire `streamText` behind existing `/api/ai`.

*Update when HSP ships hybrid composer or gateway defaults change.*
