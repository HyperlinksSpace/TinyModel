# TinyModel research summary: text-in / text-out intelligence stack

This document synthesizes the research and engineering work completed in the **TinyModel** repository. It is written for stakeholders, collaborators, and future maintainers who need a **single narrative** of what was built, why it was built that way, and what remains open. For operational commands and CI details, see the main [`README.md`](../README.md); for capability tables, see [`universal-brain-capabilities.md`](universal-brain-capabilities.md).

---

## 1. Research thesis

**TinyModel** investigates how far a **small, deployable text stack** can go when every user-facing surface stays **text-in / text-out**: one chat box, plain language in, structured or generative text out. The research hypothesis is that a compact system can remain **useful and governable** if it combines:

1. A **trainable encoder** (classification + dense embeddings) for routing, retrieval, and soft context.
2. A **small instruct language model** for generation under constraints.
3. **Deterministic natural-language layers** that detect intent and reply-shape preferences without asking users to learn a command language.
4. **Explicit evaluation artifacts** so improvements are measurable, not anecdotal.

The project does **not** claim general intelligence or multimodal “brain” completeness. It treats those as **long-horizon design targets** documented separately in [`further-development-universe-brain.md`](further-development-universe-brain.md), while the shipped product surface is **Universal Brain** on Hugging Face.

---

## 2. What “text-in / text-out” means here

In this repository, **text-in / text-out** is an architectural constraint and a product promise:

| Layer | Text in | Text out |
| ----- | ------- | -------- |
| **Universal Brain (Gradio Space)** | Plain chat, slash shortcuts, or short control phrases | Assistant reply, optional *Brain trace* footer (`classify:…`, `RAG:…`, `prompt_signals:…`) |
| **TinyModel1 encoder** | Raw strings | Label probability tables, embedding vectors, similarity scores, retrieval ranks |
| **FAQ RAG** | Natural-language query | Ranked FAQ excerpts with hybrid scores |
| **Horizon 2 generative path** | Prompt + optional context file | Summaries, reformulations, grounded answers (JSON run artifacts for regression) |
| **Horizon 3 memory** | Scoped notes via chat or CLI | Listed/exported memory rows, audit-shaped JSON |

**Deliberately out of scope** on the public demo: images, audio, video, and authenticated multi-tenant SaaS. CLIP-style multimodal work exists as **Horizon 4 smoke experiments**, not as the default Space experience.

**Live surfaces:**

