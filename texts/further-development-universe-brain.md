# Further development plan: toward a “universe brain” (north star)

This file is a **long-horizon** plan—separate from the **near-term engineering** checklist in [`further-development-plan.md`](further-development-plan.md) (Phases 1–3: baselines, eval quality, ONNX, serving). It also extends the commercial ladder in [`commercial-models-and-artificial-brain-roadmap.md`](commercial-models-and-artificial-brain-roadmap.md).

**“Universe brain”** here means an **integrated, growing system** that can **perceive** many signal types, **remember** and **retrieve** over time, **reason** with tools and constraints, and **act** in governed ways—**not** a claim of full human-level AGI or a single model that “knows everything.” It is a **design target** for multi-year R&D and selective products.

---

## How this document relates to the rest of the repo

| Document | Role |
| -------- | ---- |
| [`further-development-plan.md`](further-development-plan.md) | Concrete **Phases 1–3**: comparison matrix, eval artifacts, ONNX, benchmarks, reference API—**ship-shaped** work. |
| [`commercial-models-and-artificial-brain-roadmap.md`](commercial-models-and-artificial-brain-roadmap.md) | **Market-realistic** ladder from small encoder → LLM → multimodal; what companies pay for. |
| **This file** | **Vision + staged capabilities** toward a unified “brain-like” stack (Horizons **0–51**): through **H36–H37** freezes and pair cardinality; **H38–H39** **monotonic checkpoints** and **mutually exclusive job** scheduling; **H40–H41** **composite policy AND** and **geo-fence / residency** allow-lists; **H42–H43** **egress URL allow-lists** and **credential max-age** ceilings; **H44–H45** **optimistic concurrency** revisions and **payload size** ceilings; **H46–H47** **latency p99 budgets** and **global kill-switch** overrides; **H48–H49** **dual-control approvals** and **pinned artifact digests**; **H50–H51** **wire-format major-version compatibility** and **storage utilization headroom**—then product layers beyond this repo. |

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

### Horizon 16 — **Compatibility & versioning (artifact semver)**

**Goal:** JSON **run artifacts** (`horizonN_*_run/1.0`) evolve; **clients** (CLIs, dashboards, replay tools) must declare **which producer versions** they accept—avoid silent mis-parse after a breaking field change.

- **Semantic versioning** discipline per artifact family; **migration** notes when majors bump.

**Exit criteria**

- **Automated** compatibility matrix in CI for **consumer** ↔ **producer** pairs.

**Implemented in this repository (MVP):** `texts/horizon16_compat_manifest_sample.json` + `scripts/horizon16_semver_smoke.py` — `--verify` compares **numeric x.y.z** tuples (`reader_minimum` vs declared artifact versions) and writes `horizon16_semver_run/1.0` under `.tmp/horizon16-semver/run.json`. **Not done yet vs. full exit:** **PEP 440**, **calver**, **mixed** schemas.

---

### Horizon 17 — **Graceful degradation (service tiers)**

**Goal:** when health drops—**deps**, **budget**, **circuit breaker**—the product should **step down** capabilities (rich UI → cached answers → static fallback → read-only notice), not fail **opaquely**.

- Align **tier** with **SLO** promises and **support** messaging.

**Exit criteria**

- **Documented** behavior per tier for **every** paid SKU.

**Implemented in this repository (MVP):** `scripts/horizon17_degrade_smoke.py` — `--verify` maps a **health score** to **FULL / DEGRADED / MINIMAL / OFFLINE** and writes `horizon17_degrade_run/1.0` under `.tmp/horizon17-degrade/run.json`. **Not done yet vs. full exit:** **live** scores from probes (**H8**), **customer-facing** status pages.

---

### Horizon 18 — **Operational readiness (launch / game-day checklist)**

**Goal:** ship releases and incidents with **explicit gates**, not tribal knowledge—especially when AI surfaces depend on **deps**, **budget**, **circuit breakers**, and **policy**. Structured **phases** (pre-deploy, launch window) with **required** vs optional checks mirror **SOC** / **SRE** practice.

- Wire **checks** to **automated** probes where possible; human **sign-offs** where not.

**Exit criteria**

- **Runbook** runs **every** release train; **failed required checks** block promote.

**Implemented in this repository (MVP):** `texts/horizon18_readiness_sample.json` + `scripts/horizon18_readiness_smoke.py` — `--verify` walks phased **checks** with simulated pass/fail (demo fails only ids containing `_fail_demo`) and writes `horizon18_readiness_run/1.0` under `.tmp/horizon18-readiness/run.json`. **Not done yet vs. full exit:** **integrations** with CI, paging, **freeze windows**, **dry-run** rehearsals.

---

### Horizon 19 — **Tamper-evident audit trail (hash chain)**

**Goal:** append-only **audit logs** so later edits to history are **detectable**—pair with **H12** provenance and policy narratives for **forensics** and **compliance** shaped workflows.

