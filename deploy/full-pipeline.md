# Full deploy pipeline: Kaggle → Hugging Face → Railway → HSP (Vercel)

**Goal:** train (optional) → publish weights → serve sidecar → wire HSP API.

**Current production:** https://tinymodel.hyperlinks.space (uses `HyperlinksSpace/TinyModel1` from Hub).

---

## Overview

```text
Step 1  GitHub secrets          (Kaggle + HF)     — skip if reusing TinyModel1
Step 2  Train on Kaggle         (GitHub Action)   — optional
Step 3  Weights on Hugging Face Hub               — TinyModel1 or TinyModel{N}
Step 4  Railway env + deploy    (Docker sidecar)
Step 5  Verify                  (smoke scripts)
Step 6  HSP Vercel env          (when HSP UI ready)
```

---

## Fast path (no retrain)

If **`HyperlinksSpace/TinyModel1`** is good enough (it is today):

1. Skip Steps 1–2.
2. Do **Step 4** (Railway login + `railway up --detach`).
3. Do **Step 5** (`hsp_railway_deploy_smoke.py --verify`).

---

## Step 1 — GitHub Actions secrets ⛔ STOP if missing

**Where:** https://github.com/HyperlinksSpace/TinyModel/settings/secrets/actions

| Secret | Required for | How to get |
| ------ | ------------- | ---------- |
| `KAGGLE_USERNAME` | Kaggle train workflow | [kaggle.com/settings](https://www.kaggle.com/settings) → API → username |
| `KAGGLE_KEY` | Kaggle train workflow | Same page → **Create New Token** |
| `HF_TOKEN` | Publish to Hub (+ optional Railway Hub pull) | [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) → **Write** token |

**Verify:** Repo → Actions → run **“Train via Kaggle and publish versioned model to Hugging Face”** — it fails immediately if secrets are missing.

**Do not continue to Step 2 until all three exist** (or use fast path above).

---

## Step 2 — Train on Kaggle (GitHub Action)

**Workflow:** `.github/workflows/train-via-kaggle-to-hf.yml`

1. GitHub → **Actions** → **Train via Kaggle and publish versioned model to Hugging Face** → **Run workflow**
2. Suggested inputs (first run or refresh):

   | Input | Suggested |
   | ----- | --------- |
   | `version` | `1` (→ repo `TinyModel1`) or `2` for new |
   | `namespace` | `HyperlinksSpace` |
   | `max_train_samples` | `3000` |
   | `max_eval_samples` | `600` |
   | `epochs` | `2` |
   | `batch_size` | `16` |
   | `learning_rate` | `1e-4` |

3. Wait **~30–90 min** (GPU kernel + upload to Hub).
4. Confirm model: https://huggingface.co/HyperlinksSpace/TinyModel{N}

**If you publish `TinyModel2`:** set Railway `TINYMODEL_PATH=HyperlinksSpace/TinyModel2` before Step 4.

---

## Step 3 — Hugging Face Hub (automatic after Step 2)

No manual step if the workflow succeeded. Optional:

```bash
python -c "from huggingface_hub import model_info; print(model_info('HyperlinksSpace/TinyModel1').modelId)"
```

---

## Step 4 — Railway deploy ⛔ STOP — login + env required

### 4a. CLI login (your machine)

```bash
cd /path/to/TinyModel
railway login
railway link
# Project: HSP → Service: TinyModel → Environment: production
```

### 4b. Railway variables ⛔ STOP if not set

**Where:** Railway dashboard → project **HSP** → service **TinyModel** → **Variables**

| Variable | Value | Required |
| -------- | ----- | -------- |
| `TINYMODEL_PATH` | `HyperlinksSpace/TinyModel1` | Yes |
| `TINYMODEL_HSP_CORPUS` | `/app/texts/hsp_program_corpus.md` | Yes |
| `HOST` | `0.0.0.0` | Yes |
| `HF_TOKEN` | `hf_...` | Recommended (faster Hub downloads, private models) |
| `PORT` | *(auto)* | Railway sets this |

**Resources:** 2 vCPU, 2–4 GB RAM. Health check path `/healthz`, timeout **300s**.

### 4c. Deploy

```bash
railway up --detach
```

Or: Railway → **Deploy** from GitHub `main` if source is connected.

Build uses root `Dockerfile` + `railway.toml`.

---

## Step 5 — Verify production

```bash
curl -sS https://tinymodel.hyperlinks.space/healthz
curl -sS https://tinymodel.hyperlinks.space/v1/meta
curl -sS -X POST https://tinymodel.hyperlinks.space/v1/plan \
  -H 'Content-Type: application/json' \
  -d '{"text":"open swap page"}'

python scripts/hsp_railway_deploy_smoke.py --verify
python scripts/hsp_integration_smoke.py --verify --production
```

Expect: `healthz` → `{"status":"ok"}`, plan → `navigate:/swap`, smoke **5/5**.

---

## Step 6 — HSP on Vercel ⛔ STOP — when HSP repo is ready

**Not in TinyModel repo.** Copy `integrations/hsp/reference/*` → HSP `ai/`.

**Vercel env (HSP project):**

| Variable | Value |
| -------- | ----- |
| `TINYMODEL_API_URL` | `https://tinymodel.hyperlinks.space` |
| `AI_PROVIDER` | `hybrid` |
| `AI_COMPOSER_QUALITY_MODEL` | `openai/gpt-4.1-mini` (or gateway model id) |
| `AI_COMPOSER_FAST_MODEL` | `openai/gpt-4.1-nano` |
| `OPENAI_API_KEY` | *(legacy fallback only if `AI_PROVIDER=openai`)* |

Vercel AI Gateway auth is automatic on Vercel when using the `ai` package.

See [`integrations/hsp/composer/README.md`](../integrations/hsp/composer/README.md).

---

## Troubleshooting

| Issue | Fix |
| ----- | --- |
| Kaggle workflow: missing secrets | Complete Step 1 |
| Kaggle kernel timeout | Re-run workflow; reduce samples or epochs |
| Railway Unauthorized | `railway login` |
| `/v1/plan` 400 no corpus | Redeploy; logs must show `Loaded HSP corpus` |
| Slow first request | Normal cold start; keep 1 replica |
| New Hub model not used | Update `TINYMODEL_PATH` + redeploy Railway |

---

## Checklist (printable)

- [ ] Step 1: `KAGGLE_USERNAME`, `KAGGLE_KEY`, `HF_TOKEN` in GitHub (or skip retrain)
- [ ] Step 2: Kaggle workflow green (or skip)
- [ ] Step 4b: Railway variables set
- [ ] Step 4c: `railway up --detach` or GitHub deploy
- [ ] Step 5: `hsp_railway_deploy_smoke.py --verify` OK
- [ ] Step 6: HSP Vercel env (later)
