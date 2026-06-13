# Forward plan: toward universal capability and self-developing intelligence

This document is a **roadmap** for moving Universal Brain from today’s **demo-grade integration** toward **broader task coverage**, **predictable cost**, and **automated improvement loops**. It builds on [`universal-brain-concept-vs-tinymodel-today.md`](universal-brain-concept-vs-tinymodel-today.md), [`universal-brain-self-development-feedback-loop.md`](universal-brain-self-development-feedback-loop.md), and [`further-development-universe-brain.md`](further-development-universe-brain.md).

**Read this first:** “Universal” and “all tasks” are **design targets**, not claims about today’s stack. No honest plan promises one 360M model that excels at everything. The path is **orchestration + better models + data + automation + gates**—not a single weight file that magically generalizes.

---

## 1. What “really universal” means (defined tiers)

Use three levels so scope stays honest:

| Tier | Name | What “universal” means | Realistic horizon |
| ---- | ---- | ---------------------- | ----------------- |
| **U1** | **Broad assistant** | One text box handles chat, summarize, retrieve, classify, memory, web, 40+ reply shapes | **Now → 6 months** (extend coverage + quality) |
| **U2** | **Domain platform** | U1 + your org’s docs, auth, eval SLAs, multimodal where needed, tool/API agents | **6–18 months** |
| **U3** | **Self-improving platform** | U2 + automated feedback → eval → promote/rollback with minimal human touch | **18–36+ months** |
| **U4** | **Research north star** | Perception, memory, agency, alignment at scale (“universe brain”) | **Multi-year R&D** |

**This plan focuses on U1 → U3.** U4 stays in the horizon ladder; do not market U1 as U4.

---

## 2. Current baseline (what we extend)

Today’s Universal Brain ([`universal_brain_chat.py`](../scripts/universal_brain_chat.py)) already has:

- **Encoder:** TinyModel1 (classify, embed, RAG)
- **Generator:** SmolLM2-360M-Instruct (default)
- **Router:** JSON intent completion (up to **192** new tokens)
- **NL layers:** session controls + **40+** embedded prompt signals
- **Memory:** SQLite scoped notes
- **RAG:** small FAQ corpus, hybrid retrieval

**Main gaps for “all tasks”:** weak reasoning, tiny context, static FAQ, no auth, no production agent layer, no closed-loop learning from users.

---

## 3. Forward plan (phased)

### Phase A — Quality and coverage (U1 solid, ~8–12 weeks)

**Goal:** Same architecture, measurably better on more task types—not “bigger vision,” **better evidence**.

| Workstream | Actions | Exit gate |
| ---------- | ------- | --------- |
| **A1 Model tier** | Add **model profiles** (fast / balanced / quality) via env or UI; default balanced = current SmolLM2; quality = 1.7B–8B instruct model where GPU allows | Side-by-side eval on 200 golden prompts; quality tier wins on ≥60% of hard tasks |
| **A2 Task matrix** | Document **supported task families** (chat, summarize, RAG Q&A, classify, memory, web, each major `prompt_signal`) with pass/fail rubrics | Automated nightly run (see §5) |
| **A3 RAG upgrade** | Ingestion pipeline: chunk → embed → index; start with repo docs + one customer corpus | Retrieval@3 improves on 50 held-out FAQ questions |
| **A4 Router hardening** | Log router JSON failures; add rule fallback; expand intent examples in tests | Router parse success ≥98% on golden set |
| **A5 NL signal regression** | Auto-generate paraphrase packs per signal (see §4.2) | ≥95% detection recall on paraphrase set without spike in false positives |

**Do not skip:** Hub-vs-local parity and generative-vs-encoder checks from [`plan.txt`](../plan.txt).

---

### Phase B — Domain platform (U2, ~4–9 months)

**Goal:** Suitable for **real teams**, not only public demo.

| Workstream | Actions | Exit gate |
| ---------- | ------- | --------- |
| **B1 Identity & scope** | Real auth (OAuth/API keys); tenant `scope_key`; rate limits | Cross-tenant isolation test passes |
| **B2 Knowledge** | Live connectors (Drive, Confluence, GitHub, or file drop); citation-required mode default for enterprise | Faithfulness spot-check ≥ agreed threshold |
| **B3 Tools & agents** | Bounded tool registry (HTTP allow-list, read-only first); structured plans + audit log | Every side effect logged + policy-checked |
| **B4 Multimodal (selective)** | CLIP path (Horizon 4) behind feature flag for image+text triage | Offline + pilot eval before general enable |
| **B5 Ops** | Metrics, p99 latency budgets, on-call runbook (Horizon 8+ patterns → real dashboards) | SLO defined and measured for 30 days |

