# Universal brain (TinyModel line): current state, features, launch, and testing

This note summarizes **what exists in this repository and on Hugging Face today** under the “universe brain” / universal-brain roadmap framing. It is **not** a claim that TinyModel is already a complete autonomous universal intelligence—it is a **practical baseline** plus **staged horizon experiments** documented in [`further-development-universe-brain.md`](further-development-universe-brain.md).

For stakeholder-facing synthesis see also [`tinymodel-current-state-and-product-path.md`](tinymodel-current-state-and-product-path.md).

---

## Positioning

- **Core strength:** small, deployable **text classification** with reproducible training and structured **eval artifacts** (`eval_report.json`, confusion insights, calibration histograms—see main [`README.md`](../README.md) Phase 2).
- **Roadmap:** multimodal demos, memory-shaped tooling, composition scripts, and many **horizon smokes** that encode governance-style checks as JSON manifests plus `--verify` scripts.

---

## What you can use on Hugging Face (today)

| Artifact | URL | What it is |
| -------- | --- | ---------- |
| **Model weights + tokenizer + model card** | [HyperlinksSpace/TinyModel1](https://huggingface.co/HyperlinksSpace/TinyModel1) | Encoder-style classifier suitable for `transformers` pipelines where supported |
| **Space (Gradio app)** | [HyperlinksSpace/TinyModel1Space](https://huggingface.co/spaces/HyperlinksSpace/TinyModel1Space) | Interactive demo tied to the project |
| **Direct app URL** | [hyperlinksspace-tinymodel1space.hf.space](https://hyperlinksspace-tinymodel1space.hf.space) | Same UI as the Space; use Hub link if regions block direct preview |

 Maintainer workflows and CI deployment hooks are summarized in [`texts/HUGGING_FACE_DEPLOYMENT_INTERNAL.md`](HUGGING_FACE_DEPLOYMENT_INTERNAL.md) and [`README.md`](../README.md) (workflow names near the end of the file).

---

## Features implemented in-repo (engineering)

These are **development and experimentation** surfaces—mix and match for products:

| Area | Feature | Entry points |
| ---- | ------- | ------------ |
| **Training / eval** | Reproducible classifier training, Phase 1 comparison matrix, Phase 2 richer reports | `scripts/train_tinymodel1_classifier.py`, wrappers `train_tinymodel1_agnews.py`, `emotion`, `sst2`; `scripts/phase1_compare.py` |
| **Runtime** | Classification, similarity, retrieval over a candidate list | `scripts/tinymodel_runtime.py` (`TinyModelRuntime`) |
| **Generative (Horizon 2)** | Optional causal LM path with JSON run artifacts | Scripts referenced under Horizon 2 in [`README.md`](../README.md) |
| **Memory (Horizon 3)** | SQLite session vs long-term store, audit/export patterns | Scripts referenced under Horizon 3 in [`README.md`](../README.md) |
| **Multimodal (Horizon 4)** | CLIP-style image–caption alignment smoke | Scripts referenced under Horizon 4 in [`README.md`](../README.md) |
| **Governance smokes (Horizons 6+)** | Large ladder of manifest-driven `--verify` checks | [`README.md`](../README.md) horizon sections; [`texts/further-development-universe-brain.md`](further-development-universe-brain.md) |

Embeddings smoke for routing/search-shaped flows: `scripts/embeddings_smoke_test.py` (see [`README.md`](../README.md)).

---

## How to launch locally (minimal)

**Train a small checkpoint** (example: AG News wrapper):

```bash
python scripts/train_tinymodel1_agnews.py --output-dir .tmp/TinyModel-local
```

**Quick inference sanity check** (local folder):

```bash
python -c "from transformers import pipeline; p=pipeline('text-classification', model='.tmp/TinyModel-local', tokenizer='.tmp/TinyModel-local'); print(p('Stocks rallied after central bank comments', top_k=None))"
```

**Phase 1 smoke** (CI-aligned):

```bash
python scripts/phase1_compare.py --preset smoke --models scratch --datasets ag_news,emotion --seed 42
```

**Phase 2 tiny smoke**:

```bash
python scripts/train_tinymodel1_classifier.py \
  --output-dir .tmp/phase2-smoke \
  --max-train-samples 64 --max-eval-samples 32 \
  --epochs 1 --batch-size 8 --seed 42 \
  --max-misclassified-examples 20
```

Inspect `.tmp/phase2-smoke/eval_report.json` and optional `misclassified_sample.jsonl`.

---

## How to test horizon governance scripts

Horizon scripts follow the pattern:

```bash
python scripts/<horizon>_smoke.py --verify
```

They load JSON manifests under `texts/` and write run artifacts under `.tmp/` (see each horizon section in [`README.md`](../README.md)). CI mirrors many of these via `.github/workflows/horizon*-smoke.yml`.

---

## What is *not* included yet

- A **single hosted SaaS** with billing, multi-tenant isolation, and abuse tooling at scale (called out explicitly in [`tinymodel-current-state-and-product-path.md`](tinymodel-current-state-and-product-path.md)).
- **Fully automated** continuous learning from live users without explicit pipelines (described as a direction in [`universal-brain-self-development-feedback-loop.md`](universal-brain-self-development-feedback-loop.md)).

---

## Next steps toward a stronger Hub “universal brain” product

1. Keep **eval tables** on the model card tied to reproducible commands.
2. Expand the **Space** UX only where grounded by measured metrics (latency, accuracy slices).
3. Add **instrumentation + consent** before collecting feedback for training.
4. Align releases with **horizon gates** you actually intend to enforce in production.

Revise this document when shipped capabilities change.
