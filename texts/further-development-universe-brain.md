# Further development plan: toward a “universe brain” (north star)

This file is a **long-horizon** plan—separate from the **near-term engineering** checklist in [`further-development-plan.md`](further-development-plan.md) (Phases 1–3: baselines, eval quality, ONNX, serving). It also extends the commercial ladder in [`commercial-models-and-artificial-brain-roadmap.md`](commercial-models-and-artificial-brain-roadmap.md).

**“Universe brain”** here means an **integrated, growing system** that can **perceive** many signal types, **remember** and **retrieve** over time, **reason** with tools and constraints, and **act** in governed ways—**not** a claim of full human-level AGI or a single model that “knows everything.” It is a **design target** for multi-year R&D and selective products.

---

## How this document relates to the rest of the repo

| Document | Role |
| -------- | ---- |
| [`further-development-plan.md`](further-development-plan.md) | Concrete **Phases 1–3**: comparison matrix, eval artifacts, ONNX, benchmarks, reference API—**ship-shaped** work. |
| [`commercial-models-and-artificial-brain-roadmap.md`](commercial-models-and-artificial-brain-roadmap.md) | **Market-realistic** ladder from small encoder → LLM → multimodal; what companies pay for. |
| **This file** | **Vision + staged capabilities** toward a unified “brain-like” stack (Horizons **0–15**): through **H13** resilience, plus **H14** workflow DAGs and **H15** data-minimization exports—then product layers beyond this repo. |

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

**Implemented in this repository:** the **tactical** spine in [`further-development-plan.md`](further-development-plan.md) (Phases 1–3: training, eval reports, ONNX, packaging), plus CI on the default branch for the main smoke/verify paths. This horizon is the **foundation** for all later `horizonK-*` handbooks.

---

### Horizon 1 — **Multi-task text intelligence (single org, many tasks)**

**Goal:** one **style** of training and eval across **many** datasets and label schemas; routing and retrieval as **first-class** products.

- Unified **data versioning**, **label governance**, and **per-task** metrics.
- **Instruction-shaped** or **prompt-shaped** interfaces on top of encoders (even before a full LLM).
- **RAG** templates: chunking, citation, faithfulness checks.

**Exit criteria**

- At least **N** distinct tasks (e.g. classification + retrieval + light extraction) sharing one **runtime** and **observability** story.
- Documented **failure modes** and **rollback** for production.

**Implemented in this repository (MVP, short-term A–C, not the full H1 exit):** [`horizon1-short-term-handbook.md`](horizon1-short-term-handbook.md) — `scripts/horizon1_verify_short_term_a.py`, `scripts/horizon1_three_datasets.py`, `scripts/rag_faq_smoke.py` with [`rag_faq_corpus.md`](rag_faq_corpus.md). Full **H1 exit** (one production runtime, unified observability) is still a **target**; see the short-term block and [`further-development-plan.md`](further-development-plan.md).

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

**Remaining to reach full H4 exit (benchmark + governance):** a **multimodal eval slice** (internal or public) and an **abuse/bias** review before broad launch; shared **safety** hooks across text + image are **not** yet unified in this repo.

---

### Horizon 5 — **“Universe” scale (selective, lab-heavy)**

**Goal:** only where **ethics, budget, and regulation** allow—push the envelope on **continual learning**, **larger world models in simulators**, or **embodied** prototypes. Treat as **R&D and selective products** (per the commercial roadmap), not a default product promise.

**Exit criteria**

- **Publication-level** clarity on **limitations**; no silent production drift.
- **Kill criteria** if reliability or safety regress beyond agreed thresholds.

**In this repository:** **no** dedicated MVP (by design). Use [`optional-rd-backlog.md`](optional-rd-backlog.md) and the commercial ladder in [`commercial-models-and-artificial-brain-roadmap.md`](commercial-models-and-artificial-brain-roadmap.md) for **lab** spikes; pass **decision gates** before any product commitment.

---

### Horizon 6 — **Converged stack (orchestrated “brain” slice)**

**Goal:** after individual horizons have **credible** MVPs, **compose** them into **one** governed system—not a monolithic “brain” model, but a **routed** stack: the same **policy, audit, and observability** no matter which capability runs (classify, retrieve, generate, read/write memory, image–text score).