---

### Phase C — Self-developing intelligence (U3, ~6–18 months after B)

**Goal:** The system **improves from evidence** with automation; humans approve only high-risk changes.

See §6 for the closed loop. **“Develops by itself”** here means:

- **Automatic collection** of signals (feedback, failures, eval regressions)
- **Automatic proposal** of changes (prompt patches, RAG updates, routing thresholds, fine-tune jobs)
- **Automatic promotion** only when **canary metrics** beat baseline for N days
- **Human gate** for policy, legal, and major model swaps

This is **not** unsupervised AGI self-modification. It is **MLOps + eval discipline + governance**.

---

## 4. Prompt and token budget

### 4.1 Per user turn (today’s Universal Brain)

Rough token accounting for **one smart-routed chat turn** with RAG and brain trace (order-of-magnitude; actual counts depend on message length and tokenizer):

| Component | Input tokens (typical) | Output tokens (typical) |
| --------- | ---------------------- | ----------------------- |
| Base system + reply-style hints | 400–900 | — |
| Embedded `prompt_signals` overlays | 0–400 | — |
| Classifier hint + memory snippets | 0–300 | — |
| FAQ RAG (top-k=2) | 300–1,200 | — |
| Web snippets (if used) | 0–1,500 | — |
| User message | 50–800 | — |
| **Router** (JSON intent) | 200–1,500 (subset of above) | **≤192** (configured max) |
| **Assistant generation** | (all context reused) | **≤512** (default `--max-new-tokens`; tasks same via `--task-max-new-tokens`) |

**Typical total per turn (with routing + RAG, no web):**

| Metric | Low | Typical | Heavy |
| ------ | --- | ------- | ----- |
| **Input tokens** | ~1,000 | ~2,500 | ~5,000 |
| **Output tokens** | ~300 | ~700 | ~900 |
| **Total tokens** | ~1,300 | ~3,200 | ~5,900 |

**Slash-only or `--no-smart-route` chat** (no router call): save **~150–200 output tokens** and one LM forward for routing.

**Tool paths** (`/summarize`, `/grounded`, etc.): similar generation cap (**512** default task tokens) plus tool-specific context.

---

### 4.2 Prompt inventory needed for “universal” *coverage* (testing & training)

“Universal” in engineering terms requires **breadth of prompts**, not one magic prompt.

#### Regression / QA prompts (must-have)

| Suite | Purpose | Target count | Notes |
| ----- | ------- | ------------ | ----- |
| **Intent routing golden set** | chat, summarize, retrieve, web, memory, classify, … | **450–600** | ~15 intents × 30–40 phrasings |
| **Embedded signal paraphrases** | Each `prompt_signals` tag | **800–1,600** | 40+ tags × 20–40 paraphrases |
| **End-to-end task rubrics** | Full reply quality (human or LLM-judge) | **500–2,000** | Stratified by difficulty |
| **RAG faithfulness** | Answer must cite FAQ chunk | **200–500** | Held-out questions |
| **Safety / policy** | Deny, escalate, PII | **100–300** | Required before auto-promotion |
| **Regression after each release** | Smoke subset | **150–300** | CI-friendly |

**Minimum serious U1 test corpus:** ~**2,000 prompts** (mix of unit-style NL detection + E2E).  
**Mature U2/U3 platform:** ~**5,000–15,000** curated prompts + continuous production sample.

#### Fine-tuning / improvement data (optional, later)

| Dataset | Purpose | Scale (starting point) |
| ------- | ------- | ---------------------- |
| Router SFT pairs | `(user text → JSON intent)` | **5k–20k** examples |
| Preference pairs (DPO/RLHF-lite) | Better replies vs baseline | **2k–10k** pairs |
| Encoder label corrections | Horizon 11-style JSONL | **1k+** labeled rows before retrain |
| RAG corpus | Domain docs | **1M–50M tokens** ingested (not “prompts”) |

Store prompts and labels in **versioned Hub datasets** or private object storage—not in git.

---

### 4.3 Token budget by operating scale

Assumes **~3,200 tokens/turn** average (§4.1). Adjust ±40% for your traffic mix.

| Scale | Turns / day | Tokens / day | Tokens / month | Rough LLM API cost* |
| ----- | ----------- | ------------ | -------------- | ------------------- |
| **Demo** (Space) | 200 | 640k | ~19M | tens of USD |
| **Pilot** (1 team) | 2,000 | 6.4M | ~192M | low hundreds USD |
| **Product** (50 teams) | 50,000 | 160M | ~4.8B | thousands USD |
| **Self-improvement overhead** | +10–25% | — | — | eval + synthetic gen |

