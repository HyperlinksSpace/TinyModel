# Can Hyperlinks Space Program get responses from our Hugging Face Space?

**Short answer:** **Yes, technically** — the deployed **Universal Brain** Space exposes an HTTP **`chat`** endpoint that returns full assistant replies. **Hyperlinks Space Program (HSP) does not call it yet**; the app still routes AI through **`ai/transmitter.ts` → OpenAI**. Wiring HSP to the Space (or to a dedicated Universal Brain service built from the same artifact) is planned and straightforward.

Related docs: [`hsp-tinymodel-integration-strategy.md`](hsp-tinymodel-integration-strategy.md), [`HUGGING_FACE_DEPLOYMENT_GUIDE.md`](HUGGING_FACE_DEPLOYMENT_GUIDE.md), [`universal-brain-capabilities.md`](universal-brain-capabilities.md).

---

## What is deployed today

| Artifact | URL | Role |
| -------- | --- | ---- |
| **Space (Hub)** | [HyperlinksSpace/TinyModel1Space](https://huggingface.co/spaces/HyperlinksSpace/TinyModel1Space) | Gradio **Universal Brain** chat |
| **Direct app** | [hyperlinksspace-tinymodel1space.hf.space](https://hyperlinksspace-tinymodel1space.hf.space) | Same UI + API as the Hub Space |
| **Encoder weights** | [HyperlinksSpace/TinyModel1](https://huggingface.co/HyperlinksSpace/TinyModel1) | Topic hint + embeddings inside the Space |

The Space runs the same stack as local `scripts/universal_brain_chat.py`: **SmolLM2-360M-Instruct** (override via `HORIZON2_MODEL`), **TinyModel1** encoder, **FAQ RAG**, **JSON intent routing**, **NL session controls**, optional **Google CSE** web search, and **scoped SQLite memory**.

Deployment is automated from this repo via GitHub Actions **`deploy-hf-space-versioned.yml`** (see [`HUGGING_FACE_DEPLOYMENT_INTERNAL.md`](HUGGING_FACE_DEPLOYMENT_INTERNAL.md)).

---

## What HSP uses today

| Layer | HSP today | Hugging Face Space |
| ----- | --------- | ------------------- |
| **User surface** | Expo / TMA / Windows — wallet, swap, **GlobalBottomBar** | Single Gradio chat box |
| **AI backend** | `ai/transmitter.ts` → **OpenAI** (`gpt-5.2`), modes `chat` \| `token_info` | Full Universal Brain pipeline on CPU |
| **In-app help RAG** | Not wired (corpus exists in [`hsp_program_corpus.md`](hsp_program_corpus.md)) | Default FAQ corpus (`rag_faq_corpus.md`), not HSP-specific yet |
| **Bottom bar** | Routes to stub `/ai` or bot `transmitStream` | N/A |

So users in **HSP** and visitors on the **Space** are on **different backends** until integration work lands in Hyperlinks Space Program.

---

## Proof: the Space API responds

The live Space exposes Gradio endpoint **`/chat`** (`api_name="chat"` in `universal_brain_chat.py`). External callers can use it without opening the UI.

**Discover endpoints**

```http
GET https://hyperlinksspace-tinymodel1space.hf.space/gradio_api/info
```

**Call pattern (Gradio 5)**

1. `POST /gradio_api/call/chat` with JSON body `{"data": [message, history, session_state]}`.
2. Read `event_id` from the response.
3. `GET /gradio_api/call/chat/{event_id}` until `event: complete` — the `data` payload contains the updated chat history and assistant text.

**Minimal inputs**

| Field | Type | Notes |
| ----- | ---- | ----- |
| `message` | string | User text (plain language or `/help`, `/status`, …) |
| `history` | list | Prior chat messages; use `[]` for a fresh turn |
| `session_state` | object | Universal Brain session dict; use `{}` for defaults |

A smoke test against production (June 2026) returned a normal assistant reply with an optional *Brain trace* footer — confirming the deployed Space is reachable and answers programmatically.

**Official client**

On the Space page, **Use via API** shows copy-paste examples for the Gradio Python/JS client. That is the same **`chat`** pipeline as the **Send** button.

---

## How HSP would consume it (integration paths)

Three practical options, ordered by how much of Universal Brain you need inside the app.

### Path 1 — Call the public Space URL (fastest experiment)

Add a server-side proxy in HSP (recommended — do not call HF from the mobile client directly):

```typescript
// Conceptual: HSP api/_handlers/ai.ts or ai/universalBrain.ts
const UB_CHAT_URL = process.env.UB_CHAT_URL
  ?? "https://hyperlinksspace-tinymodel1space.hf.space";

// POST ${UB_CHAT_URL}/gradio_api/call/chat
// Poll or use @gradio/client for SSE
```

**Good for:** proving end-to-end wiring, internal demos, A/B against OpenAI.

**Weak for production:** cold starts on free CPU Spaces, queue concurrency (default 2), no per-user auth, shared default memory scope, latency (tens of seconds on first load), and coupling product uptime to public HF quotas.

### Path 2 — Dedicated Universal Brain service (recommended for product)

Build and deploy the same artifact HSP controls:

```bash
python scripts/build_space_artifact.py --namespace HyperlinksSpace --version 1 --output-dir .tmp/hsp-ub
```

Run on Fly, Railway, GCP, etc., with:

- `--rag-corpus` pointing at HSP docs (from [`hsp_program_corpus.md`](hsp_program_corpus.md))
- `scope_key` = HSP authenticated session id
- Optional `HORIZON2_MODEL` tier for quality vs cost

HSP sets `UB_CHAT_URL` to **your** host, not the public demo Space. See Phase 3 in [`hsp-tinymodel-integration-strategy.md`](hsp-tinymodel-integration-strategy.md).

### Path 3 — Hybrid (recommended architecture)

Keep OpenAI for hard reasoning and wallet-adjacent wording; use TinyModel for **routing, RAG, and reply shaping**:

```text
GlobalBottomBar → HSP /api/ai
    → TinyModel sidecar (classify + retrieve over hsp_program_corpus)
    → OpenAI and/or UB chat for final text
    → structured actions[] (navigate, token_info, …)
```

This matches the phased plan already documented: encoder sidecar first (`TINYMODEL_API_URL`), then provider abstraction in `ai/transmitter.ts`, then full UB when needed.

---

## Suggested env vars in HSP

```bash
# Phase 1 — encoder + HSP help retrieval only
TINYMODEL_API_URL=http://127.0.0.1:8765
TINYMODEL_ENCODER_MODEL=HyperlinksSpace/TinyModel1

# Phase 2+ — full Universal Brain HTTP (Space URL or self-hosted)
UB_CHAT_URL=https://hyperlinksspace-tinymodel1space.hf.space

# Provider mix until hybrid is default
AI_PROVIDER=openai   # today
# AI_PROVIDER=hybrid  # openai + tinymodel RAG/routing (+ optional UB_CHAT_URL)
```

---

## What you gain vs what you still need elsewhere

| Capability | From HF Space / UB | Still need in HSP |
| ---------- | ------------------ | ----------------- |
| Summarize, reformulate, FAQ, NL reply signals | Yes | Wire API + UI streaming |
| Program help (“where is Shield?”) | After HSP corpus in RAG | Corpus sync ([`hsp_program_corpus.md`](hsp_program_corpus.md)) |
| Token prices / Swap.Coffee facts | No | Existing `token_info` + Swap.Coffee |
| Navigate to `/swap`, prefill swap | No | Intent → `actions[]` executor in app |
| User auth-scoped memory | Partial (scope_key only) | Map HSP session id → UB scope |
| Wallet actions | No | Human confirm + wallet gates |

**Competitive angle:** rivals give answers in a browser tab; integrated HSP gives **answers plus the next in-app click** once `actions[]` is implemented.

---

## Limits and risks (honest)

| Topic | Detail |
| ----- | ------ |
| **Not connected yet** | No code in HSP calls `UB_CHAT_URL` today |
| **Latency** | CPU Space + model load; first request after sleep can take 30–90s |
| **Concurrency** | Public demo queues; product should self-host or upgrade HF hardware |
| **Privacy** | Public Space default scope is not private auth; pass per-user `scope_key` when wired |
| **Streaming** | Gradio API returns complete turns; HSP streaming needs SSE client or a custom wrapper |
| **Structured navigation** | UB returns text; HSP must parse intent or use a hybrid router for `router.push` |
| **Secrets** | Do not expose HF tokens or Google CSE keys in the mobile app — proxy via HSP API |

---

## Recommended next steps

| Priority | Action | Repo |
| -------- | ------ | ---- |
| **P0** | Add `ai/universalBrain.ts` (Gradio client) + `UB_CHAT_URL` in HSP `.env.example` | HSP |
| **P0** | Proxy `/api/ai` through UB for **non-wallet** chat; keep OpenAI for `token_info` | HSP |
| **P1** | Deploy UB with **`hsp_program_corpus.md`** as RAG source | TinyModel + ops |
| **P1** | Real chat UI on `/ai`; bottom bar POSTs to `/api/ai` with stream | HSP |
| **P2** | Golden prompts + `ub_eval_runner --verify` on HSP intents in CI | TinyModel |

---

## Bottom line

- **Can HSP get responses from the Hugging Face Space we deployed?** **Yes** — via the Gradio **`chat`** HTTP API on [hyperlinksspace-tinymodel1space.hf.space](https://hyperlinksspace-tinymodel1space.hf.space).
- **Does HSP do that today?** **No** — it still uses **OpenAI** through `ai/transmitter.ts`.
- **What should we do?** Treat the public Space as a **proven backend demo**; point production at a **self-hosted Universal Brain** (same artifact, HSP-tuned corpus) behind HSP’s **`/api/ai`**, using the **hybrid** plan in [`hsp-tinymodel-integration-strategy.md`](hsp-tinymodel-integration-strategy.md).