- **Routing** to the right sub-capability with explicit **deny/allow** and **logging**; **degradation** when a provider or model is down.
- **Single contract** for JSON/event logs and eval, so you can **reason** about end-to-end behavior in incidents.
- **Cost and latency** envelopes per path (CPU encoder vs. API LLM vs. CLIP, etc.).

**Exit criteria**

- **One** documented **end-to-end** path (scripts and/or a reference API) that exercises **at least three** of: encoder/classification, RAG, generative (H2), memory (H3), multimodal (H4).
- A **runbook** for common failures: retrieval empty, model timeout, memory quota, multimodal off.

**Implemented in this repository (MVP, thin orchestration):** `scripts/horizon6_converged_smoke.py` — `--verify` runs **H2** (`horizon2_generative.py --verify`), **H3** (`horizon3_memory_cli.py --verify`), and **H4** (`horizon4_multimodal.py --verify`) in sequence; writes `horizon6_converged_run/1.0` JSON under `.tmp/horizon6-converge/run.json`. Optional `--with-rag` appends `rag_faq_smoke.py` (needs a local encoder or Hub). **Not done yet vs. full exit:** a **single** production runtime, unified **routing** policy, and a written **runbook** beyond the chained verifiers.

---

### Horizon 7 — **Trust, scale, and ecosystem (assured platform)**

**Goal:** an H6-style stack is **internally** coherent; **broad** deployment needs **external** trust: **multi-tenant** isolation, **compliance** and **evidence** for buyers and regulators, and—where it makes sense—a **controlled ecosystem** (partners, registered tools) that still flows through **your** policy, audit, and logging—not ad hoc integrations.

- **Isolation** — strong **boundaries** between orgs/tenants for data, memory, and configuration; **blast-radius** limits when something fails.
- **Compliance & assurance** — **DSR**, retention, regional and **sector** playbooks as **product** artifacts, not one-off legal memos; paths to **external** review on a **defined** scope.
- **Ecosystem (optional)** — third-party capabilities exposed as **tools** under **contract** (schemas, timeouts, denylists), not arbitrary side effects.
- **Economics at scale** — **quotas**, tiers, and support boundaries tied to **observable** SLOs and cost visibility.

**Exit criteria**

- **Repeatable** onboarding of a **new** tenant (or large customer) **without** bespoke engineering for every deal.
- **Audit materials** and **incident** narrative that a **stakeholder** (customer security, regulator in bounded scope) can follow—**including** clear statements of what you **do not** claim.
- **No silent universality** — limits and **kill** criteria are **published** to customers, not only internal runbooks.

**Implemented in this repository (MVP, isolation demo only):** `scripts/horizon7_assured_smoke.py` — `--verify` uses two **separate** SQLite files with the **same** `scope_key` to show **no crosstalk** (export, `get`, `forget-scope`); writes `horizon7_assured_run/1.0` under `.tmp/horizon7-assured/run.json`. **Not done yet vs. full exit:** **multi-tenant** product **onboarding**, **regional** or **compliance** packs, **external** audit artifacts, **partner** ecosystem, **economics** — those remain org-level work, not a script.

---

### Horizon 8 — **Observability & probe bundle (signals for incidents)**

**Goal:** when something breaks in production, you need **one place** to see **what build**, **what environment**, and **which downstream checks** still pass—without replacing your APM vendor. **Correlate** probes (memory, tenant isolation, model smoke) with **git** identity and **platform** facts.

- **Structured** JSON snapshots suitable for log pipelines and post-incident review.
- **Synthetic** health that **re-runs** critical local verifiers (here: **H7** isolation) as a probe, not only HTTP pings.

**Exit criteria**

- **Dashboards** or **alerts** that consume these signals (outside this repo, or via your SIEM).
- **SLOs** per capability with **runbooks** tied to probe failure modes.

