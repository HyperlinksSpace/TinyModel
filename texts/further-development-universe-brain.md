# Further development plan: toward a “universe brain” (north star)

This file is a **long-horizon** plan—separate from the **near-term engineering** checklist in [`further-development-plan.md`](further-development-plan.md) (Phases 1–3: baselines, eval quality, ONNX, serving). It also extends the commercial ladder in [`commercial-models-and-artificial-brain-roadmap.md`](commercial-models-and-artificial-brain-roadmap.md).

**“Universe brain”** here means an **integrated, growing system** that can **perceive** many signal types, **remember** and **retrieve** over time, **reason** with tools and constraints, and **act** in governed ways—**not** a claim of full human-level AGI or a single model that “knows everything.” It is a **design target** for multi-year R&D and selective products.

---

## How this document relates to the rest of the repo

| Document | Role |
| -------- | ---- |
| [`further-development-plan.md`](further-development-plan.md) | Concrete **Phases 1–3**: comparison matrix, eval artifacts, ONNX, benchmarks, reference API—**ship-shaped** work. |
| [`commercial-models-and-artificial-brain-roadmap.md`](commercial-models-and-artificial-brain-roadmap.md) | **Market-realistic** ladder from small encoder → LLM → multimodal; what companies pay for. |
| **This file** | **Vision + staged capabilities** toward a unified “brain-like” stack: what to build **after** the encoder line is mature, with **horizons** and **gates**. |

---

## Definition: what would make the line “brain-like”

Decompose the metaphor into **testable capabilities** (inspired by perception / memory / reasoning / action / alignment):

1. **Perception** — stable handling of text, structured data, and eventually image/audio with a **unified contract** (same eval, same safety hooks).
2. **Memory** — not just weights: **external** memory (RAG, knowledge graphs), **session** state, and optional **long-horizon** user memory with consent and deletion.
3. **World model (bounded)** — expectations about how environments change: from **task statistics** (your data) to **simulation priors** in narrow domains—not a literal model of the entire physical universe.
4. **Agency** — tool use, APIs, workflows, and (where allowed) **side effects** under **policy** and **audit logs**.
5. **Alignment & oversight** — eval suites, red-teaming, monitoring, human escalation—**baked in**, not bolted on after launch.

None of these are “ship one binary called brain.exe.” They are **properties of a system** you grow over years.

---

## Short-term horizon: time for the next step (toward Horizon 1)

The long **Horizons** below are deliberately **not** dated. This block is a **separate, short-term** schedule for the **next** work: moving from a solid **Horizon 0** line to the **start** of **Horizon 1** (multi-task text, shared eval, RAG-shaped prototype)—without conflating that with the multi-year “universe” tail.

| Window | Target | What to deliver (outcomes) | Rough time |
| ------ | ------ | -------------------------- | ---------- |
| **A — Baseline closure** | Prove the **tactical** plan is shippable end-to-end. | CI green on `phase1-smoke` + `phase3-smoke` on the default branch; optional **one** `dev` or `full` `phase1_compare` run recorded for posterity. | **~0.5 week** (mostly CI + documentation / flake fixes). |
| **B — Data + eval breadth** | Single team, **more than one** serious task in the same harness. | At least **three** distinct dataset/task runs (e.g. AG News, Emotion, SST-2) with comparable `eval_report.json` + error artifacts; one **short** write-up of confusions and calibration. | **~1–2 weeks** (data pulls, re-runs, light analysis). |
| **C — Routing + retrieval as product** | First-class **routing/retrieve** path, not only scripts. | Documented path from `TinyModelRuntime` (or equivalent) to a **concrete** integration story: minimal **RAG** or **FAQ retrieval** over a small corpus, with chunking + one **faithfulness** or **citation** check in eval—not production-scale, but **repeatable**. | **~1–2 weeks** (depends on corpus choice). |
| **D — Generative hook (optional in this tranche)** | Bridge toward Horizon 2 **only if** A–C are stable. | One **spike**: call or host a small **open** LLM for **one** task (summarization or reformulation) with the **same** logging/eval contract as the encoder line; or defer to the next tranche. | **~0.5–1 week** if scoped tiny; else **out of band**. |

**Combined short-term envelope:** about **3–5 calendar weeks** for **A + B + C** in parallel where possible, **+0.5–1 week** if you include **D** in the same release train. Re-estimate if you add headcount, freeze datasets, or expand RAG scope.

**Implemented scripts and manual test flow (A–C):** see [`horizon1-short-term-handbook.md`](horizon1-short-term-handbook.md)—**A** `scripts/horizon1_verify_short_term_a.py`, **B** `scripts/horizon1_three_datasets.py` (optional `--offline-datasets` when the Hub is flaky), **C** `scripts/rag_faq_smoke.py` with [`rag_faq_corpus.md`](rag_faq_corpus.md). A compact per-task table from B is [`horizon1-three-tasks-summary.md`](horizon1-three-tasks-summary.md).

**Immediate next action (this week):** run the **verification** table in [`further-development-plan.md`](further-development-plan.md) (Phases 1–3) on a **fresh** checkpoint so `eval_report.json` includes all Phase 2 fields; then pick **B** (which datasets first) in a 30-line decision note (even in the repo or in your tracker).

---

## Horizons (time-agnostic; each can take many calendar months)

### Horizon 0 — **Grounded product (today’s line)**

**State:** small encoders, classification, embeddings, Phase 3 packaging, clear eval and serving notes.

**Exit (already aligned with `further-development-plan.md`):** reproducible training, ONNX path, benchmark report, reference API doc.

---

### Horizon 1 — **Multi-task text intelligence (single org, many tasks)**

