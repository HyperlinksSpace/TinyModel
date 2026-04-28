# TinyModel: current state, direction, and product-readiness (estimate)

This note is a **synthesis** for stakeholders. Authoritative checklists stay in [`further-development-plan.md`](further-development-plan.md) (Phases 1–3) and the horizon ladder in [`further-development-universe-brain.md`](further-development-universe-brain.md). It is **not** a financial forecast or a promise of ship dates.

---

## What TinyModel is today (functionality)

**Positioning (README):** a **practical, small, deployable text-classification baseline** for rapid iteration—not a full “general AI” product by itself.

**Public-facing artifacts (already usable by end users in a narrow sense):**

- **Hugging Face model** [HyperlinksSpace/TinyModel1](https://huggingface.co/HyperlinksSpace/TinyModel1) — weights, tokenizer, model card; load with `transformers` or related APIs where available.
- **Gradio Space** [TinyModel1Space](https://huggingface.co/spaces/HyperlinksSpace/TinyModel1Space) — a **live demo** for trying classification; suitable for **showcase and light use**, not a substitute for a full SaaS with auth, SLAs, and abuse handling.

**Engineering in this repository:**

The horizon ladder in [`further-development-universe-brain.md`](further-development-universe-brain.md) runs **0–53** (semver through dry-run gate smokes as later MVPs).

| Area | What exists |
| ---- | ----------- |
| **Training & eval** | Reproducible training (`train_tinymodel1_classifier.py` and dataset wrappers), Phase 1 comparison matrix, **Phase 2** `eval_report.json` (dataset quality, confusions, calibration, routing notes), misclassified sample JSONL. |
| **Packaging** | Phase 3–style ONNX path and reference patterns; CI smoke workflows for the main training/eval path. |
| **Runtime** | `TinyModelRuntime` — classification, similarity, **retrieval** over a candidate list; supports **routing-shaped** use cases. |
| **RAG-shaped demo** | FAQ-style retrieval + cheap faithfulness proxy (`rag_faq_smoke.py` + small corpus) — **prototype**, not production RAG. |
| **Generative (H2)** | Local / Hub causal LM path with JSON run artifacts; smoke tests in CI. |
| **Memory (H3)** | SQLite **session vs long-term** store, audit, export, forget; CLI + optional HTTP. |
| **Multimodal (H4)** | CLIP-style **image + caption** alignment and JSON runs; CI uses **offline** synthetic CLIP. |
| **Convergence & governance (H6–H53)** | Through **H15**: chained smokes, tenant isolation, probes, policy, budget, feedback JSONL, hashes, circuit breaker, DAG smoke, export envelopes; **H16–H17**: **semver** manifest smoke, **degradation tier** smoke; **H18–H19**: **readiness checklist** smoke, **audit hash chain** smoke; **H20–H21**: **feature-flag rollout** smoke, **retention purge** smoke; **H22–H23**: **token bucket** smoke, **blast radius** smoke; **H24–H25**: **canary regression gate** smoke, **failover route** smoke; **H26–H27**: **error budget** smoke, **prompt gate** smoke; **H28–H29**: **idempotency ledger** smoke, **SBOM semver bounds** smoke; **H30–H31**: **lease TTL** smoke, **cardinality budget** smoke; **H32–H33**: **consumer lag** smoke, **purpose matrix** smoke; **H34–H35**: **quorum majority** smoke, **crypto suite** smoke; **H36–H37**: **maintenance freeze** smoke, **pair cardinality** smoke; **H38–H39**: **watermark monotonicity** smoke, **job mutex** smoke; **H40–H41**: **composite policy AND** smoke, **geo-fence residency** smoke; **H42–H43**: **egress URL allow-list** smoke, **credential max-age** smoke; **H44–H45**: **optimistic concurrency** smoke, **payload max-bytes** smoke; **H46–H47**: **latency p99 budget** smoke, **kill-switch** smoke; **H48–H49**: **dual-control** smoke, **pinned digest** smoke; **H50–H51**: **schema major compat** smoke, **quota headroom** smoke; **H52–H53**: **RBAC role subset** smoke, **dry-run gate** smoke. |

**What this is *not* yet:** a **single** hosted product with **multi-tenant** auth, **billing**, **abuse and safety** at scale, **signed** policy distribution, or a **unified** production runtime that replaces ad hoc scripts. Those are **staged** in the plan and horizons as **targets**, with many items explicitly **TBD** outside the repo (legal, ops, org process).

---

## Where we are moving (direction)

**Tactical track** ([`further-development-plan.md`](further-development-plan.md)):

- Harden **Phases 1–3** end-to-end (smoke, optional fuller `phase1_compare` runs, clear verification of Phase 2 fields on fresh checkpoints).
- Keep eval and packaging **credible** for real deployment decisions, not only demos.

**Short-term (Horizon 1 tranche, universe-brain “A–D”):**

- **A:** Baseline / CI closure.  
- **B:** **Multiple** tasks with comparable eval artifacts and a short error/confusion write-up.  
- **C:** **RAG/retrieval** as a **repeatable** story on top of `TinyModelRuntime`, not a one-off script.  
- **D (optional):** a **generative** hook aligned with the same logging/eval contract.

**Long-horizon (Horizons 0–53, “universe brain” *design target*):**

- Move from “good encoder + scripts” toward **integrated** **perception, memory, generation, and policy**—with **decision gates** (evidence, safety, economics, operations) before each jump. The repo’s **H6–H53** work is **MVP / smoke / contracts**; full **H7+** (compliance, ecosystem, assurances) is mostly **out of band** in product and legal.

**Commercial / market context:** [`commercial-models-and-artificial-brain-roadmap.md`](commercial-models-and-artificial-brain-roadmap.md) — buyers care about **retrieval, classification, extraction, RAG, assistants, vision**; the roadmap stays **sober** about what a tiny encoder is for versus LLM-class systems.

---

## “Complete product for users” — define the bar, then estimate steps

“Complete” is ambiguous. Three useful levels:

### Level 1 — **Current public demo (already available)**

- Users can try the **Space** and load the **model** from the Hub.  
- **Steps remaining** for a “clean” maintainer experience: small **ops** and **doc** tasks (refresh card, watch CI, occasional dependency bumps)—on the order of **ongoing** maintenance, not a big sequential project.

### Level 2 — **Credible *minimal* product (single-tenant, one vertical)**

Delivers: **reliable** classification (and maybe retrieval) behind **your** API or app, with **eval discipline**, **rollback**, and **basic** monitoring.

Rough **building blocks** still to nail (from existing plans, not all in-repo):

1. **Close** Phase 1–3 **verification** on fresh artifacts and keep CI green.  
2. **Horizon 1 B–C:** three-task harness + RAG/FAQ path **as product-shaped** (corpus, runbook, not only scripts).  
3. **Host** runtime (your stack): **one** deployment pattern, health checks, logging.  
4. **Policy & safety** appropriate to the **vertical** (content rules, human review if needed).  

**Order-of-magnitude:** about **6–10** *major* milestones (each can split into many tickets). Calendar time in the plan’s own ballpark: on the order of **roughly 4–8 weeks** of focused work for **A–C**-class closure *if* scope stays tight—longer if datasets, compliance, or integration complexity grow. (The universe-brain short-term table suggests **~3–5 weeks** for **A + B + C** in parallel; add buffer for D and production hardening.)

### Level 3 — **“Full” multi-capability product (encoder + RAG + gen + memory + tenant trust + policy)**

Matches long-term **H1–H2–H3–H4** exits and significant parts of **H6–H9** *as products*, not smokes: unified **runtime**, **multi-tenant** boundaries, **real** policy and audit, **SLOs**, **on-call** runbooks, optional **LLM** tier with guardrails.

**Order-of-magnitude:** **multiple calendar quarters** and **dozens to 100+** engineering steps (epics, features, and ops work), *plus* **non-code** work (legal, security review, GTM). The repo’s horizons **0–9** are **staged** **design**; many exit criteria are **explicitly** not met by script-only MVPs.

---

## Summary table

| User goal | Roughly how far along | Order-of-magnitude “steps”* |
| --------- | ------------------------ | --------------------------- |
| Use HF model + Space demo | **Largely there** | Maintenance-style |
| Shippable app with TinyModel as **the** text AI core | **Mid** (needs H1 B/C + deploy + policy) | **~6–10** major milestones |
| **Full** integrated “brain-like” product | **Far** (multi-quarter; gates) | **Many epics (50+ tasks)** is plausible |

\*Steps = meaningful shipped milestones, not single commits.

---

## Bottom line

- **Today:** TinyModel is a **strong encoder baseline** with a **public demo**, rich **eval** and **packaging** story, and a **growing** set of **experimental** and **smoke-verified** paths (RAG demo, generative, memory, multimodal, convergence, tenant toy, probes, policy sample).  
- **Direction:** **tighten** the tactical plan, **broaden** task coverage and RAG, then **selectively** productize under **decision gates**—without confusing repo **demos** with **enterprise** assurances.  
- **“Complete product” in a serious sense (Level 3):** think in **quarters** and **many** steps; **Level 2** is a realistic near-term product bar with on the order of **single-digit** major milestones if scope is disciplined.

*This is a **planning** note; update when shipping strategy or team capacity changes.*