**Implemented in this repository (MVP):** `scripts/horizon8_observability_probe.py` — `--verify` records **Python / platform / optional `git rev`**, runs `horizon7_assured_smoke.py --verify` as a **dependency probe**, and writes `horizon8_probe_run/1.0` under `.tmp/horizon8-probe/run.json`. **Not done yet vs. full exit:** streaming metrics, **PagerDuty**/**Slack** wiring, **SLO** math, multi-region probes.

---

### Horizon 9 — **Declarative policy & capability gates**

**Goal:** **explicit** allow/deny for **named actions** (capabilities, tools, routes)—**deny wins** over allow, with a **default-deny** posture for anything not listed. Complements human review: the **contract** lives in **versioned** config, not only in code comments.

- **Policy-as-data** for staged rollouts (feature flags **and** safety).
- **Audit** of who changed policy and when (product concern; this repo ships a **sample** JSON only).

**Exit criteria**

- **Central** policy service or **signed** bundles in production; **break-glass** paths documented.
- **Tests** that fail CI if a **forbidden** action becomes **allowed** by accident.

**Implemented in this repository (MVP):** `texts/horizon9_policy_sample.json` + `scripts/horizon9_policy_smoke.py` — `--verify` evaluates the sample matrix (deny precedence, collision case) and writes `horizon9_policy_run/1.0` under `.tmp/horizon9-policy/run.json`. **Not done yet vs. full exit:** **identity**, **attribute-based** rules, **O**Auth/**OPA**, **signed** policy bundles, **tamper-evident** audit.

---

### Horizon 10 — **Resource & cost envelopes (FinOps-shaped guardrails)**

**Goal:** tie **named actions** to **abstract units** (tokens, calls, normalized dollars) and **enforce caps** before work hits GPUs or APIs—so surprise bills become **configuration errors**, not silent debt.

- **Per-window** budgets aligned with **policy** (H9); deny/throttle when **spend** would exceed **cap**.
- **Metering hooks** in real products push usage into billing systems; this repo only proves **arithmetic + contracts**.

**Exit criteria**

- **Live** metering connected to **payment** or **quota** tiers; alerts before hard deny where appropriate.

**Implemented in this repository (MVP):** `texts/horizon10_budget_sample.json` + `scripts/horizon10_budget_smoke.py` — `--verify` simulates cumulative **units** vs `max_units_per_window` and writes `horizon10_budget_run/1.0` under `.tmp/horizon10-budget/run.json`. **Not done yet vs. full exit:** **distributed** counters, **Redis**/streaming usage, **invoice** reconciliation.

---

### Horizon 11 — **Human outcome capture (feedback loop)**

**Goal:** capture **corrections** and **labels** from operators or users in a **machine-ingestible**, **auditable** format so models and policies can improve—without stuffing feedback only into Slack threads.

- **Append-only** or **versioned** stores with **PIR/privacy** rules on sensitive fields.
- **Join keys** back to predictions and training pipelines.

**Exit criteria**

- **Regular** export into **training** or **eval** loops with governance sign-off.

**Implemented in this repository (MVP):** `scripts/horizon11_feedback_smoke.py` — `--verify` writes validated **JSONL** (`horizon11_feedback_record/1.0` fields per line) under `.tmp/horizon11-feedback/` and writes `horizon11_feedback_run/1.0`. **Not done yet vs. full exit:** **secure** ingestion, **PII** scrubbing, **identity** on reviewers, **automated** train triggers.

---

### Horizon 12 — **Provenance & integrity manifest (supply-chain shaped)**

**Goal:** ship **fingerprints** (hashes) for **pinned** configs and artifacts so CI and auditors can detect **tampering** or **drift** without trusting a single opaque binary. Pairs with signed releases in mature orgs.

- **Extend** with **Sigstore**, **in-toto**, or **SBOM** links in production.

**Exit criteria**

- **Signed** attestations or **immutable** build provenance for every **release** artifact.

**Implemented in this repository (MVP):** `scripts/horizon12_provenance_smoke.py` — `--verify` computes **SHA-256** for pinned `texts/*.json` policy/budget samples and writes `horizon12_provenance_run/1.0` under `.tmp/horizon12-provenance/run.json`. **Not done yet vs. full exit:** **signing**, **timestamping**, **registry** integration.

---

### Horizon 13 — **Resilience: circuit breaker (dependency hardening)**

**Goal:** stop **cascading failures** when an **LLM**, **DB**, or **tool** is unhealthy: **fail fast** after repeated errors, **recover** cautiously (**half-open** probe), then resume. Complements **H8** probes and **H10** budgets.

- **Production** adds **timeouts**, **jitter**, **per-tenant** breakers, and **metrics**.

**Exit criteria**

- **Measured** error budget and **SLO** for dependency **availability**; **playbooks** for **OPEN** state.