- Production stacks often use **signed** heads, **WORM** storage, or **Merkle** batches; the principle is **don’t trust mutable logs blindly**.

**Exit criteria**

- **Verification** tooling proves **integrity** over retained history for regulators / security reviews.

**Implemented in this repository (MVP):** `scripts/horizon19_audit_chain_smoke.py` — `--verify` builds a linear **SHA-256** chain from a genesis anchor, confirms intact verification, confirms **tampering** breaks verification; writes `horizon19_audit_chain_run/1.0` under `.tmp/horizon19-audit-chain/run.json`. **Not done yet vs. full exit:** **keys**, **batch roots**, **distributed** consensus storage.

---

### Horizon 20 — **Feature flags & staged rollout**

**Goal:** ship risky model or UX changes behind **deterministic** cohorts—same subject always sees the same variant until you move **rollout_percent** or flip **kill switches**. Avoid “random per request” chaos.

- Combine with **H17** degradation and **H18** readiness so promotions stay controlled.

**Exit criteria**

- **Flag definitions** versioned; **audit** of who saw what variant during incidents.

**Implemented in this repository (MVP):** `texts/horizon20_flags_sample.json` + `scripts/horizon20_flags_smoke.py` — `--verify` evaluates **SHA-256(salt:subject) mod 100** vs **rollout_percent**, checks golden **expect_vectors**, plus boundary invariants; writes `horizon20_flags_run/1.0` under `.tmp/horizon20-flags/run.json`. **Not done yet vs. full exit:** **remote** flag stores, **experiments**, **audience rules**.

---

### Horizon 21 — **Data retention & purge eligibility**

**Goal:** AI stacks hoard **logs**, **embeddings**, and **feedback**—each category needs an explicit **TTL** and tooling that knows **what may be deleted** when (subject to legal holds).

- Pair with **H15** export envelopes and **H3** memory policy narratives.

**Exit criteria**

- **DSR / deletion** requests traceable to retention classes; **automated** purge jobs with **dry-run**.

**Implemented in this repository (MVP):** `texts/horizon21_retention_sample.json` + `scripts/horizon21_retention_smoke.py` — `--verify` compares **age in days** vs **retention_days** at a fixed **as_of** date; writes `horizon21_retention_run/1.0` under `.tmp/horizon21-retention/run.json`. **Not done yet vs. full exit:** **legal holds**, **cross-region** copies, **worm** archives.

---

### Horizon 22 — **Rate limiting & fairness (token bucket)**

**Goal:** protect inference and upstream **APIs** from abuse and hot loops with a **predictable** throttle—**token buckets** are the standard mental model for “burst + sustained” traffic.

- Complements **H10** budgets and **H13** circuit breakers; pair with **per-tenant** keys in production.

**Exit criteria**

- **Documented** default rates and burst per **SKU**; **load tests** prove queueing behavior.

**Implemented in this repository (MVP):** `texts/horizon22_token_bucket_sample.json` + `scripts/horizon22_token_bucket_smoke.py` — `--verify` runs a discrete **tick / consume** trace with golden **expect_allow**; writes `horizon22_token_bucket_run/1.0` under `.tmp/horizon22-token-bucket/run.json`. **Not done yet vs. full exit:** **wall-clock** refill, **distributed** Redis-style counters, **global** fairness.

---

### Horizon 23 — **Blast radius (dependency failure impact)**

**Goal:** AI products are **graphs**—if the **embeddings** index, **auth**, or **vector DB** fails, know **what else falls over** without guessing during an incident.

- Complements **H14** workflows; use for **game-day** exercises and **chaos** shaped tests.

**Exit criteria**

- **Service catalog** edges maintained as code; **redundant paths** documented where blast radius must shrink.

**Implemented in this repository (MVP):** `texts/horizon23_blast_sample.json` + `scripts/horizon23_blast_radius_smoke.py` — `--verify` propagates failure along **dependent → depends_on** edges until fixed point; compares sorted impacted sets per scenario; writes `horizon23_blast_radius_run/1.0` under `.tmp/horizon23-blast-radius/run.json`. **Not done yet vs. full exit:** **partial** degradation, **multi-region**, **capacity** overlays.

---

### Horizon 24 — **Canary promotion & regression gates**

**Goal:** shipping a **candidate** model or binary next to a **baseline** must be a **metric-disciplined** decision—latency, accuracy, error slices—with explicit **maximum regression** budgets before traffic shifts (**canary**, **shadow**, **A/B**).

- Connects to Phase **benchmark** artifacts and **H20** flags that gate rollout percentages.

**Exit criteria**

- **Automated** promote/deny from CI + offline eval JSON; **manual** override logged.