\*Highly model- and vendor-dependent; use as **planning order of magnitude**. Local GPU inference trades API cost for hardware + ops.

#### Self-improvement loop overhead (additional tokens)

| Activity | Frequency | Tokens per run (order of magnitude) |
| -------- | --------- | ----------------------------------- |
| Nightly regression (2k prompts × ~3k tok) | Daily | ~6M input + ~1.4M output |
| Weekly paraphrase expansion (LLM-assisted) | Weekly | ~500k–2M |
| Monthly encoder re-eval + optional fine-tune | Monthly | ~1M–10M (data size dependent) |
| Canary shadow traffic (5% duplicate) | Continuous | +5% production tokens |

**Rule of thumb:** budget **+15–20%** total tokens for automation until eval is optimized (caching, smaller judge models, subset sampling).

---

## 5. Automation required

Manual iteration does not scale to “universal.” Build these **in order**:

### 5.1 Measurement automation (Phase A — start now)

| Automation | Description | Repo hook today |
| ---------- | ----------- | --------------- |
| **Golden prompt runner** | CLI/CI: run N prompts through local UB or API; JSON results | Extend `horizon2_generative` JSON pattern |
| **NL signal test harness** | Feed paraphrase files; assert `prompt_signals` tags | `tests/test_nl_controls.py` + new corpus dir |
| **Router accuracy report** | Compare routed intent vs expected | New script + CI job |
| **Token/latency logger** | Per-turn: input tok, output tok, route, tools | Add to Space + export JSONL |

### 5.2 Knowledge automation (Phase B)

| Automation | Description |
| ---------- | ----------- |
| **Corpus ingest job** | Watch folder/webhook → chunk → embed → rebuild index |
| **Stale chunk detector** | Hash source docs; re-embed on change |
| **Citation verifier** | Check reply references valid chunk IDs |

### 5.3 Self-development automation (Phase C)

Align with [`universal-brain-self-development-feedback-loop.md`](universal-brain-self-development-feedback-loop.md):

```text
Production / Space
  → structured logs (hashed user id, route, signals, latency, feedback)
  → daily aggregates
  → eval runner (golden + sampled live)
  → change proposer (threshold tune | RAG patch | prompt diff | train job spec)
  → policy gate (Horizon 9-style allow/deny + human approval for tier-1)
  → canary deploy (5–10% traffic)
  → auto-promote OR rollback
  → version bump on Hub (model + Space)
```

| Step | Automate? | Human required? |
| ---- | --------- | ---------------- |
| Log & aggregate | **Yes** | Privacy review once |
| Eval regression | **Yes** | Define rubrics |
| Propose routing threshold | **Yes** | Review first months |
| Propose new NL regex/signal | **Semi** | Review false positives |
| Fine-tune encoder | **Semi** | Approve data + deploy |
| Swap generative model tier | **Semi** | Approve cost + safety eval |
| Policy / legal rules | **No** | Human owners |

**Existing building blocks in this repo:** Horizon 11 feedback JSONL schema, Horizon 24 canary gate smoke, Horizon 10 budget smoke, Phase 1–3 eval artifacts, `parity_check_hub_vs_local.py`, CI deploy workflow.

**Still to build:** persistent log store, scheduled eval orchestrator, promotion service, feedback UI in Space.

---

## 6. Self-developing intelligence — concrete loop

### 6.1 Weekly cycle (minimum viable autonomy)

1. **Collect** — append-only event log: `{turn_id, scope, route, signals, rag_ids, feedback?, latency, model_versions}`.
2. **Sample** — stratified sample for human review (e.g. 50 turns: failures, low confidence, thumbs-down).
3. **Evaluate** — run golden suites (§4.2); compare to last release.
4. **Propose** — if metric X drops > ε, open auto-ticket with diff suggestion (e.g. raise `min_confidence`, add router example, expand NL pattern).
5. **Test** — branch deploy to staging Space; re-run golden.
6. **Promote** — if green for 7 days canary, merge; else rollback.

### 6.2 What can improve *without* retraining the big LM

Often **higher ROI than fine-tuning**:

- RAG corpus and chunking
- Routing thresholds ([`routing_policy.py`](../scripts/routing_policy.py))
- NL control patterns ([`nl_controls.py`](../scripts/nl_controls.py))
- System prompt templates and tool descriptions
- Model tier selection (fast vs quality)
- Web search triggers and citation rules

Automate proposals for these first—they are **cheap, reversible, and testable**.

### 6.3 When to retrain TinyModel1

Trigger (all should be true):

