# AI Transmitter: smart routing across models and APIs

**Target file (HSP repo):** `ai/transmitter.ts`  
**Role:** Single orchestrator for every AI turn—bottom bar, chat panel, Telegram bot. It **does not** pick one model globally; it **routes per request** based on prompt, screen context, explicit mode, and **which backends are healthy**.

TinyModel reference client: [`integrations/hsp/reference/`](../integrations/hsp/reference/). Plan context: [02-architecture.md](02-architecture.md), [03-interface-control.md](03-interface-control.md).

---

## Design principles

1. **Plan first, generate second** — always try TinyModel `POST /v1/plan` when the sidecar is configured (cheap, deterministic `actions[]` + RAG).
2. **Best tool for the job** — token facts from Swap.Coffee, navigation from plan, wording from OpenAI or UB.
3. **Graceful degradation** — if a backend is down, fall back without breaking the user turn (log `meta.routing.fallback_used`).
4. **Never block on slow demos** — public HF Space is last-resort, not in the hot path for production.
5. **Server-side only** — all API keys and sidecar URLs stay on Vercel; clients talk only to `/api/ai`.

---

## Backends the transmitter talks to

| Backend | Env | Strength | Weakness |
| ------- | --- | -------- | -------- |
| **TinyModel sidecar** | `TINYMODEL_API_URL` | Intent, `actions[]`, HSP RAG, `explain_screen` | No long-form chat quality alone |
| **OpenAI** | `OPENAI_API_KEY` | Reply quality, `token_info` narration | Cost, no native navigate |
| **Swap.Coffee** | existing HSP config | TON token facts | Not conversational |
| **Universal Brain** | `UB_CHAT_URL` (optional) | Summarize, reformulate, NL signals, memory | Heavier, Gradio or custom HTTP |
| **HF Space** | `UB_CHAT_URL` → public Space | Demos only | Cold start, queue, no `actions[]` |

---

## High-level flow (every request)

```mermaid
flowchart TD
  IN[AiRequest: input, mode, context, thread]
  AVAIL[Probe availability cache]
  PLAN{TinyModel\navailable?}
  P[POST /v1/plan]
  MODE{Resolved intent}
  NAV[Template + actions[]]
  TOK[Swap.Coffee + OpenAI]
  GND[RAG context + generator]
  GEN{Pick generator}
  OAI[OpenAI stream]
  UB[UB chat / generate]
  TPL[Short template only]
  OUT[TransmitResponse:\noutput_text, actions, meta]

  IN --> AVAIL --> PLAN
  PLAN -->|yes| P --> MODE
  PLAN -->|no| MODE2[Regex/mode fallback]
  MODE2 --> MODE
  MODE -->|navigate, feature| NAV --> OUT
  MODE -->|token_info| TOK --> OUT
  MODE -->|explain_screen, chat, swap_hint| GND --> GEN
  GEN -->|OpenAI up| OAI --> OUT
  GEN -->|OpenAI down, UB up| UB --> OUT
  GEN -->|both down| TPL --> OUT
```

---

## Step 1 — Resolve availability (cached)

Maintain a lightweight **health cache** (refresh every 30–60s, non-blocking on user path):

| Service | Probe | Mark down when |
| ------- | ----- | -------------- |
| TinyModel | `GET ${TINYMODEL_API_URL}/healthz` | timeout, non-200, 3 failures |
| OpenAI | optional lightweight `models` or skip (assume up until 5xx on call) | 401, 429 sustained, 5xx |
| UB | `GET ${UB_CHAT_URL}/healthz` or Gradio info | timeout, non-200 |
| Swap.Coffee | existing HSP health | existing rules |

Expose in response meta:

```json
"meta": {
  "availability": {
    "tinymodel": true,
    "openai": true,
    "ub": false,
    "swap_coffee": true
  }
}
```

**Rule:** never call a backend marked down until next successful probe (circuit-breaker style).

---

## Step 2 — Plan (control plane)

When `TINYMODEL_API_URL` is set **and** availability.tinymodel:

```typescript
const plan = await planRequest(input, {
  context: {
    route: request.context?.route,
    locale: request.context?.locale,
    wallet_connected: request.context?.walletConnected,
  },
});
```

Use plan output:

| Field | Transmitter use |
| ----- | --------------- |
| `intent` | Primary routing key |
| `actions` | Copy to response (client executor) |
| `retrieval.chunk_preview` | Inject into generator system context |
| `route_hint` | Analytics + optional short ack text |

**If plan fails** (timeout, 5xx): continue with **local fallback routing** (see Step 3) and set `meta.tinymodel = { error: "plan_unavailable", … }`.

---

## Step 3 — Intent resolution (prompt + mode + plan)

Priority order:

1. **Explicit `request.mode`** — `token_info` always wins for symbol lookups when mode set.
2. **`plan.intent`** — when plan succeeded.
3. **Local heuristics** — port of `hsp_intent_router` / regex (swap, send, shield, telegram).
4. **Default** — `chat`.

| Resolved intent | Generator path | actions[] |
| --------------- | -------------- | --------- |
| `navigate` | Short template or tiny OpenAI ack | From plan |
| `explain_screen` | Grounded chat (RAG + OpenAI/UB) | Usually none |
| `token_info` | Swap.Coffee facts + OpenAI | Optional `token_info` action |
| `swap_hint` | Grounded + prefill action (future) | Prefill, no submit |
| `chat` | OpenAI or UB | From plan if any |

**Prompt signals** (upgrade path without new intents):

| User pattern | Boost intent |
| ------------ | ------------ |
| `$USDT`, `price`, `holders` | `token_info` |
| `summarize`, `rephrase`, `/summarize` | UB or OpenAI with UB-style system prompt |
| `be brief`, `step by step` | NL overlay in `buildContext()` (port key `nl_controls` rules) |
| Russian UI + English question | Reply language instruction from `context.locale` |

---

## Step 4 — Pick generator (availability-aware)

```typescript
type GeneratorTier = "openai" | "ub" | "template";

function pickGenerator(intent: PlanIntent, avail: Availability): GeneratorTier {
  if (intent === "navigate") {
    return avail.openai ? "openai" : "template";
  }
  if (intent === "token_info") {
    return avail.openai ? "openai" : "template"; // facts still from Swap.Coffee
  }
  // explain_screen, chat, swap_hint
  if (avail.openai) return "openai";
  if (avail.ub) return "ub";
  return "template";
}
```

### Generator behaviors

| Tier | When | Behavior |
| ---- | ---- | -------- |
| **openai** | Default quality path | `transmitStream` with enriched system prompt (thread + RAG + screen + safety) |
| **ub** | OpenAI down or `AI_GENERATOR=ub` for soft chat | `UB_CHAT_URL` Gradio or `horizon2_server` `/v1/generate`; pass `scope_key` = session id |
| **template** | All generators down | Deterministic strings: “Opening Swap…”, retrieval chunk as plain text, apology if nothing else |

**HF public Space:** only use when `UB_CHAT_URL` explicitly points there **and** `AI_ALLOW_HF_SPACE=true` (staging). Production should use self-hosted UB or skip.

---

## Step 5 — `buildContext()` (shared)

Assemble generator input once per turn:

```typescript
async function buildContext(req: AiRequest, plan: PlanResponse | null): Promise<string> {
  const parts: string[] = [];

  // 1. Program help excerpt
  if (plan?.retrieval?.chunk_preview) {
    parts.push(`Help excerpt (cite when relevant):\n${plan.retrieval.chunk_preview}`);
  }

  // 2. Screen context
  if (req.context?.route) {
    parts.push(`User is on app route: ${req.context.route}`);
  }

  // 3. Wallet / locale
  if (req.context?.locale) parts.push(`UI locale: ${req.context.locale}`);
  if (req.context?.walletConnected === false) {
    parts.push("Wallet not connected; do not imply they can send yet.");
  }

  // 4. NL overlays (brief, language, step style) — from prompt regex or UB signals

  // 5. Safety footer (never ask for seed phrase, confirm sends on screen)

  return parts.join("\n\n");
}
```

---

## Configuration (env)

```bash
# Provider mode
AI_PROVIDER=hybrid          # openai | hybrid (recommended)
AI_GENERATOR=auto           # auto | openai | ub | template

# Backends
TINYMODEL_API_URL=https://tinymodel-production.up.railway.app
TINYMODEL_PLAN_TIMEOUT_MS=8000
OPENAI_API_KEY=sk-...
UB_CHAT_URL=                # optional self-hosted UB
AI_ALLOW_HF_SPACE=false     # never true in production

# Resilience
AI_HEALTH_CACHE_MS=45000
AI_PLAN_REQUIRED=false      # if true, fail turn when plan down; else fallback heuristics
```