**Implemented in this repository (MVP):** `texts/horizon24_canary_gate_sample.json` + `scripts/horizon24_canary_gate_smoke.py` — `--verify` computes **regression %** vs baseline per metric (**worse_direction** `up` or `down`), compares to **max_regression_pct**; writes `horizon24_canary_gate_run/1.0` under `.tmp/horizon24-canary-gate/run.json`. **Not done yet vs. full exit:** **shadow traffic**, **multi-objective** Pareto gates, **Bayesian** stops.

---

### Horizon 25 — **Regional failover & traffic steering**

**Goal:** inference endpoints span **regions**; during outages or latency spikes you need a **deterministic preference order** (latency, compliance, cost) over **healthy** replicas—not random DNS luck.

- Complements **H23** blast radius (know dependencies) and **H17** degradation (when to steer traffic).

**Exit criteria**

- **Documented** fallback order per SKU; **game-days** validate probes flip routing.

**Implemented in this repository (MVP):** `texts/horizon25_failover_sample.json` + `scripts/horizon25_failover_smoke.py` — `--verify` selects the **first** region in **preference_order** not listed **unhealthy** (including empty-unhealthy → primary); writes `horizon25_failover_run/1.0` under `.tmp/horizon25-failover/run.json`. **Not done yet vs. full exit:** **latency-weighted** routing, **data residency**, **sticky sessions**.

---

### Horizon 26 — **SLO error budget (availability shaped)**

**Goal:** reliability is not vibes—it is **budgeted**. Given an **availability target** over a **request window**, only so many **failures** are tolerable before you breach SLO—tie this to incidents (**H18**) and probes (**H8**).

- Complements **H24** canary gates (same metric spine); burn triggers freeze or rollback.

**Exit criteria**

- **PagerDuty** / incident policy when budget crosses thresholds; **runbooks** for “freeze deploys.”

**Implemented in this repository (MVP):** `texts/horizon26_error_budget_sample.json` + `scripts/horizon26_error_budget_smoke.py` — `--verify` computes **max_allowed_errors** = ⌊window × (100 − availability_target_pct) / 100⌋ vs **errors_observed**; writes `horizon26_error_budget_run/1.0` under `.tmp/horizon26-error-budget/run.json`. **Not done yet vs. full exit:** **composite** SLIs, **seasonality**, **multi-window** burn alerts.

---

### Horizon 27 — **Prompt injection resistance (policy-shaped gate)**

**Goal:** deployed LLMs face **prompt injection**, jailbreak strings, and role-confusion attempts—the **minimum** product stance is explicit **blocking rules**, tuned datasets, and escalation—not “trust the model.”

- Connects to **H9** policy layers and **H19** audit trails when prompts are denied.

**Exit criteria**

- **Logged** rejects with policy version; **human review** queue for ambiguous hits.

**Implemented in this repository (MVP):** `texts/horizon27_prompt_gate_sample.json` + `scripts/horizon27_prompt_gate_smoke.py` — `--verify` applies **case-insensitive substring** deny lists across rule sets vs golden vectors; writes `horizon27_prompt_gate_run/1.0` under `.tmp/horizon27-prompt-gate/run.json`. **Not done yet vs. full exit:** **tokenizer-aware** scanners, **ML filters**, multilingual coverage.

---

### Horizon 28 — **Idempotent side-effects (ledger)**

**Goal:** payments, provisioning, and **embedding jobs** must tolerate **retries**—clients replay the same logical operation with an **idempotency key** so **exactly-once-ish** semantics hold without double charging.

- Aligns with **H14** workflows (steps must be **retry-safe**) and **H19** audit trails.

**Exit criteria**

- **Durable** dedupe store with TTL; **conflicting** payloads under same key rejected loudly.

**Implemented in this repository (MVP):** `texts/horizon28_idempotency_sample.json` + `scripts/horizon28_idempotency_smoke.py` — `--verify` processes keyed events **in order**, keeps **first-seen** sequence, counts **suppressed** duplicates; writes `horizon28_idempotency_run/1.0` under `.tmp/horizon28-idempotency/run.json`. **Not done yet vs. full exit:** **distributed** stores, **exactly-once** sinks, **payload hash** conflicts.

---

### Horizon 29 — **Supply chain bounds (SBOM semver)**

**Goal:** reproducible stacks Pin **libraries** (**numpy**, HTTP clients, tokenizers) with explicit **semver intervals**—catch accidental drift during upgrades before CI merges **broken pins**.

- Complements **H16** artifact semver with **dependency policy**.

**Exit criteria**

- **Automated** dependency review blocking pins outside approved bands; **CVE** gates tied to SBOM.

**Implemented in this repository (MVP):** `texts/horizon29_sbom_bounds_sample.json` + `scripts/horizon29_sbom_bounds_smoke.py` — `--verify` checks **pinned_version** satisfies **[min_version, max_exclusive)** via padded numeric tuples; writes `horizon29_sbom_bounds_run/1.0` under `.tmp/horizon29-sbom-bounds/run.json`. **Not done yet vs. full exit:** **PEP 440**, prereleases, **signed** SBOM.

