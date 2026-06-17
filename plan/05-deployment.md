# Deployment topology

## Recommended production layout

```text
                    ┌─────────────────────────────────┐
                    │  Vercel — Hyperlinks Space API   │
                    │  /api/ai  /api/auth  /api/…    │
                    │  ai/transmitter.ts (hybrid)      │
                    └───────────┬─────────────────────┘
                                │ server-side only
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                 ▼
     ┌────────────────┐ ┌──────────────┐ ┌─────────────┐
     │ Railway        │ │ OpenAI API   │ │ Swap.Coffee │
     │ TinyModel      │ │ gpt-5.2      │ │ token facts │
     │ phase3 :8765   │ └──────────────┘ └─────────────┘
     │ /v1/plan       │
     └────────┬───────┘
              │ pulls weights
              ▼
     ┌────────────────┐
     │ Hugging Face   │
     │ HyperlinksSpace│
     │ /TinyModel1    │
     └────────────────┘

Optional later:
     ┌────────────────┐
     │ Railway #2     │
     │ Universal Brain│
     │ UB_CHAT_URL    │
     └────────────────┘
```

**Never** call TinyModel or OpenAI from the mobile client directly—keys and corpus stay on the API.

---

## Service 1: TinyModel encoder sidecar (P0)

**Production:** https://tinymodel.hyperlinks.space (Railway project **HSP**, service **TinyModel**).

**Deploy guide:** [`deploy/railway/README.md`](../deploy/railway/README.md).

**What:** `scripts/phase3_reference_server.py`

**Railway setup (outline)**

1. Service linked to this repo; domain `tinymodel.hyperlinks.space` configured.
2. Deploy: `railway up --detach` (uses root `Dockerfile` + `railway.toml`).
3. Env:
   - `TINYMODEL_PATH=HyperlinksSpace/TinyModel1`
   - `TINYMODEL_HSP_CORPUS=/app/texts/hsp_program_corpus.md`
   - optional `HF_TOKEN`
4. Health check: `GET /healthz` (timeout 300s on first boot).
5. Verify: `python scripts/hsp_railway_deploy_smoke.py --verify`
6. HSP: `TINYMODEL_API_URL=https://tinymodel.hyperlinks.space`

**Resource hint:** CPU 1–2 vCPU, 2–4 GB RAM; first request loads HF weights (~tens of seconds).

**Alternative hosts:** Fly.io, GCP Cloud Run, same pattern as TDLib gateway.

---

## Service 2: HSP API (existing)

**Vercel** — no change to hosting; add env vars and longer timeout for AI routes if needed.

```bash
TINYMODEL_API_URL=https://tinymodel.hyperlinks.space
AI_PROVIDER=hybrid
OPENAI_API_KEY=sk-...
# optional
UB_CHAT_URL=https://<ub-service>.up.railway.app
```

Consider **keep-alive** ping to Railway from a cron if cold starts hurt UX.

---

## Service 3: Hugging Face Space (demo / fallback only)

| URL | Role |
| --- | ---- |
| [TinyModel1Space](https://huggingface.co/spaces/HyperlinksSpace/TinyModel1Space) | Public UB demo |
| Gradio `/gradio_api/call/chat` | Full chat, not `/v1/plan` |

**Use for:** internal demos, comparing reply quality, not primary HSP traffic.

**Upgrade path:** duplicate Space config on Railway with HSP corpus via `build_space_artifact.py`.

---

## Corpus sync

| Method | When |
| ------ | ---- |
| Sidecar bundles `texts/hsp_program_corpus.md` at deploy | Simplest |
| `python scripts/hsp_corpus_export.py` → commit or CI artifact | HSP static JSON fallback |
| Version field `tinymodelCorpusVersion` in HSP | Detect drift |

---

## Secrets & compliance

| Secret | Where |
| ------ | ----- |
| `OPENAI_API_KEY` | Vercel only |
| `TINYMODEL_*` | No secret for public weights; optional HF token on Railway for private models |
| User messages | Log policy on Vercel; do not log seeds/keys |

---

## Local dev (both repos)

```bash
# Terminal 1 — TinyModel
pip install -r optional-requirements-phase3.txt torch transformers
python scripts/phase3_reference_server.py --port 8765

# Terminal 2 — HSP
TINYMODEL_API_URL=http://127.0.0.1:8765 AI_PROVIDER=hybrid npm run dev:vercel
```

---

## Decision matrix

| Need | Deploy |
| ---- | ------ |
| Routing + RAG + `actions[]` | Railway **phase3** |
| Best reply quality today | OpenAI via **transmitter** |
| Summarize/reformulate without OpenAI | Railway **UB** (Phase 4) |
| Quick demo without ops | Public **HF Space** |
