# HSP TinyModel sidecar — TypeScript reference modules

Copy into **Hyperlinks Space Program** when Phase 2 `ai/transmitter.ts` wiring begins. Mirrors `scripts/phase3_reference_server.py`, `scripts/hsp_intent_router.py`, and [`plan/07-ai-transmitter.md`](../../../plan/07-ai-transmitter.md).

| File | HSP target | Role |
| ---- | ---------- | ---- |
| `tinymodel-types.ts` | `ai/tinymodel-types.ts` | API + meta types |
| `tinymodel-client.ts` | `ai/tinymodel.ts` | `planRequest`, `getServiceMeta`, meta builders |
| `fallback-router.ts` | `ai/fallback-router.ts` | Heuristic routing when plan fails |
| `availability.ts` | `ai/availability.ts` | Sidecar health cache |
| `build-context.ts` | `ai/build-context.ts` | Generator context assembly |
| `composer.ts` | `ai/composer.ts` | Plan → Vercel AI model route (composer) |
| `composer-types.ts` | `ai/composer-types.ts` | Composer types |
| `vercel-ai-client.ts` | `ai/vercel-ai-client.ts` | Vercel AI SDK params + provider priority |
| `transmitter.ts` | `ai/transmitter.ts` | **Replace legacy OpenAI-only transmitter** |

**Composer plan (robust):** [`../composer/README.md`](../composer/README.md)

**Provider priority:** `AI_PROVIDER=hybrid` (default) → TinyModel plan + **Vercel AI SDK** (`streamText` / AI Gateway). Legacy `AI_PROVIDER=openai` → old path until HSP migrates.

**Env:** `TINYMODEL_API_URL` (default `http://127.0.0.1:8765`).

**Gates (TinyModel repo):**

```bash
python scripts/hsp_reference_client_smoke.py --verify
python scripts/hsp_reference_transmitter_smoke.py --verify
python scripts/hsp_composer_smoke.py --verify
python scripts/hsp_vercel_ai_transmitter_smoke.py --verify
python scripts/hsp_integration_smoke.py --verify
python scripts/hsp_integration_smoke.py --verify --production   # + Railway probe
```