---

### Horizon 30 — **Distributed coordination (leases / TTL)**

**Goal:** training locks, **embedding** shard reservations, and **leader election** shaped workflows need **time-bounded leases**—otherwise stale holders block progress forever after crashes.

- Connects to **H22** token buckets (burst vs sustained) and **H28** idempotency (who owns the side-effect).

**Exit criteria**

- **Graceful renewal**, **fencing tokens**, and **GC** of orphaned leases under documented clocks.

**Implemented in this repository (MVP):** `texts/horizon30_lease_sample.json` + `scripts/horizon30_lease_smoke.py` — `--verify` marks leases **active** when **check_at ∈ [acquired_at, acquired_at + ttl)** (half-open end); writes `horizon30_lease_run/1.0` under `.tmp/horizon30-lease/run.json`. **Not done yet vs. full exit:** **wall-clock skew**, **multi-node** consensus, **renewal** pipelines.

---

### Horizon 31 — **Cardinality & observability budgets**

**Goal:** telemetry dimensions (**user**, **region**, **SKU**) explode **metric cardinality**—bill shock and slow queries—unless batches enforce **distinct-count caps** per dimension window.

- Feeds **H10** budgets and **H26** SLO math when backends overload.

**Exit criteria**

- **Sampling / aggregation** strategies documented when approaching caps; **alerts** before breach.

**Implemented in this repository (MVP):** `texts/horizon31_cardinality_sample.json` + `scripts/horizon31_cardinality_smoke.py` — `--verify` compares **distinct counts** per dimension vs **max_distinct** across synthetic batches (including intentional violations); writes `horizon31_cardinality_run/1.0` under `.tmp/horizon31-cardinality/run.json`. **Not done yet vs. full exit:** **HyperLogLog**, **streaming** windows, **per-tenant** isolation.

---

### Horizon 32 — **Streaming backlog & consumer lag**

**Goal:** queued inference, **embedding** rebuilds, and **feedback** ingestion are **streams**—operators must see **lag** (high-water mark minus consumer position) versus **budget** before queues spill into **latency SLO** breaches (**H26**) or **tier downgrade** (**H17**).

- Complements **H14** DAG steps when steps are **partition consumers**.

**Exit criteria**

- **Dashboards** on lag per partition; **auto-scale** hooks documented when sustained lag exceeds threshold.

**Implemented in this repository (MVP):** `texts/horizon32_consumer_lag_sample.json` + `scripts/horizon32_consumer_lag_smoke.py` — `--verify` computes **lag_units** = max(0, **high_water_mark − consumer_position**) vs **max_lag_allowed**; writes `horizon32_consumer_lag_run/1.0` under `.tmp/horizon32-consumer-lag/run.json`. **Not done yet vs. full exit:** **Kafka/Orchestrator** semantics, **exactly-once** checkpoints, **consumer groups**.

---

### Horizon 33 — **Purpose limitation (lawful basis × processing)**

**Goal:** GDPR-shaped systems tie each **processing purpose** (**inference**, **analytics**, **marketing**) to an explicit **lawful basis** (**contract**, **consent**, etc.)—not “collect everything because ML.” Product policy must **encode** allowed combinations.

- Aligns with **H15** export envelopes and **H21** retention when lawful basis drives deletion rules.

**Exit criteria**

- **Records of processing**, **DPIAs**, and **jurisdiction** overlays reviewed by counsel—not repo scripts alone.

**Implemented in this repository (MVP):** `texts/horizon33_purpose_matrix_sample.json` + `scripts/horizon33_purpose_matrix_smoke.py` — `--verify` checks (**legal_basis**, **processing_purpose**) pairs against an explicit **allowed_pairs** set; writes `horizon33_purpose_matrix_run/1.0` under `.tmp/horizon33-purpose-matrix/run.json`. **Not done yet vs. full exit:** **Art. 6** nuance per sector, **international transfers**, **automated decision-making** carve-outs.

---

### Horizon 34 — **Distributed quorum (strict majority)**

**Goal:** promotions (**canary advance**, **config commits**, **failover**) cannot rely on a single node's opinion—**Raft-ish** majorities (**⌊n/2⌋ + 1** yes votes on total membership **n**) prevent split-brain commits under partitions.

- Connects to **H25** routing health signals and **H30** leases when electing primaries.

**Exit criteria**

- **Formal proof sketches** + simulation under partitions for your consensus library; **never hand-roll** Paxos/Raft for production data planes casually.

**Implemented in this repository (MVP):** `texts/horizon34_quorum_sample.json` + `scripts/horizon34_quorum_smoke.py` — `--verify` evaluates **strict majority** as **votes_yes × 2 > replicas_total** per scenario; writes `horizon34_quorum_run/1.0` under `.tmp/horizon34-quorum/run.json`. **Not done yet vs. full exit:** **Byzantine** thresholds, **weighted** voters, **witness** logs.

