# HSP TinyModel sidecar — TypeScript reference modules

Copy into **Hyperlinks Space Program** when Phase 2 `ai/transmitter.ts` wiring begins. Mirrors `scripts/phase3_reference_server.py`, `scripts/hsp_intent_router.py`, and [`plan/07-ai-transmitter.md`](../../../plan/07-ai-transmitter.md).

| File | HSP target | Role |
| ---- | ---------- | ---- |
| `tinymodel-types.ts` | `ai/tinymodel-types.ts` | API + meta types |
| `tinymodel-client.ts` | `ai/tinymodel.ts` | `planRequest`, `getServiceMeta`, meta builders |
| `fallback-router.ts` | `ai/fallback-router.ts` | Heuristic routing when plan fails |
| `availability.ts` | `ai/availability.ts` | Sidecar health cache |
| `build-context.ts` | `ai/build-context.ts` | Generator context assembly |

**Env:** `TINYMODEL_API_URL` (default `http://127.0.0.1:8765`).

**Gates (TinyModel repo):**

```bash
python scripts/hsp_reference_client_smoke.py --verify
python scripts/hsp_reference_transmitter_smoke.py --verify
python scripts/hsp_integration_smoke.py --verify
python scripts/hsp_integration_smoke.py --verify --production   # + Railway probe
```