- Model: [HyperlinksSpace/TinyModel1](https://huggingface.co/HyperlinksSpace/TinyModel1)
- Space: [HyperlinksSpace/TinyModel1Space](https://huggingface.co/spaces/HyperlinksSpace/TinyModel1Space)
- Direct app: [hyperlinksspace-tinymodel1space.hf.space](https://hyperlinksspace-tinymodel1space.hf.space)

---

## 3. Encoder research (TinyModel1, Phases 1–3)

### 3.1 Core model

**TinyModel1** is a **small BERT-style encoder** trained from scratch (WordPiece tokenizer fit on training data, Transformer stack, classification head). Default public demo labels follow **AG News** semantics: World, Business, Sports, Sci/Tech.

Research goals for the encoder lane:

- Prove **reproducible** training with fixed seeds, capped subsets, and structured reports.
- Compare **scratch vs pretrained** fine-tune paths on multiple reference datasets.
- Support **runtime reuse** of the same checkpoint for classify, embed, similarity, and retrieve—not only argmax labels.

Key artifacts per training run:

- `eval_report.json` — metrics, confusion matrix, reproducibility block, Phase 2 quality fields (class distribution, top confusions, calibration histogram, routing notes).
- `misclassified_sample.jsonl` — wrong predictions for error analysis.
- Hub-ready weights, tokenizer, model card.

### 3.2 Phase 1 — stabilize and compare

[`phase1_compare.py`](../scripts/phase1_compare.py) standardizes presets (`smoke`, `dev`, `full`) and produces comparison matrices (accuracy, macro F1, per-class F1) across datasets and model origins. This prevents ad-hoc hyperparameter drift and gives a **scientific baseline** before scaling data or architecture.

### 3.3 Phase 2 — evaluation quality beyond accuracy

Phase 2 research asks: *when is the model confidently wrong?* Training now emits:

- **Dataset quality** — label distribution on train/eval caps.
- **Error analysis** — largest off-diagonal confusion pairs.
- **Calibration** — histogram of winner softmax probability.
- **Routing notes** — documented fallback behavior for low-confidence triage (thresholds tuned on validation data, not fixed by training).

[`routing_policy.py`](../scripts/routing_policy.py) implements **min-confidence** and **min-margin** gates on classifier outputs—the bridge from “label prediction” to **safe routing**.

### 3.4 Phase 3 — deployment-shaped research

Phase 3 extends the encoder story toward **serving**:

- ONNX export and PyTorch vs ONNX Runtime **parity**.
- CPU **benchmarks** (classify / embed / retrieve patterns).
- Reference HTTP API contract (`/v1/classify`, `/v1/retrieve`, health checks).

This answers whether the same small model can run **outside notebooks** with predictable numerics and latency envelopes.

### 3.5 Multi-dataset breadth (Horizon 1 B)

Beyond AG News, the stack validates on **Emotion** (6-class) and **SST-2** (binary sentiment), confirming one training harness serves multiple label schemas. Summaries live in [`horizon1-three-tasks-summary.md`](horizon1-three-tasks-summary.md).

---

## 4. Retrieval and route-to-RAG research

A second research thread asks: *what should happen when classification is uncertain?*

**Implemented pipeline:**

```
user query
  → TinyModelRuntime.classify()
  → routing_policy (confidence + margin gates)
  → if accept: use label as soft hint
  → if fallback: hybrid FAQ retrieval (keyword + embedding similarity)
```

Components:

| Module | Role |
| ------ | ---- |
| [`tinymodel_runtime.py`](../scripts/tinymodel_runtime.py) | Load checkpoint; classify, embed, similarity, retrieve |
| [`routing_policy.py`](../scripts/routing_policy.py) | Deterministic accept/fallback from probability dict |
| [`rag_faq_smoke.py`](../scripts/rag_faq_smoke.py) | Chunk [`rag_faq_corpus.md`](rag_faq_corpus.md); hybrid ranking |
| [`horizon1_route_then_retrieve.py`](../scripts/horizon1_route_then_retrieve.py) | End-to-end glue with `--verify` gates matching CI |

This is **prototype RAG**, not production-scale retrieval—but it is **repeatable**, logged, and wired into Universal Brain’s FAQ tool.

Design note: [`single-input-multipurpose-routing.md`](single-input-multipurpose-routing.md) documents the **single-input orchestrator** pattern (intent detection → argument extraction → function execution → formatted response). The Space implements **Pattern A (rules) + JSON LLM router + confidence fallback**, which is the recommended MVP path from that research note.

---

## 5. Universal Brain: converged text-in / text-out product

Universal Brain ([`universal_brain_chat.py`](../scripts/universal_brain_chat.py)) is the **integration research artifact**: one Gradio UI that composes six subsystems:

1. **Generative instruct LM** — default `HuggingFaceTB/SmolLM2-360M-Instruct` (override `HORIZON2_MODEL`).
2. **TinyModel1 encoder** — topic soft hint + embeddings for similarity, nearest, and RAG.
3. **FAQ hybrid RAG** — bundled corpus, grounding strictness toggles.
4. **Horizon 3 SQLite memory** — session vs long-term notes scoped by `scope_key`.
5. **JSON intent router** — maps plain language to tools (summarize, retrieve, web_search, classify, memory, …).
6. **Natural-language control layers** — session phrases + **embedded prompt signals** (see §6).

Optional **Google Custom Search** injects web snippets when Hub secrets are configured; the model is instructed to cite `[Web n]` when using them.

**Brain trace** (when enabled) makes routing research **observable**: users and maintainers see classifier hints, RAG/memory flags, and the **`prompt_signals:`** footer that records which NL-detected reply overlays fired for that turn.

Space artifacts are built by [`build_space_artifact.py`](../scripts/build_space_artifact.py) and deployed via GitHub Actions (`deploy-hf-space-versioned.yml`).

---

## 6. Natural-language detection research (primary recent work)

The most active research line in recent development is **natural-language detection of features**: users write normal questions; the system **infers** which reply contract to apply **for one turn**, without slash commands or a settings panel.

Implementation lives in [`nl_controls.py`](../scripts/nl_controls.py) (~4,500 lines of deterministic regex and conservative phrase matching).

### 6.1 Two NL layers

| Layer | Trigger style | Persistence | Examples |
| ----- | -------------- | ----------- | -------- |
| **Session control phrases** | Short, explicit | Until reset / new session | *Be brief*, *Show the brain trace*, *Strict FAQ*, *Start a new private session* |
| **Embedded prompt signals** | Cues inside **long** normal chat | **One turn only** | *pros and cons*, *RACI matrix*, *write an email*, *five whys*, *Mermaid diagram* |

**Conservative design principles** (documented in code and tests):

- Only fire on **fairly explicit** wording; ambiguous lines do not silently flip behavior.
- **Conflicting cues** in one message usually disable both sides (e.g. *pros and cons* + *no pros and cons*).
- Short-line **trace toggles** are length-capped so long prompts are not hijacked as control commands (regression fix: `144d697`).

### 6.2 Embedded prompt signal catalog (40+ families)

Signals are grouped by research intent:

**Layout and comparison** — `comparison_frame=pros_cons|narrative`, table prefer/avoid, bullets vs prose, numbered vs continuous steps, section headings, FAQ Q&A pairs.

**Length and verbosity** — `verbosity=brief|detailed`, word/sentence caps (`len_cap=80w`).

**Code and math** — `code_only`, `code_explained`, `pseudocode`, `runnable_code`, fenced vs inline code, show-work vs final-only math.

**Decision and planning formats** — `ranked_options`, `decision_matrix`, `build_vs_buy`, `one_pager`, `status_report`, `action_plan`, `raci`, `stakeholder_map`, `cost_benefit`, `go_no_go`, `options_n=N`, checklists.

**Professional document genres** — `email_format`, `letter_format`, `press_release`, `release_notes`, `runbook_format`, `job_aid`, `meeting_agenda`.

**Analysis frameworks** — `swot`, `pestle`, `frame_star|prep|irac`, `five_whys`, `fishbone`, `postmortem`, `sprint_retro`, `user_story`, `definition_of_done`.

**Editing and guardrails** — `revise_draft`, `revise_diff`, `topic_guard`, `topic_must`, `glossary`, `open_questions`, scenario cases.

**Tone, audience, and language** — ELI5 vs technical audience, formal/casual register, second/third person, UK/US spelling, reply language, speculation strict vs creative, red-team vs supportive coaching.

**Sources and grounding** — cite sources vs minimal links, FAQ quote vs paraphrase, FAQ grounding strict/relaxed.

**Opening and closing shape** — BLUF / direct answer, recommendation-first, summary at end.

Each detector returns a **machine-readable tag** appended to the system prompt for that generation and echoed in **`prompt_signals:`** when trace is on. The Space UI includes a **Testing embedded prompt signals** table (synced from `GRADIO_INSTRUCTIONS_MARKDOWN` in `universal_brain_chat.py`) so researchers can copy-paste probes and verify detection on the live app.

### 6.3 Why deterministic NL detection (not only LLM routing)

Research rationale:

| Approach | Benefit | Risk |
| -------- | ------- | ---- |
| **Deterministic regex/phrase rules** | Debuggable, fast, no extra model call, reproducible in unit tests | Limited paraphrase coverage |
| **JSON LLM intent router** | Flexible tool selection for diverse phrasing | Latency, cost, schema validation burden |
| **Hybrid (this repo)** | Router picks **tool**; `nl_controls` picks **session** and **reply shape** | Two systems must stay documented and tested |

The embedded-signal layer is intentionally **orthogonal** to TinyModel1 classification: reply formatting is a **generative UX** problem, not a 4-label topic task. Keeping it in Python regex makes CI coverage practical (`tests/test_nl_controls.py` and related help tests).

Recent commit history (2025–2026) shows iterative expansion of genre detectors: stakeholder maps, sprint retros, user stories, DoD, runbooks, job aids, status reports, press releases, release notes, and paired risks/mitigations—each with Space testing instructions and README sync.

---

## 7. Generative, memory, and multimodal research (Horizons 2–4)

These horizons extend the text stack without replacing the encoder:

| Horizon | Research question | MVP in repo |
| ------- | ----------------- | ----------- |
| **H2 Generative** | Can a small instruct LM produce drafts/summaries with JSON regression artifacts? | `horizon2_generative.py`, optional FastAPI server |
| **H3 Memory** | Can session vs long-term memory be scoped, audited, exported, forgotten? | SQLite CLI + optional HTTP API |
| **H4 Multimodal** | Can image–caption alignment score support triage? | CLIP smoke (`horizon4_multimodal.py`, offline CI verify) |
| **H6 Converged** | Do H2+H3+H4 smokes chain cleanly? | `horizon6_converged_smoke.py` |

Universal Brain **productizes H2 + H3 + encoder + RAG** in one Gradio app; H4 remains experimental.

---

## 8. Governance and platform research (Horizons 7–77)

A parallel research program encodes **enterprise-shaped concerns** as **stdlib JSON manifests + `--verify` smokes**: tenant isolation, observability probes, declarative policy, budget caps, feedback JSONL, provenance hashes, circuit breakers, semver gates, crypto suites, legal-hold locks, pen-test finding ceilings, and dozens more.

These are **contract and education artifacts**, not production enforcement. They document what a “universe brain” platform would need to **prove** before claiming assurances. See [`tinymodel-current-state-and-product-path.md`](tinymodel-current-state-and-product-path.md) for the honest gap between **smoke MVPs** and **shippable multi-tenant products**.

---

## 9. Evaluation, parity, and maintainer exit gates

Current maintainer focus ([`plan.txt`](../plan.txt)):

1. **Hub vs local parity** — train a fixed-seed checkpoint locally; compare to published `HyperlinksSpace/TinyModel1` via [`parity_check_hub_vs_local.py`](../scripts/parity_check_hub_vs_local.py).
2. **Generative vs encoder role split** — generation smoke (`horizon2_generative.py`) vs route-to-RAG verify (`horizon1_route_then_retrieve.py --verify`); symptoms mapped in [`model-output-improvement-guide.md`](model-output-improvement-guide.md).

CI runs **stdlib unit tests first** (including NL control and routing tests), then Phase 1/3 smokes, Horizon smokes, and Space deploy workflows—see [`.github/workflows/`](../.github/workflows/).

---

## 10. Research outcomes (what we can claim today)

**Demonstrated:**

- A **reproducible small encoder** with multi-dataset training, rich eval reports, ONNX path, and Hub publication.
- A **text-in / text-out assistant** combining generation, classification hints, hybrid FAQ RAG, scoped memory, optional web search, and **40+ NL-detected reply overlays**.
- A **route-to-RAG** story with explicit confidence fallback—not silent wrong routing.
- **Observable routing** via brain trace and structured JSON run artifacts across horizons.
- **Extensive CI** tying training, parity, NL controls, and deploy into repeatable checks.

**Not demonstrated (honest limits):**

- Strong reasoning on hard multi-step problems (small LMs remain shallow).
- Hallucination-free answers (RAG/web reduce but do not eliminate errors).
- Real authentication, billing, abuse prevention, or legal compliance at scale.
- Unified production runtime replacing script collection (Horizons 6–77 are mostly smokes).
- Continual learning from live users without explicit pipelines.

---

## 11. Open research questions

1. **Intent classifier (Pattern B)** — Should tool routing graduate from JSON LLM + rules to a small fine-tuned intent model trained from logged `route_query` decisions?
2. **Signal calibration** — How often do embedded prompt signals misfire on paraphrases, and should low-confidence detections ask a one-line clarification?
3. **Encoder refresh** — When does Hub-vs-local parity drift enough to require republish, and which dataset mix best serves Universal Brain’s FAQ + classify hints?
4. **Grounding metrics** — What automatic faithfulness/citation checks beyond hybrid retrieval scores are worth adding to Phase 2-style reports?
5. **Multimodal productization** — Under what vertical constraints does H4 CLIP scoring belong in the same chat box?

Backlog items: [`optional-rd-backlog.md`](optional-rd-backlog.md), [`universal-brain-session-improvement-plan.txt`](universal-brain-session-improvement-plan.txt).

---

## 12. How to reproduce key research paths

**Train encoder (smoke):**
```bash
python scripts/train_tinymodel1_agnews.py --output-dir .tmp/TinyModel-local
```

**Phase 1 matrix:**
```bash
python scripts/phase1_compare.py --preset smoke --models scratch --datasets ag_news,emotion --seed 42
```

**Route-to-RAG verify:**
```bash
python scripts/horizon1_route_then_retrieve.py --verify --model .tmp/TinyModel-local
```

**Universal Brain locally:**
```bash
python scripts/universal_brain_chat.py
```

**NL controls unit tests:**
```bash
python -m unittest discover -s tests -p "test_nl_controls*.py" -v
```

**Build Space artifact:**
```bash
python scripts/build_space_artifact.py --namespace HyperlinksSpace --version 1
```

---

## 13. Related documents

| Document | Contents |
| -------- | -------- |
| [`README.md`](../README.md) | Full command reference, Horizon index, CI workflows |
| [`universal-brain-capabilities.md`](universal-brain-capabilities.md) | Maintainer capability tables |
| [`implemented-results-summary.md`](implemented-results-summary.md) | Short-term plan completion checklist |
| [`deep-learning-and-tinymodel-project.md`](deep-learning-and-tinymodel-project.md) | DL concepts mapped to this repo |
| [`single-input-multipurpose-routing.md`](single-input-multipurpose-routing.md) | Orchestrator patterns for one input box |
| [`commercial-models-and-artificial-brain-roadmap.md`](commercial-models-and-artificial-brain-roadmap.md) | Market-realistic positioning |
| [`further-development-universe-brain.md`](further-development-universe-brain.md) | Long-horizon “universe brain” ladder |
| [`plan-internet-access-for-universal-brain.md`](plan-internet-access-for-universal-brain.md) | Web search provider research |

---

*Last updated to reflect the Universal Brain embedded prompt signal program, Phases 1–3 encoder stack, and Horizon 1 route-to-RAG integration. Revise when shipped capabilities or public artifacts change.*