---

### Horizon 35 — **Cryptographic suite policy (algorithm × key length)**

**Goal:** encryption **at rest** and **in transit** must match **explicit allow-lists**—weak algorithms (**DES**, short keys) blocked before artifacts ship—pairs with **H29** SBOM pins.

- Supports **SOC 2**, **FedRAMP**, and internal crypto standards narratives.

**Exit criteria**

- **Automated** linter over infra manifests / TLS configs; **HSM** integration where mandated.

**Implemented in this repository (MVP):** `texts/horizon35_crypto_suite_sample.json` + `scripts/horizon35_crypto_suite_smoke.py` — `--verify` accepts a claim only when **algorithm** matches an **allowed_suites** row and **key_bits ≥ key_bits_min**; writes `horizon35_crypto_suite_run/1.0` under `.tmp/horizon35-crypto-suite/run.json`. **Not done yet vs. full exit:** **cipher suites** negotiation order, **PQ/TLS** hybrid profiles, **attestation**.

---

### Horizon 36 — **Maintenance freeze windows**

**Goal:** coordinated **infra / model deploy** freezes (**game days**, holidays, regulated quiet periods) block risky automation unless someone invokes **break-glass**—encoded as UTC windows over operator tooling.

- Aligns with **H18** readiness checklists and **H24** canary gates when freezes overlap promotions.

**Exit criteria**

- **Immutable calendar** feeds CI/CD; **pager + audit** when freezes are overridden.

**Implemented in this repository (MVP):** `texts/horizon36_maintenance_freeze_sample.json` + `scripts/horizon36_maintenance_freeze_smoke.py` — `--verify` marks **frozen** when **check_at ∈ [start, end)** for any listed interval; writes `horizon36_maintenance_freeze_run/1.0` under `.tmp/horizon36-maintenance-freeze/run.json`. **Not done yet vs. full exit:** **recurring** RRULE calendars, **multi-region** tz joins.

---

### Horizon 37 — **Pair cardinality (Cartesian explosion guard)**

**Goal:** observability labels compound—**(tenant × SKU)** pairs can multiply faster than single dimensions (**H31**) alone—enforce **distinct pair budgets** before dashboards melt billing or query caches.

- Together with **H31** single-dimension caps and **H22** token buckets as shaping layers.

**Exit criteria**

- **Sampling**, **high-cardinality drop**, or **pre-aggregation** runbooks before breach.

**Implemented in this repository (MVP):** `texts/horizon37_pair_cardinality_sample.json` + `scripts/horizon37_pair_cardinality_smoke.py` — `--verify` counts unique **(dim_a, dim_b)** tuples vs **max_distinct_pairs** per scenario; writes `horizon37_pair_cardinality_run/1.0` under `.tmp/horizon37-pair-cardinality/run.json`. **Not done yet vs. full exit:** **triple** products, **approximate** sketches per pair key.

---

### Horizon 38 — **Monotonic checkpoints & replay watermarks**

**Goal:** streaming pipelines (**offsets**, **sequence numbers**, **vector clock** summaries) must never **rewind** silently—retrograde checkpoints corrupt downstream **exactly-once** reasoning (**H28**) and confuse **audit** (**H19**).

- Connects to **H32** consumer lag math as **progress** telemetry.

**Exit criteria**

- **Invariant checks** in processors; **alert + halt** when violations detected outside controlled resets.

**Implemented in this repository (MVP):** `texts/horizon38_watermark_sample.json` + `scripts/horizon38_watermark_smoke.py` — `--verify` asserts integer **watermarks** lists are **non-decreasing** adjacent-wise; writes `horizon38_watermark_run/1.0` under `.tmp/horizon38-watermark/run.json`. **Not done yet vs. full exit:** **per-partition** vectors, **Kafka ISR**, **checkpoint stores**.

---

### Horizon 39 — **Mutually exclusive jobs (scheduler mutex)**

**Goal:** certain workloads cannot overlap (**train vs deploy**, **migrate vs serve**)—encoded **mutex pairs** feed schedulers so conflicting windows never obtain exclusive resources concurrently.

- Complements **H14** DAG constraints when parallelism must exclude hazards.

**Exit criteria**

- **Solver-backed** schedules or **Kubernetes** affinity rules reflecting mutex graphs—not only spreadsheets.

**Implemented in this repository (MVP):** `texts/horizon39_job_mutex_sample.json` + `scripts/horizon39_job_mutex_smoke.py` — `--verify` detects **conflict** when **both** endpoints of any **mutex_pair** appear in **scheduled_jobs**; writes `horizon39_job_mutex_run/1.0` under `.tmp/horizon39-job-mutex/run.json`. **Not done yet vs. full exit:** **resource** capacities, **duration**, **retry** storms.

---

### Horizon 40 — **Composite policy AND (all gates)**

