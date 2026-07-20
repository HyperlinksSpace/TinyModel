# Hyperlinks Space Program × Universal Brain — master plan

This folder is the **single entry point** for shipping **universal in-app chat** in Hyperlinks Space Program (HSP) with **interface control** (navigate, explain screen, prefill flows)—not a separate chat tab that only talks.

**North star:** one **GlobalBottomBar** input → answers **and** the next in-app action when safe.

**Repos**

| Repo | Role |
| ---- | ---- |
| **TinyModel** (this repo) | Encoder sidecar, HSP corpus, golden prompts, UB artifact, verify gates, reference TS client |
| **HyperlinksSpaceProgram** | Product shell: `/api/ai`, `ai/transmitter.ts`, chat UI, `actions[]` executor |

**Related docs (detail)**

- [`texts/hsp-tinymodel-integration-strategy.md`](../texts/hsp-tinymodel-integration-strategy.md) — long-form strategy
- [`texts/hsp-huggingface-space-responses.md`](../texts/hsp-huggingface-space-responses.md) — HF Space vs self-host
- [`texts/hsp-sidecar-meta.md`](../texts/hsp-sidecar-meta.md) — `meta.tinymodel` contract
- [`integrations/hsp/reference/`](../integrations/hsp/reference/) — copy-paste TS client for HSP

---

## Plan documents

| Doc | Contents |
| --- | -------- |
| [01-vision.md](01-vision.md) | What “universal chat + UI control” means (and does not mean) |
| [02-architecture.md](02-architecture.md) | Hybrid control plane, services, request/response shape |
| [03-interface-control.md](03-interface-control.md) | Intents, `actions[]`, screen context, safety rules |
| [04-phases.md](04-phases.md) | Phased delivery, owners, exit criteria |
| [05-deployment.md](05-deployment.md) | Railway (`tinymodel.hyperlinks.space`), Vercel, HF Space |
| [06-verify-gates.md](06-verify-gates.md) | Commands that must pass before each phase ships |
| [07-ai-transmitter.md](07-ai-transmitter.md) | **AI Transmitter** — per-prompt routing, availability fallbacks, generators |
| [Composer plan](../integrations/hsp/composer/README.md) | **AI Composer** — TinyModel plan → Vercel AI SDK model routing |

---

## Status snapshot (TinyModel)

| Phase | TinyModel | HSP |
| ----- | --------- | --- |
| **0** Corpus & contracts | Done | Pending docs/env |
| **1** Encoder sidecar (`/v1/plan`) | **Done** (Railway live) | Not wired |
| **2** Hybrid `transmitter` + meta | **Composer prep done** (Vercel AI routing reference) | Not started |
| **3** Full UB chat service | Artifact exists; deploy optional | Not started |
| **4** Chat UI + action executor | N/A | Not started |

**One-command verify (TinyModel):**

```bash
python scripts/hsp_integration_smoke.py --verify          # stdlib (11 gates)
python scripts/hsp_integration_smoke.py --verify --full     # + torch + live HTTP
```

---

## 90-day priority (both repos)

1. **HSP** — Real chat panel; bottom bar → `POST /api/ai` (stream); apply `actions[]`.
2. **Both** — Hybrid provider: TinyModel `plan` + OpenAI answer + Swap.Coffee `token_info`.
3. **Ops** — TinyModel sidecar on **Railway**; HSP API calls it server-side only.
4. **TinyModel** — UB on Railway/Fly with **HSP corpus** when you need summarize/reformulate without OpenAI.
5. **Both** — Golden intents in CI; log `meta.tinymodel` until UI is stable.

See [04-phases.md](04-phases.md) for full timeline.
