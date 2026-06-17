# Phased delivery plan

Phases are **ordered** but some HSP UI work can overlap backend wiring. Each phase has **exit criteria**—do not mark done without verify.

---

## Phase 0 — Corpus & contracts

**Goal:** Shared language between repos; regression data exists.

| Owner | Work | Status |
| ----- | ---- | ------ |
| TinyModel | `texts/hsp_program_corpus.md`, golden `hsp_intents.jsonl`, eval runner | **Done** |
| TinyModel | `plan/` folder (this document set) | **Done** |
| HSP | `docs/ai-tinymodel-integration.md` pointer to TinyModel `plan/` | Todo |
| HSP | `.env.example`: `TINYMODEL_API_URL`, `AI_PROVIDER`, optional `UB_CHAT_URL` | Todo |

**Exit:** `python scripts/hsp_integration_smoke.py --verify` green on TinyModel `main`.

---

## Phase 1 — Encoder sidecar (control plane)

**Goal:** HSP API can call TinyModel for plan/RAG without UI changes.

| Owner | Work | Status |
| ----- | ---- | ------ |
| TinyModel | `phase3_reference_server.py` — `/v1/classify`, `/retrieve`, `/plan` | **Done** |
| TinyModel | Reference TS client `integrations/hsp/reference/` | **Done** |
| Ops | Deploy sidecar to **Railway** (or Fly); `GET /healthz` | Todo |
| HSP | Copy/adapt `tinymodel-client.ts` → `ai/tinymodel.ts` | Todo |
| HSP | `/api/ai` calls `planRequest`; log `meta.tinymodel` | Todo |

**Exit:**

- `curl $TINYMODEL_API_URL/v1/plan -d '{"text":"open swap page"}'` → `actions` + `intent`
- HSP staging logs show `meta.tinymodel` on real requests

**TinyModel verify:**

```bash
python scripts/hsp_integration_smoke.py --verify --full
```

---

## Phase 2 — Hybrid transmitter (universal chat backend)

**Goal:** One `/api/ai` path merges TinyModel control plane + OpenAI (or UB) generation.

| Owner | Work | Status |
| ----- | ---- | ------ |
| HSP | Refactor `ai/transmitter.ts`: `AI_PROVIDER=hybrid` | Todo |
| HSP | `buildContext()`: thread + RAG + screen context + NL overlays | Todo |
| HSP | Return `actions[]` + `output_text` + `meta` | Todo |
| HSP | `/api/ai/stream` (mirror bot `transmitStream`) | Todo |
| TinyModel | Keep golden prompts ≥95% pass on router changes | Ongoing |

**Exit:**

- “Open swap and explain slippage” → navigate + coherent reply
- “What is this?” on `/shield` → `explain_screen` + Shield corpus citation
- `token_info` still uses Swap.Coffee

**Env:**

```bash
AI_PROVIDER=hybrid
TINYMODEL_API_URL=https://tinymodel-production.up.railway.app
OPENAI_API_KEY=...
```

---

## Phase 3 — Chat UI + action executor (product face)

**Goal:** User sees universal chat and feels the program move.

| Owner | Work | Status |
| ----- | ---- | ------ |
| HSP | Replace stub `app/(app)/ai.tsx` with streaming chat | Todo |
| HSP | GlobalBottomBar → POST `/api/ai` with full `context` | Todo |
| HSP | `applyAiActions()` on client (navigate, features) | Todo |
| HSP | Wide layout: inline chat column | Todo |
| TinyModel | Optional: UB deploy with HSP `--rag-corpus` | Todo |

**Exit:**

- Manual QA script: 10 flows in [03-interface-control.md](03-interface-control.md) work on web + TMA
- No regression on `hsp_intents` golden set

---

## Phase 4 — Full Universal Brain tier (optional scale-up)

**Goal:** Summarize/reformulate/memory without sending every turn to OpenAI.

| Owner | Work | Status |
| ----- | ---- | ------ |
| TinyModel | `build_space_artifact.py` with HSP corpus | Todo |
| Ops | UB on Railway/Fly; `UB_CHAT_URL` | Todo |
| HSP | Route “soft” chat to UB; keep OpenAI for hard/token | Todo |

**Exit:** Parity on internal eval for summarize/reformulate; cost/latency report documented.

---

## Phase 5 — Self-improvement loop (ongoing)

| Work | Gate |
| ---- | ---- |
| Nightly `ub_eval_runner` on HSP intents | ≥95% pass |
| Thumbs → JSONL review | Horizon 11 pattern |
| Corpus version pin in HSP `tinymodelCorpusVersion` | Drift detection |

---

## Suggested calendar (indicative)

| Weeks | Focus |
| ----- | ----- |
| 1–2 | Phase 1 ops + HSP `tinymodel.ts` + meta logging |
| 3–5 | Phase 2 hybrid transmitter + stream endpoint |
| 6–9 | Phase 3 chat UI + action executor |
| 10+ | Phase 4 UB host; Phase 5 automation |

Adjust for HSP UI readiness—backend Phases 1–2 do not require finished GlobalBottomBar UI.

---

## Repo checklist summary

**TinyModel (mostly Phase 0–1 complete)**

- [x] Corpus + smokes
- [x] `/v1/plan` + screen context
- [x] TS reference client
- [x] `plan/` documentation
- [ ] Railway deploy recipe in CI or `plan/05-deployment.md` automation script
- [ ] UB artifact with HSP corpus (Phase 4)

**Hyperlinks Space Program**

- [ ] `ai/tinymodel.ts` from reference
- [ ] Hybrid `transmitter.ts`
- [ ] `/api/ai` + stream + `actions[]`
- [ ] Chat UI + executor
- [ ] Context from router on every request