**Goal:** production policies often bundle **many** checks (**budget**, **prompt**, **crypto**, region)—the **composite** decision **permits** only when **every** constituent gate passes (**logical AND**), not when any single score looks green.

- Composes **H9**, **H27**, **H35**, **H41**, and similar gates into one **enforceable** bundle.

**Exit criteria**

- **Policy-as-code** with **explicit AND/OR** algebra, **exceptions** under audit, and **version pins** shipped with deployments.

**Implemented in this repository (MVP):** `texts/horizon40_policy_and_sample.json` + `scripts/horizon40_policy_and_smoke.py` — `--verify` asserts **`composite_ok`** matches **`expect_all_pass`** when **`all(gate.pass)`** per scenario; writes `horizon40_policy_and_run/1.0` under `.tmp/horizon40-policy-and/run.json`. **Not done yet vs. full exit:** **OR** groups, **weighted** scores, **dynamic** gate lists.

---

### Horizon 41 — **Geo-fence / data residency (region allow-list)**

**Goal:** regulated workloads require **hard** boundaries—**processing** and **storage** must occur only in **approved regions**; deny-by-default when jurisdiction does not match contract.

- Aligns with **H15** export envelopes and **H35** crypto posture when regions imply **key material** locality.

**Exit criteria**

- **Cloud/private link** topology maps; **transfer impact** assessments; **continuous** residency proofs—not only spreadsheet attestations.

**Implemented in this repository (MVP):** `texts/horizon41_geo_fence_sample.json` + `scripts/horizon41_geo_fence_smoke.py` — `--verify` marks **allowed** iff **`region ∈ allowed_regions`** per check; writes `horizon41_geo_fence_run/1.0` under `.tmp/horizon41-geo-fence/run.json`. **Not done yet vs. full exit:** **multi-region** failover semantics, **data lineage** proofs, **private** interconnect routing.

---

### Horizon 42 — **Egress allow-list (tool / outbound URL gate)**

**Goal:** agents and backends must not **POST** or **fetch** arbitrary URLs—only **approved hostnames** (API partners, Slack hooks, tenant endpoints)—encoded as policy before tools ship.

- Complements **H9** policy samples and **H41** residency when egress crosses regions.

**Exit criteria**

- **Service mesh / egress proxy** enforcement; **certificate pinning** where required; **break-glass** audit when lists widen.

**Implemented in this repository (MVP):** `texts/horizon42_egress_allow_sample.json` + `scripts/horizon42_egress_allow_smoke.py` — `--verify` parses each **`url`** hostname and marks **allowed** on **exact** match or **suffix** match (`hostname.endswith("." + rule)` when the rule contains **`.`**); writes `horizon42_egress_allow_run/1.0` under `.tmp/horizon42-egress-allow/run.json`. **Not done yet vs. full exit:** **glob** patterns, **IP allow-lists**, **DNS rebinding** defenses.

---

### Horizon 43 — **Credential / session freshness (max age)**

**Goal:** long-lived **API keys**, **OAuth access tokens**, and **session cookies** invite replay—enforce **maximum staleness** relative to issuance (**wall-clock age** envelope), pairing with **H30** leases and **H41** geo shifts.

**Exit criteria**

- **Automatic rotation**, **revocation surfaces**, **clock-skew** budgets—not only max-age checks on paper.

**Implemented in this repository (MVP):** `texts/horizon43_credential_age_sample.json` + `scripts/horizon43_credential_age_smoke.py` — `--verify` marks **valid** iff **`age_seconds ≤ max_age_seconds`** per check; writes `horizon43_credential_age_run/1.0` under `.tmp/horizon43-credential-age/run.json`. **Not done yet vs. full exit:** **not-before / not-after** windows, **hardware-bound** freshness, **replay** caches.

---

### Horizon 44 — **Optimistic concurrency (revision match)**

**Goal:** concurrent writers must not silently **clobber** state—**compare-and-set** on a **monotonic revision** (or row version) rejects stale updates and surfaces **409-style** conflicts to clients.

- Connects to **H28** idempotency (distinct concerns: exactly-once delivery vs last-write-wins).

**Exit criteria**

- **Database-level** CAS or **transaction isolation** proofs; **merge** semantics where conflicts are expected.

**Implemented in this repository (MVP):** `texts/horizon44_optimistic_lock_sample.json` + `scripts/horizon44_optimistic_lock_smoke.py` — `--verify` marks **`apply_ok`** iff **`client_revision == stored_revision`** per scenario; writes `horizon44_optimistic_lock_run/1.0` under `.tmp/horizon44-optimistic-lock/run.json`. **Not done yet vs. full exit:** **vector clocks**, **CRDT** payloads, **human merge** workflows.

---

### Horizon 45 — **Payload size ceiling (ingress guard)**

