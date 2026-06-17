# Interface control: intents, actions, and safety

## Control model

The model does **not** emit UI events. It emits **`actions[]`** that HSP maps to:

| `actions[]` type | HSP executor behavior |
| ---------------- | --------------------- |
| `{ type: "navigate", path: "/swap" }` | `router.push(path)` |
| `{ type: "feature", id: "shield" }` | Open Shield flow / floating control |
| `{ type: "feature", id: "connect_telegram" }` | Start Telegram connect |
| `{ type: "prefill", screen: "swap", fields: {…} }` | Set swap form state (future) |
| `{ type: "token_info", symbol: "USDT" }` | Run existing token_info pipeline |

**Source of truth today:** TinyModel `POST /v1/plan` + `hsp_intent_router.py` (mirrored in TS when copied to HSP).

---

## Intent enum

| Intent | Trigger examples | Side effects |
| ------ | ---------------- | ------------ |
| `navigate` | “open swap”, “show wallet” | `actions[]` navigate |
| `explain_screen` | “what is this” + `context.route=/shield` | RAG over screen chunk; usually no navigate |
| `token_info` | “$NOT price”, “USDT holders” | Swap.Coffee + chat (no auto-trade) |
| `swap_hint` | “swap 10 TON to ETH” | Prefill + explain (confirm required) |
| `chat` | General questions | Reply only unless RAG suggests navigate |

Plan response includes `intent` string; HSP `meta.intent` should match for analytics.

---

## Screen context (required for explain_screen)

Client must send on every AI call:

```typescript
context: {
  route: "/shield",      // from expo-router
  locale: "en" | "ru",
  walletConnected: boolean,
  selectedToken?: string // when on token surfaces
}
```

TinyModel maps `route` → corpus title (see `hsp_screen_context.py`). Vague on-screen questions bias retrieval to the correct help chunk.

**Wide layout:** inject same context from the panel that hosts chat beside Smart/home.

---

## Safety rules (non-negotiable)

| Action class | Rule |
| ------------ | ---- |
| **Navigate** | Auto-apply for safe routes (swap, get, feed, settings help) |
| **Send / sign / swap submit** | Never auto-execute; prefill + explicit user tap |
| **Secrets** | Never ask user to paste seed phrase in AI; corpus enforces this |
| **Telegram connect** | Feature action opens flow; no silent linking |
| **Destructive** | No `actions[]` without confirm modal |

Log all applied actions server-side for support and eval.

---

## Client executor (HSP `ai/actionExecutor.ts` — to build)

```typescript
export async function applyAiActions(
  actions: TinyModelAction[],
  ctx: { router: Router; dispatch: AppDispatch }
): Promise<void> {
  for (const action of actions) {
    switch (action.type) {
      case "navigate":
        ctx.router.push(action.path);
        break;
      case "feature":
        openFeature(action.id); // shield, connect_telegram, …
        break;
      // prefill, token_info delegation, …
    }
  }
}
```

Call **after** first stream chunk or on complete message—product choice; navigate-on-intent can be immediate for responsiveness.

---

## Chat UI requirements

| Surface | Requirement |
| ------- | ----------- |
| **GlobalBottomBar** | Submit → `/api/ai` with `context`, not only `/ai?prompt=` stub |
| **Chat panel** | Stream `output_text`; show thread; optional dev “brain trace” toggle |
| **Narrow** | Full-screen `/ai` |
| **Wide** | Inline column next to Smart/home (per Smart layout docs) |
| **After response** | `applyAiActions(actions)` |

Until UI ships, backend can log `actions[]` in `meta` for Telegram bot or API testers.

---

## Golden coverage

| Suite | File | Gate |
| ----- | ---- | ---- |
| Navigate intents | `texts/golden-prompts/hsp_intents.jsonl` | `ub_eval_runner --verify` |
| Screen explain | `hsp_screen_context_smoke.py` | stdlib |
| End-to-end plan | `hsp_phase3_server_smoke.py` | live HTTP |
| Full stack | `hsp_integration_smoke.py --full` | CI / manual |

Add new intents to golden file **before** expanding router regex in both Python and TS.