**Goal:** one **style** of training and eval across **many** datasets and label schemas; routing and retrieval as **first-class** products.

- Unified **data versioning**, **label governance**, and **per-task** metrics.
- **Instruction-shaped** or **prompt-shaped** interfaces on top of encoders (even before a full LLM).
- **RAG** templates: chunking, citation, faithfulness checks.

**Exit criteria**

- At least **N** distinct tasks (e.g. classification + retrieval + light extraction) sharing one **runtime** and **observability** story.
- Documented **failure modes** and **rollback** for production.

---

### Horizon 2 — **Generative core (decoder or API LLM)**

**Goal:** move from “predict a label” to **generate** under constraints: summaries, drafts, chat-shaped UIs—using **open** or **hosted** LLMs plus your data and eval harness.

- **PEFT** (LoRA, etc.) on mid-size models where cost allows.
- **SFT** on instruction–response data; optional **preference** alignment if quality demands.

**Exit criteria**

- **Side-by-side** eval vs. human or strong baseline on **domain** tasks.
- **Latency and cost** envelopes documented per **tier** (CPU small model vs. GPU vs. API).

**Implemented in this repository (MVP, local weights + JSON runs):** [`texts/horizon2-handbook.md`](horizon2-handbook.md) — `scripts/horizon2_core.py` (prompts, generation), `scripts/horizon2_generative.py` (CLI, `--verify`, optional `--compare-with`), `scripts/horizon2_server.py` (optional FastAPI; install Phase 3 style deps for HTTP), `optional-requirements-horizon2.txt`, and `.github/workflows/horizon2-smoke.yml` (runs `python scripts/horizon2_generative.py --verify`).

---

### Horizon 3 — **Persistent mind (memory + continuity)**

**Goal:** user- or org-level **memory** that is **editable**, **auditable**, and **deletable**—not an opaque vector dump.

- Explicit **memory policies** (what is stored, TTL, jurisdiction).
- **Conflict resolution** when new evidence contradicts old retrieved memory.
- **Session + long-term** separation; “forget me” paths.

**Exit criteria**

- Privacy review artifacts; **DSR** (access/delete) story for stored memory.
- Measured **utility** (e.g. retrieval hit rate, task success) vs. **risk** (leakage tests).

**Implemented in this repository (MVP, local SQLite + audit):** [`texts/horizon3-handbook.md`](horizon3-handbook.md) — `scripts/horizon3_store.py` (session vs long-term, TTL, prune, export, forget), `scripts/horizon3_memory_cli.py` (`--verify`), optional `scripts/horizon3_memory_api.py` (FastAPI), `optional-requirements-horizon3.txt`, and `.github/workflows/horizon3-smoke.yml`.

---

### Horizon 4 — **Multimodal grounding**

**Goal:** condition on **images and/or audio** where the product needs them, using **fusion** architectures or **orchestrated** specialists under one policy layer.

- Shared **safety and moderation** across modalities.
- **Evaluation** that is multimodal (not only text sidecars).

**Exit criteria**

- **Benchmark slice** (internal or public) for each modality you ship.
- **Abuse and bias** review before broad launch.

**Implemented in this repository (MVP, image + text only):** [`texts/horizon4-handbook.md`](horizon4-handbook.md) — `scripts/horizon4_multimodal.py` (CLIP-style alignment, JSON `horizon4_multimodal_run/1.0`), `optional-requirements-horizon4.txt` (Pillow), and `.github/workflows/horizon4-smoke.yml` (offline `python scripts/horizon4_multimodal.py --verify` using a synthetic random `CLIPConfig` + `CLIPModel`). Pretrained CLIP and manual `--verify-pretrained` are documented in the handbook; audio and production moderation are out of scope for this file.

---

### Horizon 5 — **“Universe” scale (selective, lab-heavy)**

**Goal:** only where **ethics, budget, and regulation** allow—push the envelope on **continual learning**, **larger world models in simulators**, or **embodied** prototypes. Treat as **R&D and selective products** (per the commercial roadmap), not a default product promise.

**Exit criteria**

- **Publication-level** clarity on **limitations**; no silent production drift.
- **Kill criteria** if reliability or safety regress beyond agreed thresholds.

---

## Decision gates (before funding each jump)

1. **Evidence gate** — the previous horizon’s metrics and incident data justify the next **scope** increase.
2. **Safety gate** — new modalities or memory types pass **threat models** and **red-team** bar for the intended user class.
3. **Economics gate** — **unit economics** (inference, storage, support) are modeled for the **smallest** viable deployment, not only demos.
4. **Operations gate** — runbooks, on-call, and **rollback** for model + memory + tool versions.

---

## What to do next in practice (from where TinyModel sits)

Short list that connects **this** repo to **Horizon 1** without waiting for a “brain” label:

- **Harden data + eval** across more tasks; treat [`further-development-plan.md`](further-development-plan.md) as the **tactical** spine.
- **Prototyping lane:** follow [`optional-rd-backlog.md`](optional-rd-backlog.md) for spikes (PEFT, retrieval pooling, etc.).
- **System thinking:** as soon as you add an LLM, invest in **RAG, policies, and logs** in parallel with weights—not after.

---

## Open risks (explicit)

- **Over-promising** “universe” or “brain” externally while the stack is still a **specialized text pipeline**—**avoid**; use this doc **internally** for alignment.
- **Memory + agency** without **security** and **governance** invite incidents; **Horizon 3** is not “more parameters,” it is **more responsibility**.
- **Scope creep** across horizons without **gates** burns budget; sequence matters.

---

*This is a **planning** artifact, not a release commitment, a valuation narrative, or a claim of AGI. Revise as evidence and product strategy change.*