**Goal:** oversized bodies (**prompt injection blobs**, accidental megabyte POSTs) exhaust gateways and parsers—enforce **`max_bytes`** at the edge before expensive routing (**H26** budgets, **H27** prompt gates).

**Exit criteria**

- **Streaming** APIs with **chunk** budgets; **multipart** parsers hardened against zip bombs—not only static limits.

**Implemented in this repository (MVP):** `texts/horizon45_payload_size_sample.json` + `scripts/horizon45_payload_size_smoke.py` — `--verify` marks **allowed** iff **`bytes ≤ max_bytes`** per check; writes `horizon45_payload_size_run/1.0` under `.tmp/horizon45-payload-size/run.json`. **Not done yet vs. full exit:** **per-tenant** quotas, **compression** bombs, **WS** frame limits.

---

### Horizon 46 — **Latency tail budget (approximate p99 ceiling)**

**Goal:** **SLO** narratives often cite **p95/p99 latency**—encode a **ceil-ranked** percentile sample smoke against **`max_p99_ms`** so promotions respect tail risk beside **H26** burn rates.

- Distinct from **H32** lag as **consumer backlog**—here **wall-clock request duration** samples.

**Exit criteria**

- **HDR histograms**, **distributed traces**, **tenant-scoped** tails—not only toy arrays.

**Implemented in this repository (MVP):** `texts/horizon46_latency_p99_sample.json` + `scripts/horizon46_latency_p99_smoke.py` — `--verify` sorts **`samples_ms`**, takes approximate **p99** (`ceil(0.99·n)−1` rank), compares to **`max_p99_ms`** vs **`expect_under_budget`**; writes `horizon46_latency_p99_run/1.0` under `.tmp/horizon46-latency-p99/run.json`. **Not done yet vs. full exit:** **t-digest**, **weighted** SLIs, **multi-region** aggregation.

---

### Horizon 47 — **Kill switch (global deny)**

**Goal:** **Incident response** sometimes requires **immediate traffic denial** regardless of fine-grained policy—**toggle** routes to safe degradation (**read-only**, **503**) without redeploying every rule (**H40**, **H24**).

- **Stronger than** **H13** circuit breaker per dependency—here **global** product stance.

**Exit criteria**

- **Pager-owned** switches with **mandatory audit**, **automatic expiry**, **regional scope** options.

**Implemented in this repository (MVP):** `texts/horizon47_kill_switch_sample.json` + `scripts/horizon47_kill_switch_smoke.py` — `--verify` marks **`allowed`** iff **`¬kill_switch_engaged ∧ policy_allow`** per check within scenarios; writes `horizon47_kill_switch_run/1.0` under `.tmp/horizon47-kill-switch/run.json`. **Not done yet vs. full exit:** **scoped** kills (**tenant**, **route class**), **gradual drain**.

---

### Horizon 48 — **Dual control (distinct approvers)**

**Goal:** high-risk changes (**production promotions**, **policy edits**, **break-glass**) require **more than one distinct human identity** (or mandated roles)—**count unique approvers**, not duplicate clicks from the same principal.

- Connects to **H18** readiness and **SOC 2** change-management narratives without replacing ticketing systems.

**Exit criteria**

- **Identity-bound** approvals (**SSO subject** + device posture), **time-bound** voting windows, **override** audits.

**Implemented in this repository (MVP):** `texts/horizon48_dual_control_sample.json` + `scripts/horizon48_dual_control_smoke.py` — `--verify` marks **`pass_gate`** iff **`|unique(approver_ids)| ≥ min_distinct_approvers`** per check; writes `horizon48_dual_control_run/1.0` under `.tmp/horizon48-dual-control/run.json`. **Not done yet vs. full exit:** **role matrices**, **rotation schedules**, **hardware-bound** attestations.

---

### Horizon 49 — **Pinned artifact digest (immutable promote)**

**Goal:** shipping software means tying promotions to **exact binary identity**—**SHA-256** (or stronger) pins per channel/environment block drift between approved CI outputs and runtime (**H29**, container signing).

**Exit criteria**

- **Sigstore/cosign**, **OCI digest locks**, **SBOM linkage**, **automated diff gates**.

**Implemented in this repository (MVP):** `texts/horizon49_digest_pin_sample.json` + `scripts/horizon49_digest_pin_smoke.py` — `--verify` marks **`allow`** iff **`artifact_sha256 == pinned_sha256`** per check (case-insensitive hex compare); writes `horizon49_digest_pin_run/1.0` under `.tmp/horizon49-digest-pin/run.json`. **Not done yet vs. full exit:** **threshold signatures**, **rekor transparency**, **multi-artifact bundles**.

---

### Horizon 50 — **Wire-format major-version compatibility**

**Goal:** evolving APIs (**RPC**, **event envelopes**, **tool contracts**) must declare **breaking ranges** safely—a client’s **minimum major** must not exceed what servers still honor backward-compatibly (**H16** semver narrative at wire shape).

**Exit criteria**

