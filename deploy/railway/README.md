# Railway — TinyModel HSP sidecar

Production URL: **https://tinymodel.hyperlinks.space**

Serves `phase3_reference_server.py` (`GET /healthz`, `POST /v1/plan`, classify, retrieve).

---

## One-time setup (already done if domain shows in `railway status`)

1. **Link repo** (from TinyModel root):
   ```bash
   railway link
   # Project: HSP → Service: TinyModel
   ```

2. **Custom domain** (Railway dashboard → TinyModel → Settings → Networking):
   - Domain: `tinymodel.hyperlinks.space`
   - DNS: CNAME `tinymodel` → Railway target (or use Railway DNS integration)

3. **Recommended variables** (Railway → TinyModel → Variables):
   ```bash
   TINYMODEL_PATH=HyperlinksSpace/TinyModel1
   TINYMODEL_HSP_CORPUS=/app/texts/hsp_program_corpus.md
   HOST=0.0.0.0
   # optional — faster Hub downloads / higher rate limits
   HF_TOKEN=hf_...
   ```

   `PORT` is set automatically by Railway.

4. **Resources** (Settings → Resources):
   - **CPU:** 2 vCPU recommended (first deploy downloads ~100MB model)
   - **RAM:** 2–4 GB (PyTorch + TinyModel1 on CPU)
   - **Health check:** path `/healthz`, timeout **300s** (cold start loads weights)

---

## Deploy

From repository root (after `git push` or local):

```bash
railway up --detach
```

Or connect **GitHub** in Railway → TinyModel → Settings → Source → deploy on push to `main`.

Build uses root **`Dockerfile`** and **`railway.toml`**.

---

## Verify production

```bash
curl -sS https://tinymodel.hyperlinks.space/healthz
curl -sS -X POST https://tinymodel.hyperlinks.space/v1/plan \
  -H 'Content-Type: application/json' \
  -d '{"text":"open swap page"}'

python scripts/hsp_railway_deploy_smoke.py --verify
python scripts/hsp_railway_deploy_smoke.py --verify --base-url https://tinymodel.hyperlinks.space
```

OpenAPI: https://tinymodel.hyperlinks.space/docs

---

## Wire Hyperlinks Space Program

On **Vercel** (HSP API), set:

```bash
TINYMODEL_API_URL=https://tinymodel.hyperlinks.space
AI_PROVIDER=hybrid
```

Copy client from [`integrations/hsp/reference/`](../../integrations/hsp/reference/) into `ai/tinymodel.ts`. See [`plan/07-ai-transmitter.md`](../../plan/07-ai-transmitter.md).

**Do not** expose the sidecar URL to the mobile client — only server-side `transmitter.ts` calls it.

---

## Troubleshooting

| Symptom | Fix |
| ------- | --- |
| 502 / deploy crash | Check logs: `railway logs`; increase RAM; set `HF_TOKEN` |
| Slow first request | Normal — Hub model download on cold start; keep 1 replica warm |
| `/v1/plan` 400 no corpus | Redeploy latest Docker image (`railway up`); logs must show `Loaded HSP corpus` |
| Health check fails | Increase timeout to 300s; first boot can take 2–3 min |

```bash
railway logs --service TinyModel
railway redeploy
```

---

## Files in this repo

| File | Role |
| ---- | ---- |
| `Dockerfile` | Image: Python 3.11, torch CPU, scripts, HSP corpus |
| `requirements-railway.txt` | Pip deps for sidecar |
| `railway.toml` | Build + health check config |
| `.dockerignore` | Smaller build context |
| `scripts/hsp_railway_deploy_smoke.py` | Post-deploy HTTP verify |