- ≥**1,000** verified label corrections OR new domain dataset ready
- Eval on held-out set beats current Hub model on **macro_f1** + routing metric
- Parity check passes ([`parity_check_hub_vs_local.py`](../scripts/parity_check_hub_vs_local.py))
- Human approves publish

Pipeline already exists: train → `eval_report.json` → publish via HF workflows.

### 6.4 When to fine-tune or swap the generative model

- Hard-task slice on golden set **< target** for 2+ weeks after prompt/RAG fixes
- Budget approved for GPU or API fine-tune
- Safety suite re-run on new weights

Prefer **LoRA / adapter** on open instruct models before full training.

### 6.5 Safety rails (non-negotiable for “self-developing”)

- **Never** auto-promote from raw user feedback alone (poisoning risk)
- **Always** keep held-out golden sets secret from auto-training pipelines
- **Dual control** for policy files and model tier changes (Horizon 48 patterns)
- **Kill switch** env flag to freeze promotions (Horizon 47)
- **Budget cap** on daily eval + train tokens (Horizon 10)

---

## 7. Roadmap timeline (summary)

| Quarter | Focus | Universal tier | Key token/prompt deliverable |
| ------- | ----- | -------------- | ---------------------------- |
| **Q1** | A1–A5: profiles, golden sets, NL/RAG tests | U1 | ~2k golden prompts; nightly CI on 300-smoke subset |
| **Q2** | B1–B2: auth, live corpus | U2 start | Ingest 5–20M doc tokens; 500 RAG eval prompts |
| **Q3** | B3–B5: tools, ops, selective multimodal | U2 | Agent audit logs; SLO dashboards |
| **Q4** | C1: logging + weekly eval + canary promote | U3 start | +15% token budget for automation |
| **Year 2** | C2–C3: semi-auto retrain + generative tier upgrades | U3 mature | 5k–15k prompt corpus; feedback loop live |

Adjust calendar to team size; solo maintainer → stretch 2×.

---

## 8. Decision gates (do not skip)

Before claiming “more universal,” require evidence:

| Gate | Question | Tool |
| ---- | -------- | ---- |
| **G1** | Does encoder Hub match local? | `parity_check_hub_vs_local.py` |
| **G2** | Did we regress routing/RAG? | Golden runner + `horizon1_route_then_retrieve --verify` |
| **G3** | Did NL signals misfire? | Paraphrase harness + `test_nl_controls` |
| **G4** | Can we afford next tier at scale? | Token dashboard (§4.3) |
| **G5** | Is auto-promotion safe? | Canary + safety suite + human sign-off |

---

## 9. Immediate next actions (this month)

1. **Create `texts/golden-prompts/`** (or private dataset) with first **300** prompts: 100 routing, 100 NL signals, 100 E2E tasks.
2. **Add `scripts/ub_eval_runner.py`** (new) — batch local Universal Brain; output JSON like `horizon2` runs.
3. **Log tokens per turn** in Space (stderr or optional JSONL export).
4. **Define model profiles** — document env vars: `HORIZON2_MODEL_FAST`, `HORIZON2_MODEL_QUALITY`.
5. **Wire thumbs up/down** to Horizon 11 JSONL schema (behind consent banner).
6. **Schedule weekly** manual golden run until CI job exists.

---

## 10. Related documents

| Document | Role |
| -------- | ---- |
| [`universal-brain-concept-vs-tinymodel-today.md`](universal-brain-concept-vs-tinymodel-today.md) | Concept vs current state |
| [`tinymodel-text-in-text-out-research.md`](tinymodel-text-in-text-out-research.md) | Research synthesis |
| [`universal-brain-self-development-feedback-loop.md`](universal-brain-self-development-feedback-loop.md) | Closed-loop design |
| [`commercial-models-and-artificial-brain-roadmap.md`](commercial-models-and-artificial-brain-roadmap.md) | Market-realistic ladder |
| [`further-development-universe-brain.md`](further-development-universe-brain.md) | Horizons 0–77 |
| [`model-output-improvement-guide.md`](model-output-improvement-guide.md) | Symptom → fix mapping |

---

## Bottom line

- **Truly universal for all tasks** is a **platform goal (U2–U4)**, not a property of SmolLM2-360M alone.
- Plan for **~2,000+ curated prompts** minimum and **~3,000 tokens per typical turn**; scale monthly tokens linearly with usage and add **15–20%** for self-improvement automation.
- **Self-developing intelligence** means **automated measure → propose → test → promote** with **human gates**—using feedback, eval, RAG, routing, and selective retraining—not unchecked self-modification.

*Revise when model tiers, traffic, or automation ship.*