- **Deprecation calendars**, **automatic codegen**, **dual-publish** bridges—not only integer compares.

**Implemented in this repository (MVP):** `texts/horizon50_schema_compat_sample.json` + `scripts/horizon50_schema_compat_smoke.py` — `--verify` marks **`compatible`** iff **`server_schema_major ≥ required_minimum_major`** per check; writes `horizon50_schema_compat_run/1.0` under `.tmp/horizon50-schema-compat/run.json`. **Not done yet vs. full exit:** **minor/patch negotiation**, **feature bits**, **protobuf field masks**.

---

### Horizon 51 — **Quota headroom (storage utilization ceiling)**

**Goal:** disks and **object stores** need slack before writes wedge pipelines—deny destructive grows when **`utilization_pct`** breaches **`max_utilization_pct`** (**H45** ingress complements egress/storage).

**Exit criteria**

- **Predictive capacity**, **tiered storage**, **GC/back-pressure** controllers—not only threshold booleans.

**Implemented in this repository (MVP):** `texts/horizon51_quota_headroom_sample.json` + `scripts/horizon51_quota_headroom_smoke.py` — `--verify` marks **`under_budget`** iff **`utilization_pct ≤ max_utilization_pct`** vs **`expect_under_budget`**; writes `horizon51_quota_headroom_run/1.0` under `.tmp/horizon51-quota-headroom/run.json`. **Not done yet vs. full exit:** **inode** quotas, **per-bucket** curves, **multi-AZ** replication slack.

---

## Decision gates (before funding each jump)

1. **Evidence gate** — the previous horizon’s metrics and incident data justify the next **scope** increase.
2. **Safety gate** — new modalities or memory types pass **threat models** and **red-team** bar for the intended user class.
3. **Economics gate** — **unit economics** (inference, storage, support) are modeled for the **smallest** viable deployment, not only demos.
4. **Operations gate** — runbooks, on-call, and **rollback** for model + memory + tool versions.

---

## What to do next in practice (from where TinyModel sits)

Short list that connects **this** repo to **Horizon 1** and, later, **Horizons 6–51**, without waiting for a “brain” label:

- **Harden data + eval** across more tasks; treat [`further-development-plan.md`](further-development-plan.md) as the **tactical** spine.
- **Know what exists:** H0 (plan), **H1** short-term scripts (handbook), **H2** generative, **H3** memory, **H4** image–text CLIP each have a **local MVP**; **H5** remains lab-only. **H6–H15** cover **composition** through **export** envelopes; **H16–H17** add **semver** contracts and **degradation** tiers; **H18–H19** add **readiness gates** and **audit hash chains**; **H20–H21** add **feature-flag rollout** and **retention purge** smokes; **H22–H23** add **token-bucket** and **blast-radius** smokes; **H24–H25** add **canary gates** and **failover routing** smokes; **H26–H27** add **error budget** and **prompt gate** smokes; **H28–H29** add **idempotency ledger** and **SBOM semver bounds** smokes; **H30–H31** add **lease TTL** and **cardinality budget** smokes; **H32–H33** add **consumer lag** and **purpose matrix** smokes; **H34–H35** add **quorum majority** and **crypto suite** smokes; **H36–H37** add **maintenance freeze** and **pair cardinality** smokes; **H38–H39** add **watermark monotonicity** and **job mutex** smokes; **H40–H41** add **composite policy AND** and **geo-fence residency** smokes; **H42–H43** add **egress URL allow-list** and **credential max-age** smokes; **H44–H45** add **optimistic concurrency revision match** and **payload max-bytes** smokes; **H46–H47** add **latency p99 budget** and **kill-switch global deny** smokes; **H48–H49** add **dual-control distinct approvers** and **pinned digest promote** smokes; **H50–H51** add **wire major-version compat** and **storage quota headroom** smokes—still **scripts**, not full product.
- **Prototyping lane:** follow [`optional-rd-backlog.md`](optional-rd-backlog.md) for spikes (PEFT, retrieval pooling, etc.).
- **System thinking:** as soon as you add an LLM, invest in **RAG, policies, and logs** in parallel with weights—not after; **H8–H51** add **operational** and **governance** shapes as **tests and contracts**, not only narrative.

---

## Open risks (explicit)

- **Over-promising** “universe” or “brain” externally while the stack is still a **specialized text pipeline**—**avoid**; use this doc **internally** for alignment.
- **Memory + agency** without **security** and **governance** invite incidents; **Horizon 3** is not “more parameters,” it is **more responsibility**.
- **Scope creep** across horizons without **gates** burns budget; sequence matters.
- **Horizon 7**-style **multi-tenant** or **compliance** promises without **engineered** isolation and **contractual** clarity invite breach and **regulatory** exposure.

---

*This is a **planning** artifact, not a release commitment, a valuation narrative, or a claim of AGI. Revise as evidence and product strategy change.*