**Implemented in this repository (MVP):** `scripts/horizon13_circuit_smoke.py` — `--verify` drives a tiny **CLOSED → OPEN → HALF_OPEN → CLOSED** state machine and writes `horizon13_circuit_run/1.0` under `.tmp/horizon13-circuit/run.json`. **Not done yet vs. full exit:** **async** integration, **distributed** coordination, **live** traffic metrics.

---

### Horizon 14 — **Orchestrated workflows (DAG execution)**

**Goal:** complex AI products are **graphs** of steps (retrieve → rerank → generate → guardrail → log). You need **acyclic** plans, **deterministic order**, and **failure isolation**—often backed by Temporal, Airflow, or bespoke queues.

- **Visualize** and **test** ordering **before** production traffic.

**Exit criteria**

- **Idempotent** steps where possible; **compensation** / **saga** patterns for multi-write flows.

**Implemented in this repository (MVP):** `scripts/horizon14_workflow_smoke.py` — `--verify` builds a tiny **ingest → tokenize → classify → emit_log** DAG, checks **topological order**, **cycle rejection**, and **parallel roots**; writes `horizon14_workflow_run/1.0` under `.tmp/horizon14-workflow/run.json`. **Not done yet vs. full exit:** **distributed** orchestrator, **retries**, **dynamic** branching.

---

### Horizon 15 — **Data minimization & export envelopes (privacy engineering)**

**Goal:** each **export kind** (DSR bundle, analytics aggregate, partner feed) exposes **only** fields listed in an **explicit envelope**—the opposite of “dump everything JSON.” Supports **GDPR**/**DSR** discipline when paired with legal review.

- **Deny-by-default** field sets; **schema version** per export type.

**Exit criteria**

- **Privacy review** sign-off per export template; **automated** CI failures when envelopes regress.

**Implemented in this repository (MVP):** `texts/horizon15_export_envelope_sample.json` + `scripts/horizon15_export_smoke.py` — `--verify` validates **allow-list** payloads and rejects **extra** keys; writes `horizon15_export_run/1.0` under `.tmp/horizon15-export/run.json`. **Not done yet vs. full exit:** **encryption** at rest/in transit, **redaction** pipelines, **legal** attestations.

---

## Decision gates (before funding each jump)

1. **Evidence gate** — the previous horizon’s metrics and incident data justify the next **scope** increase.
2. **Safety gate** — new modalities or memory types pass **threat models** and **red-team** bar for the intended user class.
3. **Economics gate** — **unit economics** (inference, storage, support) are modeled for the **smallest** viable deployment, not only demos.
4. **Operations gate** — runbooks, on-call, and **rollback** for model + memory + tool versions.

---

## What to do next in practice (from where TinyModel sits)

Short list that connects **this** repo to **Horizon 1** and, later, **Horizons 6–15**, without waiting for a “brain” label:

- **Harden data + eval** across more tasks; treat [`further-development-plan.md`](further-development-plan.md) as the **tactical** spine.
- **Know what exists:** H0 (plan), **H1** short-term scripts (handbook), **H2** generative, **H3** memory, **H4** image–text CLIP each have a **local MVP**; **H5** remains lab-only. **H6–H9** add **composition**, **tenant** isolation, **probes**, **policy**; **H10–H15** add **budget**, **feedback**, **hashes**, **circuit breaker**, **DAG** order, **export** envelopes—still **scripts**, not full product.
- **Prototyping lane:** follow [`optional-rd-backlog.md`](optional-rd-backlog.md) for spikes (PEFT, retrieval pooling, etc.).
- **System thinking:** as soon as you add an LLM, invest in **RAG, policies, and logs** in parallel with weights—not after; **H8–H15** add **operational** and **governance** shapes as **tests and contracts**, not only narrative.

---

## Open risks (explicit)

- **Over-promising** “universe” or “brain” externally while the stack is still a **specialized text pipeline**—**avoid**; use this doc **internally** for alignment.
- **Memory + agency** without **security** and **governance** invite incidents; **Horizon 3** is not “more parameters,” it is **more responsibility**.
- **Scope creep** across horizons without **gates** burns budget; sequence matters.
- **Horizon 7**-style **multi-tenant** or **compliance** promises without **engineered** isolation and **contractual** clarity invite breach and **regulatory** exposure.

---

*This is a **planning** artifact, not a release commitment, a valuation narrative, or a claim of AGI. Revise as evidence and product strategy change.*
