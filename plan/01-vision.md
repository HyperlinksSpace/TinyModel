# Vision: universal chat that controls the program

## User experience

A signed-in user types once in **AI & Search** (GlobalBottomBar):

| User says | Program should |
| --------- | -------------- |
| “Open swap and explain slippage” | Navigate to Swap **and** answer in chat |
| “What is this?” (on Shield screen) | Explain Shield from HSP docs **without** leaving the screen |
| “What is USDT on TON?” | `token_info` facts + concise analyst-style reply |
| “Send 10 TON to …” | Prefill Send flow; **never** auto-submit without confirm |
| “Summarize this message” | Universal Brain reformulate/summarize path |
| “Remember I prefer 1% slippage” | Scoped memory (later phase) |

**Competitive line:** generic assistants give text in another window. HSP gives **text + the next click** inside one wallet/social/swap program.

---

## What we mean by “the model controls the interface”

**Do not mean:** the neural network directly clicks React Native views or signs transactions.

**Do mean:** a **text-in / structured-out control plane**:

```text
user text + screen context
    → intent (navigate | explain_screen | token_info | chat | …)
    → optional actions[] for the app executor
    → generation tier produces user-visible reply
    → HSP client applies safe actions (router.push, feature toggles, prefill)
```

The **app** remains authoritative for wallet, auth, and destructive ops. The model proposes; the shell executes with gates.

---

## “Universal” scope (honest)

| In scope for v1 | Later / optional |
| --------------- | ---------------- |
| Chat + help RAG over HSP corpus | Full AGI / arbitrary tool use |
| Navigate major routes (swap, send, get, shield, feed) | Every deep settings screen |
| Explain current screen (`context.route`) | Vision / screenshot understanding |
| Token lookup via Swap.Coffee | On-chain execution from chat |
| OpenAI quality answers + TinyModel routing | 100% offline SmolLM-only |
| Telegram bot parity via same `/api/ai` | |

Universal **for the product** first: everything a daily HSP user does from the bottom bar—not universal for every task on the internet.

---

## Success criteria

1. Bottom bar is the **primary** control surface (not a stub `/ai` redirect only).
2. **≥90%** of golden HSP intents pass `ub_eval_runner` + integration smokes before release.
3. Every `/api/ai` response can include **`actions[]`** and **`meta.tinymodel`** for debug.
4. Wallet/send/swap actions always require **on-screen confirmation**.
5. Production does **not** depend on the public HF Space cold-start path (self-hosted sidecar or UB).
