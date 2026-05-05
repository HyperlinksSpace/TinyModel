# How to improve model output (Universal Brain / TinyModel)

This note ties **what you see in the chat** to **what to change in the repo**. For a line-by-line walkthrough of a sample session (classifier flatness, RAG size, `/nearest` quirks, brain trace), see [`universal-brain-session-improvement-plan.txt`](universal-brain-session-improvement-plan.txt).

---

## Quick read of typical outputs

| Symptom | Likely cause | First levers |
| -------- | -------------- | ------------- |
| Topic winner around **0.25–0.27** with all four labels within a few points | Encoder head is **uncertain** on that sentence (common on World vs Business for macro/energy news, or weak fine-tune) | More/better **AG News–style** (or custom) training data; optional **“low confidence”** UX when top-1 − top-2 is tiny |
| `/summarize` answers a **placeholder** (“paste here…”) as if it were content | Router or user message carried **instruction text**, not a real passage | **Pre-flight**: reject very short / boilerplate “sources”; teach users to paste text in the same message (see `/help` in `universal_brain_chat.py`) |
| `/reformulate` is **slow** (~10–20 s) and still **verbose** | **CPU** decode on a 360M instruct model; **256** default cap on `--task-max-new-tokens` still allows long replies | **GPU** / smaller `--model`; lower `--task-max-new-tokens`; tighten `build_user_prompt(..., task="reformulate")` in `horizon2_core.py` (e.g. cap words for one-line inputs) |
| `/grounded` is **faster** and more **faithful** than open chat | Constrained task with explicit context | For policy questions, prefer **retrieve → grounded** when FAQ chunks exist |
| `/retrieve` second hit is **off-topic** but plausible | **Tiny corpus** (e.g. four chunks) limits ranking | Expand [`rag_faq_corpus.md`](rag_faq_corpus.md); tune hybrid weights in `rag_faq_smoke.py`; optional reranker later |
| `/nearest` picks a candidate that is **lexically** close but **wrong intent** (e.g. “refund policy” → “exchanges only”) | **Pooled embedding** geometry vs query; `/embed` shows **raw [CLS]**, not necessarily the same normalization as retrieve | Align **L2-normalized** cosine everywhere; try **mean pooling** vs `[CLS]` after retrain; blend with **BM25** on the same strings |
| “Brain trace” shows **classify:World** while the reply feels unrelated | Trace is an **encoder hint for the whole user line**, not a post-hoc explanation of the last sentence only | Use `--no-trace` if noisy; treat trace as **debug**, not ground truth |
| **Header / menu flashes** when widening or narrowing the window | **Responsive layout** recomputes breakpoints; a brief resize can pick a **default variant** before the final width settles | Fix in the **hosting UI** (Space shell, Expo/web app): **debounce** resize, **hold the last stable layout** until a new breakpoint is stable (hysteresis), avoid rendering a “loading” layout between states |

---

## Improving the **classifier / encoder** (TinyModel)

1. **Train or continue training** on your distribution (AG News is only a default story topic schema):
   - Entry points: `scripts/train_tinymodel1_classifier.py`, `scripts/train_tinymodel1_agnews.py` (see also [`universal-brain-current-state-features-and-testing.md`](universal-brain-current-state-features-and-testing.md)).
2. **Point the chat** at the new checkpoint: `python scripts/universal_brain_chat.py --encoder /path/to/checkpoint`.
3. **Evaluate** with Phase 2-style reports (`eval_report.json`, misclassified samples) so improvements show up as higher margins and better calibration—not only a higher top-1 on a single example.

---

## Improving the **generative** side (SmolLM2 or replacement)

1. **`--model`** — Larger models improve quality; smaller ones improve latency.
2. **`--task-max-new-tokens`** — Cuts tail verbosity for `/summarize`, `/reformulate`, `/grounded`.
3. **Prompts** — `build_user_prompt` and `DEFAULT_CHAT_SYSTEM` in `scripts/horizon2_core.py` control tone and length; adjust before chasing a new HF model.
4. **Router** — `--router-max-new-tokens` caps JSON routing completions; `--no-smart-route` avoids mis-routes at the cost of manual `/…` commands.

---

## Improving **RAG and memory**

- **RAG:** grow and structure the FAQ markdown; adjust `--rag-top-k` and corpus chunking so hybrid search has real headroom.
- **Memory:** scope and DB path are documented in the improvement plan; long-term vs session behavior is intentional—clarify in product copy if users are confused.

---

## Suggested priority

Match the existing plan: **placeholder guard + embedding consistency (P0)**, **classifier confidence and boundary data (P1)**, **generation length/latency (P2)**, **corpus and hybrid tuning (P3)**, **trace/router clarity (P4)**.

---

## Related docs

- [`universal-brain-session-improvement-plan.txt`](universal-brain-session-improvement-plan.txt) — detailed actions from a real session log  
- [`horizon1-short-term-handbook.md`](horizon1-short-term-handbook.md) — route-to-RAG, encoder smoke, three-task matrix  
- [`horizon2-handbook.md`](horizon2-handbook.md) — generative CLI, server, tiers  
- [`tinymodel-current-state-and-product-path.md`](tinymodel-current-state-and-product-path.md) — product framing  
- [`commercial-models-and-artificial-brain-roadmap.md`](commercial-models-and-artificial-brain-roadmap.md) — demand categories vs “brain” direction  
- [`README.md`](../README.md) — training phases and smoke commands  
