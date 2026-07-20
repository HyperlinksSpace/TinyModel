# TinyModel: functionality, scope, and how to develop further

**Last updated:** July 2026  
**Audience:** maintainers deciding what TinyModel does today vs what to build next  
**Related:** [`plan/README.md`](../plan/README.md) (HSP master plan) · [`tinymodel-current-state-and-product-path.md`](tinymodel-current-state-and-product-path.md) (product-level estimate) · [`phase3-serving-profile.md`](phase3-serving-profile.md) (HTTP API contract)

---

## 1. What TinyModel is

TinyModel is a **small, deployable text-understanding stack** built around **TinyModel1** — a compact BERT-style **encoder** trained for **topic classification** and **dense embeddings**. It is **not** a large language model on its own.

| Piece | Role |
| ----- | ---- |
| **TinyModel1** ([Hub weights](https://huggingface.co/HyperlinksSpace/TinyModel1)) | 4-label classifier (default labels: World / Business / Sports / Sci/Tech) + sentence embeddings for similarity and retrieval |
| **`TinyModelRuntime`** (`scripts/tinymodel_runtime.py`) | PyTorch inference: `classify`, `embed`, cosine `retrieve` over a candidate list |
| **Universal Brain** ([HF Space](https://huggingface.co/spaces/HyperlinksSpace/TinyModel1Space)) | Full **text-in / text-out** chat: SmolLM2 instruct LM + TinyModel1 encoder + FAQ RAG + routing + memory + 40+ NL reply controls |
| **HSP encoder sidecar** (Railway) | JSON API for **Hyperlinks Space Program**: intent routing, `actions[]`, HSP help RAG — **no long-form chat** in this service |

**Honest positioning:** TinyModel is strong as a **cheap control plane** (route, retrieve, classify) and as the **retrieval backbone** inside a larger assistant. **Reply quality** for open-ended chat still comes from **OpenAI** (in HSP) or **SmolLM / UB** (in the Space demo), not from the encoder alone.

---

## 2. What works today (functionality)

### 2.1 Core model capabilities

| Capability | How | Typical use |
| ---------- | --- | ----------- |
| **Classification** | Softmax over label head | Routing gate (`routing_policy.py`: confidence + margin); AG News–style topic hint |
| **Embeddings** | Mean-pool encoder hidden states | Semantic similarity, hybrid RAG second signal |
| **Retrieval** | Cosine similarity over candidate strings | FAQ chunks, HSP help corpus |
| **Training / eval** | `train_tinymodel1_classifier.py`, `eval_report.json`, Phase 1 compare matrix | Reproducible benchmarks, second datasets (emotion, SST-2) |
| **Export / serve** | ONNX export, `phase3_benchmark.py`, reference HTTP server | Sidecar deployment, latency reports |

Default public weights: **`HyperlinksSpace/TinyModel1`**. Local or custom checkpoints work anywhere `TinyModelRuntime` is pointed.

### 2.2 Universal Brain (demo / research surface)

The Gradio Space is the **product-facing chat demo**. It combines:

- **Generative:** `HuggingFaceTB/SmolLM2-360M-Instruct` (override via `HORIZON2_MODEL`)
- **Encoder:** classify, embed, hybrid FAQ RAG (`texts/rag_faq_corpus.md`)
- **Routing:** JSON intent router → slash tools and NL controls
- **Memory:** Horizon 3 SQLite (session + long-term, scoped by `scope_key`)
- **Optional web:** Google CSE when secrets are set

**Use for:** trying the stack, comparing reply quality, golden-prompt eval (`python scripts/ub_eval_runner.py --verify`).  
**Do not use for:** primary HSP production traffic (cold start, Gradio API, no native `actions[]`).

See [`universal-brain-capabilities.md`](universal-brain-capabilities.md) for the full feature list.

### 2.3 Hyperlinks Space Program integration (TinyModel repo — done)

TinyModel’s **current product focus** is being the **encoder sidecar** for HSP’s universal chat + interface control. Implemented in this repo:

| Component | Location | Purpose |
| --------- | -------- | ------- |
| **HSP help corpus** | `texts/hsp_program_corpus.md` (12 chunks) | Swap, send, Shield, Telegram, feed, safety, etc. |
| **Plan glue** | `scripts/hsp_plan_lib.py` | One call: regex route hints + classify gate + hybrid RAG + `intent` |
| **HTTP sidecar** | `scripts/phase3_reference_server.py` | `POST /v1/plan`, `/v1/classify`, `/v1/retrieve`, `GET /v1/meta`, `GET /healthz` |
| **Production deploy** | Railway → **https://tinymodel.hyperlinks.space** | Docker image bundles corpus; pulls weights from Hub |
| **Golden intents** | `texts/golden-prompts/hsp_intents.jsonl` | Regression for navigate / feature hints |
| **Reference TS modules** | `integrations/hsp/reference/` | Copy to HSP when wiring `ai/transmitter.ts` |
| **Verify gates** | `python scripts/hsp_integration_smoke.py --verify [--full] [--production]` | 9 stdlib + optional torch + Railway probe |

#### `/v1/plan` behavior (control plane)

For each user message (+ optional screen context):

1. **Deterministic route hints** — regex (`hsp_intent_router.py`): e.g. “open swap page” → `navigate:/swap` + `actions: [{type: navigate, path: /swap}]`
2. **Classifier gate** — TinyModel1 probs → accept / abstain (`routing.fallback`, confidence, margin)
3. **Hybrid RAG** — when routing abstains or user asks “what is this” on a screen (`context.route`), retrieve best HSP corpus chunk (keyword + encoder score)
4. **Intent** — `navigate` | `explain_screen` | `chat` (from route hint + screen + retrieval)

Example production call:

```bash
curl -sS -X POST https://tinymodel.hyperlinks.space/v1/plan \
  -H 'Content-Type: application/json' \
  -d '{"text":"open swap page"}'
```

Corpus drift detection:

```bash
curl -sS https://tinymodel.hyperlinks.space/v1/meta
# corpus.version = SHA-256 of bundled markdown — pin in HSP as tinymodelCorpusVersion
```

#### Phase 2 prep (reference only — not wired in HSP yet)

| Module | Role when HSP wires `ai/transmitter.ts` |
| ------ | --------------------------------------- |
| `fallback-router.ts` | Heuristic routing when sidecar is down |
| `availability.ts` | Health cache + circuit breaker |
| `build-context.ts` | Assemble RAG + screen context for OpenAI/UB |
| `buildMetaTinyModelError()` | Log `{ error: "plan_unavailable" }` in `meta.tinymodel` |

Spec: [`plan/07-ai-transmitter.md`](../plan/07-ai-transmitter.md).

### 2.4 What is **not** implemented yet

| Area | Status |
| ---- | ------ |
| **HSP UI** | GlobalBottomBar → real chat, `actions[]` executor — **Hyperlinks Space Program repo**, not started |
| **HSP `/api/ai` hybrid** | `AI_PROVIDER=hybrid`, `TINYMODEL_API_URL` on Vercel — not wired |
| **Dedicated UB on Railway** with HSP corpus | Optional Phase 4; artifact builder exists |
| **Fine-tuned HSP-specific encoder** | Still using AG News–style Hub weights; routing relies heavily on regex + RAG |
| **Auto swap/send execution** | By design: prefill + confirm only (`plan/03-interface-control.md`) |
| **Multimodal / vision** | Out of scope for v1 |

---

## 3. Scope boundaries

### In scope (TinyModel + HSP v1)

- Bottom-bar chat that **answers** and **navigates** when safe
- HSP help RAG (corpus bundled in sidecar)
- Screen-aware **explain this page** (`context.route`)
- Token facts via **Swap.Coffee** + OpenAI wording (HSP transmitter)
- Server-side only: no API keys or sidecar URLs in the mobile client
- Golden intent regression ≥ ~95% before releases

### Out of scope (v1)

- Replacing OpenAI for all chat quality
- On-chain signing or swap submission from chat
- Arbitrary tool use / general web agent
- Enterprise multi-tenant auth inside TinyModel sidecar
- Public HF Space as production hot path

### Two surfaces — do not confuse

| Surface | API | HSP use |
| ------- | --- | ------- |
| **Encoder sidecar** (`phase3_reference_server.py`) | JSON `/v1/plan` | **Primary** — routing, RAG, `actions[]` |
| **Universal Brain** (Gradio / Space) | `/chat`, tools | **Optional** — summarize, reformulate; deploy separately if needed |

---

## 4. Architecture (target production)

```text
HSP client (GlobalBottomBar, /ai chat)
    → POST /api/ai  (Vercel, ai/transmitter.ts)
        → POST TINYMODEL_API_URL/v1/plan   (Railway sidecar)
        → OpenAI (reply quality)
        → Swap.Coffee (token_info)
    ← { output_text, actions[], meta.tinymodel }
    → client applies actions[] (router.push, feature:shield, …)
```

TinyModel’s job in this loop: **plan first** (cheap, deterministic structure); **generate second** (OpenAI or UB for wording).

---

## 5. How to develop further

### Track A — TinyModel only (no HSP UI required)

These steps keep the sidecar credible while HSP UI is unfinished.

| Step | Work | Verify |
| ---- | ---- | ------ |
| **A1 Corpus maintenance** | Edit `texts/hsp_program_corpus.md`; redeploy Railway; check `GET /v1/meta` version | `hsp_corpus_smoke.py --verify` |
| **A2 Golden intents** | Add rows to `hsp_intents.jsonl` for new routes/phrases | `ub_eval_runner.py --verify` |
| **A3 Router parity** | Update `hsp_intent_router.py` + `fallback-router.ts` together | `hsp_reference_transmitter_smoke.py --verify` |
| **A4 Production health** | Nightly / manual Railway probe | `hsp_railway_deploy_smoke.py --verify` |
| **A5 Encoder quality (optional)** | Fine-tune TinyModel1 on HSP intent labels or retrieval pairs | `hsp_rag_hybrid_smoke.py --verify --full` |
| **A6 UB with HSP corpus (Phase 4)** | `build_space_artifact.py --rag-corpus texts/hsp_program_corpus.md`; host on Railway as `UB_CHAT_URL` | UB eval on summarize/reformulate subset |

**One command before any TinyModel release:**

```bash
python scripts/hsp_integration_smoke.py --verify --full --production
```

### Track B — When Hyperlinks Space Program is ready

Order matches [`plan/04-phases.md`](../plan/04-phases.md). **AI Composer** (TinyModel plan → Vercel AI SDK routing): [`integrations/hsp/composer/README.md`](../integrations/hsp/composer/README.md).

| Phase | HSP work | TinyModel dependency |
| ----- | -------- | -------------------- |
| **1 Wire sidecar** | Copy `integrations/hsp/reference/*` → `ai/`; set `TINYMODEL_API_URL=https://tinymodel.hyperlinks.space`; log `meta.tinymodel` | Sidecar live ✓ |
| **2 Hybrid transmitter** | Implement `plan/07-ai-transmitter.md`: plan → OpenAI + Swap.Coffee; fallback router; stream endpoint | Reference modules ✓ |
| **3 Chat UI + executor** | Real `/ai` panel; GlobalBottomBar sends `context`; `applyAiActions()` | Stable `/v1/plan` contract |
| **4 UB tier** | Route soft chat to self-hosted UB when OpenAI down | Optional UB deploy |

**Minimum env on Vercel (Phase 2):**

```bash
AI_PROVIDER=hybrid
TINYMODEL_API_URL=https://tinymodel.hyperlinks.space
OPENAI_API_KEY=sk-...
```

**Local dev (both repos):**

```bash
# Terminal 1 — TinyModel
python scripts/phase3_reference_server.py --port 8765

# Terminal 2 — HSP
TINYMODEL_API_URL=http://127.0.0.1:8765 AI_PROVIDER=hybrid npm run dev:vercel
```

### Track C — Universal Brain (parallel research path)

If the goal is a **standalone assistant** (not HSP shell):

- Improve SmolLM tier or swap `HORIZON2_MODEL_QUALITY` ([`model-profiles.md`](model-profiles.md))
- Expand FAQ / golden prompts; run `ub_eval_runner.py` in CI
- Keep HF Space updated via `build_space_artifact.py` + deploy workflow

This path does **not** replace the HSP sidecar for `actions[]` and stable JSON.

---

## 6. Suggested priorities (July 2026)

| Priority | Owner | Why |
| -------- | ----- | --- |
| **1** | HSP | Wire `TINYMODEL_API_URL` + hybrid transmitter — unlocks real product value |
| **2** | HSP | Chat UI + `actions[]` executor — user-visible “program moves” |
| **3** | TinyModel | Keep golden intents + production smoke green on corpus/router changes |
| **4** | Both | `token_info` + navigate combo flows (“open swap and explain slippage”) |
| **5** | TinyModel | Optional: fine-tune encoder or deploy UB with HSP corpus for cost/latency |

---

## 7. Key files (quick map)

| Question | Start here |
| -------- | ---------- |
| What does the HTTP API return? | [`phase3-serving-profile.md`](phase3-serving-profile.md) |
| How does plan logic work? | `scripts/hsp_plan_lib.py`, `scripts/hsp_intent_router.py` |
| How to deploy sidecar? | [`deploy/railway/README.md`](../deploy/railway/README.md), [`plan/05-deployment.md`](../plan/05-deployment.md) |
| HSP integration strategy (long) | [`hsp-tinymodel-integration-strategy.md`](hsp-tinymodel-integration-strategy.md) |
| Transmitter routing spec | [`plan/07-ai-transmitter.md`](../plan/07-ai-transmitter.md) |
| meta.tinymodel contract | [`hsp-sidecar-meta.md`](hsp-sidecar-meta.md) |
| Copy-paste TS for HSP | [`integrations/hsp/reference/`](../integrations/hsp/reference/) |
| All verify commands | [`plan/06-verify-gates.md`](../plan/06-verify-gates.md) |

---

## 8. Summary

- **Today:** TinyModel1 is a **small encoder**; the repo ships **training/eval tooling**, a **Universal Brain chat demo**, and a **production HSP sidecar** on Railway with `/v1/plan`, bundled help corpus, verify gates, and Phase 2 reference modules for HSP.
- **Scope:** TinyModel **routes and retrieves**; HSP + OpenAI **talk**; the app **executes** safe actions. Not full autonomy over wallet or chain.
- **Next (TinyModel):** maintain corpus, golden intents, production smoke, optional encoder fine-tune or UB deploy.
- **Next (product):** wire HSP `ai/transmitter.ts` and chat UI — TinyModel backend is ready; the interface is not.

*Update this note when Phase 2 HSP wiring ships or when the sidecar contract changes.*