| `AI_PROVIDER` | Behavior |
| ------------- | -------- |
| `openai` | Legacy: skip plan; existing transmitter only |
| `hybrid` | Plan + enriched OpenAI/UB (target state) |

---

## Response shape (transmitter output)

```typescript
interface TransmitResponse {
  ok: boolean;
  output_text: string;
  actions: TinyModelAction[];
  meta: {
    intent: PlanIntent;
    generator: "openai" | "ub" | "template";
    availability: AvailabilitySnapshot;
    tinymodel?: MetaTinyModel | { error: string };
    routing: {
      plan_used: boolean;
      fallback_used?: string; // e.g. "openai→ub", "plan→heuristic"
    };
    token_info?: object;      // Swap.Coffee payload when applicable
  };
}
```

Stream variant: emit `actions[]` and `meta` in **first SSE event** so the client can navigate before text finishes.

---

## Fallback matrix (quick reference)

| Condition | Action |
| --------- | ------ |
| TinyModel down | Heuristic intent; no RAG; `meta.routing.fallback_used = "plan→heuristic"` |
| OpenAI 429 | Retry once with backoff; then UB if up; else template |
| OpenAI 5xx | UB → template |
| UB down | OpenAI only for chat |
| Swap.Coffee down | OpenAI with disclaimer; no fabricated prices |
| Both OpenAI + UB down | Template + retrieval text if plan succeeded |
| Plan says navigate, generator down | Still return `actions[]`; template ack text |

---

## `transmitStream` integration

Today HSP bot uses `transmitStream` for OpenAI. Hybrid path:

```text
1. await plan (parallel optional: start Swap.Coffee if token_info likely)
2. yield meta chunk { actions, intent, availability }
3. stream generator tokens
4. yield done { full meta }
```

Keep **one** public API: `transmit()` / `transmitStream()` — handlers do not branch on provider themselves.

---

## Implementation checklist (HSP repo)

| Task | File |
| ---- | ---- |
| Copy plan client | `ai/tinymodel.ts` ← `integrations/hsp/reference/` |
| Availability cache | `ai/backendHealth.ts` |
| Intent merge (plan + heuristics) | `ai/intentRouter.ts` |
| Generator pick + fallbacks | `ai/transmitter.ts` |
| Context builder | `ai/buildContext.ts` |
| Stream meta first | `api/_handlers/ai/stream.ts` |
| Golden manual tests | `docs/ai-transmitter-scenarios.md` |

---

## Test scenarios (manual)

| # | Input | Context | Expect |
| - | ----- | ------- | ------ |
| 1 | open swap | — | `actions: navigate /swap`, generator any |
| 2 | what is this | route `/shield` | intent `explain_screen`, retrieval mentions Shield |
| 3 | $USDT price | — | Swap.Coffee + OpenAI |
| 4 | (TinyModel stopped) | — | heuristic navigate still works for “open swap” |
| 5 | (OpenAI stopped) | chat question | UB or template + RAG text |
| 6 | summarize this: … | — | UB path if configured |

Automated: mirror navigate cases in `texts/golden-prompts/hsp_intents.jsonl`; run `ub_eval_runner --verify` on TinyModel; HSP adds integration tests against mocked plan responses.

---

## Anti-patterns

| Do not | Do instead |
| ------ | ---------- |
| Call OpenAI for every navigate ack | Template or one-line OpenAI |
| Let mobile client pick provider | `AI_PROVIDER` on server only |
| Block user on HF Space cold start | Self-host or fallback template |
| Auto-execute swap/send from chat | `actions[]` prefill only |
| Ignore `plan.actions` when generator fails | Always return actions when plan succeeded |

---

## Related

- [04-phases.md](04-phases.md) — Phase 2 owns transmitter refactor
- [`texts/hsp-sidecar-meta.md`](../texts/hsp-sidecar-meta.md) — `meta.tinymodel` fields
- [`texts/hsp-huggingface-space-responses.md`](../texts/hsp-huggingface-space-responses.md) — when to use HF API
