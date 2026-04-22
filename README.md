<div align="center">

# TinyModel

### Tiny, deployable text classification baseline for rapid product iteration

[![Model](https://img.shields.io/badge/Hugging%20Face-TinyModel1-yellow)](https://huggingface.co/HyperlinksSpace/TinyModel1)
[![Space Hub](https://img.shields.io/badge/Space%20Hub-TinyModel1Space-orange)](https://huggingface.co/spaces/HyperlinksSpace/TinyModel1Space)
[![Live preview](https://img.shields.io/badge/Live%20preview-Gradio%20app-brightgreen)](https://hyperlinksspace-tinymodel1space.hf.space)

</div>

`TinyModel` is a practical starter model line for text classification.
End users consume deployed Hugging Face model and Space endpoints. Maintainer deployment policy lives in `texts/HUGGING_FACE_DEPLOYMENT_INTERNAL.md`.

Repository: [HyperlinksSpace/TinyModel](https://github.com/HyperlinksSpace/TinyModel)

**TinyModel1 on Hugging Face**

- **Model weights & model card** — [HyperlinksSpace/TinyModel1](https://huggingface.co/HyperlinksSpace/TinyModel1): Safetensors, tokenizer, and `README.md` on the Hugging Face Hub (load with `transformers` or the Inference API where available).
- **Space project (Hub)** — [HyperlinksSpace/TinyModel1Space](https://huggingface.co/spaces/HyperlinksSpace/TinyModel1Space): Space repository (app code, build logs, settings, community).
- **Live Gradio app** — **Direct app URL:** [https://hyperlinksspace-tinymodel1space.hf.space](https://hyperlinksspace-tinymodel1space.hf.space) · **Same app on the Hub:** [huggingface.co/spaces/HyperlinksSpace/TinyModel1Space](https://huggingface.co/spaces/HyperlinksSpace/TinyModel1Space). If the direct link fails or is blocked, use the Hub link or see **Availability in Russia** below.

**Availability in Russia**

Some features may not work reliably from Russia—for example **live preview** or other flows that depend on third-party hosts or regions that are blocked or throttled. If you hit that, you can try third-party tools such as the free tier of [1VPN](https://1vpn.org/) (browser extension or app), or **Happ** (paid subscription). One place people buy Happ subscriptions is [this Telegram bot](https://t.me/tylervpsbot). These are all **third-party** services; use at your own discretion and follow applicable laws.

**Model card (README)** — On the Hub, the model card is the **`README.md`** file at the root of the model repo (same URL as the model). In this repository, the template is implemented by `write_model_card()` in [`scripts/train_tinymodel1_classifier.py`](https://github.com/HyperlinksSpace/TinyModel/blob/main/scripts/train_tinymodel1_classifier.py); training writes `README.md`, [`artifact.json`](https://github.com/HyperlinksSpace/TinyModel/blob/main/scripts/train_tinymodel1_classifier.py), and `eval_report.json` next to the weights. We do **not** run CI that downloads full model weights into the repo or runner caches for republish; update the card by retraining and publishing, or edit `README.md` on the Hub and keep weights unchanged.

## 1) Local testing

Train locally after cloning the repo:

```bash
python scripts/train_tinymodel1_agnews.py --output-dir .tmp/TinyModel-local
```

Quick local inference sanity check:

```bash
python -c "from transformers import pipeline; p=pipeline('text-classification', model='.tmp/TinyModel-local', tokenizer='.tmp/TinyModel-local'); print(p('Stocks rallied after central bank comments', top_k=None))"
```

### Phase 1 presets and comparison matrix

`scripts/phase1_compare.py` standardizes run profiles and prevents ad-hoc parameter drift.
It executes matching-seed runs and writes a comparison matrix with `accuracy`, `macro_f1`,
and per-class F1 for each run.

Presets:

- `smoke`: quickest reproducibility/health check (`120/80`, `1 epoch`)
- `dev`: day-to-day iteration (`1000/300`, `2 epochs`)
- `full`: heavier baseline (`6000/1200`, `3 epochs`)

Run full Phase 1 baseline comparison (scratch vs pretrained) on both AG News and Emotion:

```bash
python scripts/phase1_compare.py --preset smoke --seed 42
```

Outputs:

- `artifacts/phase1/runs/<preset>/<dataset>/<model>/...` (model artifacts per run)
- `artifacts/phase1/reports/phase1_<preset>_seed<seed>.md` (human-readable table)
- `artifacts/phase1/reports/phase1_<preset>_seed<seed>.csv` (spreadsheet-friendly)
- `artifacts/phase1/reports/phase1_<preset>_seed<seed>.json` (machine-readable)

CI smoke check (no heavy pretrained download by default):

```bash
python scripts/phase1_compare.py \
  --preset smoke \
  --models scratch \
  --datasets ag_news,emotion \
  --seed 42
```

This same default check is wired in `.github/workflows/phase1-smoke.yml`.

## Phase 2: Evaluation quality (datasets, errors, calibration)

Training and pretrained fine-tuning now emit richer evaluation artifacts so reports support decisions beyond headline accuracy.

| Artifact | What it contains |
| -------- | ---------------- |
| **`eval_report.json`** | Existing `reproducibility` + `metrics`, plus **`dataset_quality.class_distribution`** (train/eval counts and proportions per label on the capped subsets), **`error_analysis.top_confusions`** (largest off-diagonal confusion pairs), **`calibration.max_prob_histogram`** (bins over the winner softmax probability per eval example), and **`routing`** (documented fallback behavior for low-confidence routing; thresholds are not fixed by training). |
| **`misclassified_sample.jsonl`** | Up to **`--max-misclassified-examples`** wrong predictions with `text`, `true_label`, `predicted_label`, `max_prob` (one JSON object per line). Use `0` to skip writing the file content beyond an empty run. |

CLI knobs (scratch and [`finetune_pretrained_classifier.py`](scripts/finetune_pretrained_classifier.py)):

- `--max-misclassified-examples` (default `100`)
- `--confidence-histogram-bins` (default `10`)
- `--top-confusions` (default `20`)

**Third reference dataset (SST-2)** — binary sentiment on GLUE, useful as an additional domain check:

```bash
python scripts/train_tinymodel1_sst2.py \
  --output-dir .tmp/TinyModel-sst2 \
  --max-train-samples 500 \
  --max-eval-samples 200 \
  --epochs 1 \
  --batch-size 8 \
  --seed 42
```

Quick Phase 2 smoke (AG News, small caps):

```bash
python scripts/train_tinymodel1_classifier.py \
  --output-dir .tmp/phase2-smoke \
  --max-train-samples 64 \
  --max-eval-samples 32 \
  --epochs 1 \
  --batch-size 8 \
  --seed 42 \
  --max-misclassified-examples 20
```

Then inspect `.tmp/phase2-smoke/eval_report.json` (new sections) and `.tmp/phase2-smoke/misclassified_sample.jsonl`.

Expected local output folder:

- `.tmp/TinyModel-local/model.safetensors`
- `.tmp/TinyModel-local/config.json`
- `.tmp/TinyModel-local/tokenizer.json`
- `.tmp/TinyModel-local/README.md`
- `.tmp/TinyModel-local/artifact.json`
- `.tmp/TinyModel-local/eval_report.json` — evaluation metrics, confusion matrix, reproducibility, and Phase 2 fields (class distribution, top confusions, calibration histogram, routing notes)
- `.tmp/TinyModel-local/misclassified_sample.jsonl` — optional sample of errors for review (see Phase 2 section)

### Training script: evaluation and artifacts

The canonical training implementation is [`scripts/train_tinymodel1_classifier.py`](https://github.com/HyperlinksSpace/TinyModel/blob/main/scripts/train_tinymodel1_classifier.py). [`scripts/train_tinymodel1_agnews.py`](https://github.com/HyperlinksSpace/TinyModel/blob/main/scripts/train_tinymodel1_agnews.py) is a thin wrapper that calls the same `main()` with AG News–friendly defaults.

| Function / area | Role |
| ---------------- | ---- |
| **`parse_args()`** | CLI for dataset id, splits, text/label columns, caps, hyperparameters, `--seed`, and Hub card metadata. |
| **`set_seed()`** | Sets Python, NumPy, and PyTorch RNGs so runs are repeatable for a given `--seed`. |
| **`load_splits()`** | Loads the Hub dataset, selects train/eval split names, **shuffles each split with `seed`**, then takes the first *N* rows (`--max-train-samples`, `--max-eval-samples`). |
| **`infer_text_column()`** | Picks the text column if you do not pass `--text-column`. |
| **`resolve_label_names()`** / **`build_label_maps()`** / **`rows_to_model_inputs()`** | Resolve class names, map raw labels to contiguous ids, and build `Dataset` columns for training. |
| **`build_tokenizer()`** | Trains a WordPiece tokenizer on training texts and writes tokenizer files under the output dir. |
| **`evaluate()`** / **`evaluate_with_details()`** | Runs eval, builds the confusion matrix and **`EvalMetrics`**; **`evaluate_with_details`** also records per-example **max softmax** (winner) probability for calibration histograms. |
| **`write_eval_report()`** | Writes **`eval_report.json`**: `reproducibility`, `metrics`, plus optional **`dataset_quality`**, **`error_analysis`**, **`calibration`**, **`routing`** (see Phase 2 section). |
| **`write_misclassified_jsonl()`** | Writes **`misclassified_sample.jsonl`** (up to N lines) for manual error review. |
| **`write_manifest()`** | Writes **`artifact.json`**: training config, labels, and summary metrics for downstream tooling. |
| **`write_model_card()`** | Writes Hub-style **`README.md`** next to the weights (model card with eval summary). |
| **`copy_model_card_image()`** | Optionally copies `TinyModel1Image.png` into the output dir for the card banner. |

How the eval subset is defined (same script, same seed → same rows) is documented in [`texts/eval-reproducibility.md`](texts/eval-reproducibility.md).

### Second reference dataset (Emotion)

Besides AG News ([`train_tinymodel1_agnews.py`](https://github.com/HyperlinksSpace/TinyModel/blob/main/scripts/train_tinymodel1_agnews.py)), this repo includes a **second** single-label task on the Hub **[`emotion`](https://huggingface.co/datasets/emotion)** (English short text, 6 classes: sadness, joy, love, anger, fear, surprise). It uses the **same** training code path; only dataset id, eval split, and label names are preset.

| Entry point | Dataset | Eval split (default) |
| ----------- | ------- | -------------------- |
| [`scripts/train_tinymodel1_agnews.py`](https://github.com/HyperlinksSpace/TinyModel/blob/main/scripts/train_tinymodel1_agnews.py) | `fancyzhx/ag_news` | `test` |
| [`scripts/train_tinymodel1_emotion.py`](https://github.com/HyperlinksSpace/TinyModel/blob/main/scripts/train_tinymodel1_emotion.py) | `emotion` | `validation` |
| [`scripts/train_tinymodel1_sst2.py`](https://github.com/HyperlinksSpace/TinyModel/blob/main/scripts/train_tinymodel1_sst2.py) | `glue` (`sst2`) | `validation` |

**Equivalent explicit CLI** (if you prefer not to use the wrapper):

```bash
python scripts/train_tinymodel1_classifier.py \
  --dataset emotion \
  --eval-split validation \
  --labels sadness,joy,love,anger,fear,surprise \
  --output-dir .tmp/TinyModel-emotion
```

**Instant smoke test** (small samples, ~1 minute on CPU; needs network to download `emotion` once):

```bash
python scripts/train_tinymodel1_emotion.py \
  --output-dir artifacts/emotion-smoke \
  --max-train-samples 200 \
  --max-eval-samples 100 \
  --epochs 1 \
  --batch-size 8 \
  --seed 42
```

Then check `artifacts/emotion-smoke/eval_report.json` — `reproducibility.dataset` should be `emotion` and `label_order` should list the six emotion names. For other Hub datasets, pass `--dataset`, splits, and optional `--labels` / `--text-column` to [`train_tinymodel1_classifier.py`](https://github.com/HyperlinksSpace/TinyModel/blob/main/scripts/train_tinymodel1_classifier.py) directly.

### Embeddings smoke test (routing / search-shaped)

[`scripts/embeddings_smoke_test.py`](https://github.com/HyperlinksSpace/TinyModel/blob/main/scripts/embeddings_smoke_test.py) runs [`TinyModelRuntime`](https://github.com/HyperlinksSpace/TinyModel/blob/main/scripts/tinymodel_runtime.py) on a few queries: **classification probabilities**, **pairwise similarity**, and **retrieval** over a toy candidate list (support/triage scenario).

**What these terms mean**

- **Classification probabilities** — Output of `TinyModelRuntime.classify(...)`: for each input text, the model returns a probability distribution across all labels (values sum to ~1.0). Use this for routing decisions and confidence-aware thresholds.
- **Pairwise similarity** — Output of `TinyModelRuntime.similarity(text_a, text_b)`: cosine similarity between two sentence embeddings (from the encoder). Higher values mean semantically closer text under this model.
- **Retrieval** — Output of `TinyModelRuntime.retrieve(query, candidates, top_k=...)`: ranks candidate texts by embedding similarity to a query and returns top matches with scores and indices.

**Instant test** (needs a checkpoint — train the tiny eval run first, or pass a Hub id):

```bash
python scripts/train_tinymodel1_classifier.py \
  --output-dir artifacts/eval-smoke --max-train-samples 120 --max-eval-samples 80 \
  --epochs 1 --batch-size 8 --seed 42
python scripts/embeddings_smoke_test.py --model artifacts/eval-smoke
# Or: python scripts/embeddings_smoke_test.py --model HyperlinksSpace/TinyModel1
```

### Pretrained encoder fine-tune (compare to scratch baseline)

[`scripts/finetune_pretrained_classifier.py`](https://github.com/HyperlinksSpace/TinyModel/blob/main/scripts/finetune_pretrained_classifier.py) fine-tunes **`AutoModelForSequenceClassification`** from `--base-model` (default `distilbert-base-uncased`) using the **same** splits and metrics as the scratch trainer. Use matching `--seed` and sample caps, then compare `eval_report.json` / `artifact.json` to a scratch run.

**Instant test** (downloads base weights once; CPU-friendly small run):

```bash
python scripts/finetune_pretrained_classifier.py \
  --output-dir artifacts/finetune-smoke \
  --base-model distilbert-base-uncased \
  --max-train-samples 400 --max-eval-samples 200 \
  --epochs 1 --batch-size 8 --seed 42
```

### Custom labels and data hygiene

For proprietary or weakly labeled data: use a short **label guide**, **versioned snapshots**, and **leakage-safe splits**. See [`texts/labeling-and-data-hygiene.md`](texts/labeling-and-data-hygiene.md).

### Current implementation status (what, why, how to run)

This section summarizes the currently implemented components and their practical purpose.

| Part | What it is for | How to launch | What to verify |
| ---- | ---- | ---- | ---- |
| **Scratch baseline training** (`scripts/train_tinymodel1_classifier.py`) | Build a small from-scratch text classifier baseline and export all model artifacts. | `python scripts/train_tinymodel1_classifier.py --output-dir artifacts/eval-smoke --max-train-samples 120 --max-eval-samples 80 --epochs 1 --batch-size 8 --seed 42` | `artifacts/eval-smoke/eval_report.json` exists and includes `accuracy`, `macro_f1`, `per_class_f1`, `confusion_matrix`. |
| **Second dataset path** (`scripts/train_tinymodel1_emotion.py`) | Prove the same pipeline works on another Hub dataset without forking core training code. | `python scripts/train_tinymodel1_emotion.py --output-dir artifacts/emotion-smoke --max-train-samples 200 --max-eval-samples 100 --epochs 1 --batch-size 8 --seed 42` | `reproducibility.dataset == "emotion"` and 6 labels in `label_order`. |
| **Embeddings/runtime smoke** (`scripts/embeddings_smoke_test.py`) | Validate product-shaped runtime behavior: classify, similarity, retrieval. | `python scripts/embeddings_smoke_test.py --model artifacts/eval-smoke` (or `--model HyperlinksSpace/TinyModel1`) | Script prints all 3 blocks and ends with `Embeddings smoke test completed.` |
| **Pretrained fine-tune path** (`scripts/finetune_pretrained_classifier.py`) | Compare a pretrained encoder baseline (DistilBERT/BERT-family) against scratch training using same eval reporting format. | `python scripts/finetune_pretrained_classifier.py --output-dir artifacts/finetune-smoke --base-model distilbert-base-uncased --max-train-samples 400 --max-eval-samples 200 --epochs 1 --batch-size 8 --seed 42` | `artifacts/finetune-smoke/eval_report.json` + `artifact.json` exist; compare metrics to scratch run on same caps/seed. |
| **Data hygiene guide** (`texts/labeling-and-data-hygiene.md`) | Lightweight rules for label quality, versioning, and leakage prevention when moving to custom/proprietary data. | Read the file and apply before collecting custom labels. | Label guide versioning and split hygiene rules are defined before annotation scale-up. |
| **Kaggle→HF training workflow hardening** (`.github/workflows/train-via-kaggle-to-hf.yml`) | Make CI training/publish flow robust: stable auth handling, unique kernel slugs, resilient status polling, and clearer diagnostics. | Trigger workflow from GitHub Actions with `version`, `namespace`, train hyperparameters. | Workflow reaches model publish step and uploads `{namespace}/TinyModel{version}`. |

## 2) Using the Hub model and Space

Load the published model by id (no local files required):

```bash
python -c "from transformers import pipeline; p=pipeline('text-classification', model='HyperlinksSpace/TinyModel1', tokenizer='HyperlinksSpace/TinyModel1'); print(p('Stocks rallied after central bank comments', top_k=None))"
```

Use the general-purpose runtime helpers (classification + embeddings + semantic search):

```python
from scripts.tinymodel_runtime import TinyModelRuntime

rt = TinyModelRuntime("HyperlinksSpace/TinyModel1")

# 1) Classification
print(rt.classify(["Oil prices fell after a demand forecast update."])[0])

# 2) Embeddings (shape: [batch, hidden_size])
emb = rt.embed(
    [
        "The team won the cup final in extra time.",
        "Central bank policy affected bond yields.",
    ]
)
print(emb.shape)

# 3) Pairwise semantic similarity
score = rt.similarity(
    "Stocks rose after inflation cooled.",
    "Markets rallied as price growth slowed.",
)
print("similarity:", round(score, 4))

# 4) Retrieval: nearest texts to a query
hits = rt.retrieve(
    "Chipmaker launches a new AI processor.",
    [
        "Parliament debated tax policy in the capital.",
        "Semiconductor company unveils next-gen accelerator.",
        "Team signs striker before the derby.",
    ],
    top_k=2,
)
for h in hits:
    print(h.index, round(h.score, 4), h.text)
```

### TinyModelRuntime function outputs

| Function | Return type | Output values |
| ---- | ---- | ---- |
| `classify(texts)` | `list[dict[str, float]]` | One dict per input text. Keys are label names from `model.config.id2label`; values are probabilities in `[0, 1]` that sum to ~1.0 for each text. |
| `embed(texts, normalize=True)` | `torch.Tensor` | Shape `[batch_size, hidden_size]` (default TinyModel hidden size is `128`). If `normalize=True`, each row is L2-normalized (vector norm ~1.0). |
| `similarity(text_a, text_b)` | `float` | Cosine similarity between the two embeddings. Typical range is `[-1, 1]`: higher means more semantically similar under this model. |
| `retrieve(query, candidates, top_k=3)` | `list[RetrievalHit]` | Ranked top matches. Each item has: `index` (position in `candidates`), `text` (candidate string), `score` (cosine similarity; higher is closer). Length is `min(top_k, len(candidates))`. |

Or open the demo: [direct app](https://hyperlinksspace-tinymodel1space.hf.space) · [on the Hub](https://huggingface.co/spaces/HyperlinksSpace/TinyModel1Space).

Quick checks:

- Space loads; inference returns labels and scores; no errors in Space logs.

## 3) GitHub Actions workflows

Workflow definitions live under [`.github/workflows/`](https://github.com/HyperlinksSpace/TinyModel/tree/main/.github/workflows). Trigger them from **Actions →** select the workflow → **Run workflow**. Runners use **`ubuntu-latest`** unless you change the workflow.

### Repository secrets (Settings → Secrets and variables → Actions)

Configure these once per repository (or organization). They are **not** committed to git.

| Secret | Used by | Purpose |
| ------ | ------- | ------- |
| **`HF_TOKEN`** | Workflows below | Hugging Face [access token](https://huggingface.co/settings/tokens) with **write** permission to create/update models and Spaces in the target namespace. |
| **`KAGGLE_USERNAME`** | [`train-via-kaggle-to-hf.yml`](https://github.com/HyperlinksSpace/TinyModel/blob/main/.github/workflows/train-via-kaggle-to-hf.yml) only | Your Kaggle username (same value as in Kaggle **Account** → API). |
| **`KAGGLE_KEY`** | [`train-via-kaggle-to-hf.yml`](https://github.com/HyperlinksSpace/TinyModel/blob/main/.github/workflows/train-via-kaggle-to-hf.yml) only | Kaggle API key from **Account** → **Create New API Token**. |

No other GitHub secrets are read by these workflows. Internal step outputs (`GITHUB_ENV`) such as `KAGGLE_OWNER` / `KAGGLE_KERNEL_SLUG` are set automatically during the Kaggle run.

### Core flows (validated on the GitHub Actions free tier)

| Workflow | File |
| -------- | ---- |
| **Deploy versioned Space to Hugging Face** | [`deploy-hf-space-versioned.yml`](https://github.com/HyperlinksSpace/TinyModel/blob/main/.github/workflows/deploy-hf-space-versioned.yml) |
| **Train on Hugging Face Jobs and publish versioned model** | [`train-hf-job-versioned.yml`](https://github.com/HyperlinksSpace/TinyModel/blob/main/.github/workflows/train-hf-job-versioned.yml) |

- **[`deploy-hf-space-versioned.yml`](https://github.com/HyperlinksSpace/TinyModel/blob/main/.github/workflows/deploy-hf-space-versioned.yml)** — Builds the Gradio Space with `scripts/build_space_artifact.py` and uploads **`{namespace}/TinyModel{version}Space`**.  
  - **Secrets:** `HF_TOKEN`.  
  - **Workflow inputs:** `version`, `namespace`, `model_id` (for example `HyperlinksSpace/TinyModel1`).

- **[`train-hf-job-versioned.yml`](https://github.com/HyperlinksSpace/TinyModel/blob/main/.github/workflows/train-hf-job-versioned.yml)** — Submits training on **Hugging Face Jobs**, then publishes **`{namespace}/TinyModel{version}`**.  
  - **Secrets:** `HF_TOKEN` (also passed into the remote job so it can run `publish_hf_artifact.py`).  
  - **Workflow inputs:** `version`, `namespace`, optional `commit_sha` (empty = current workflow SHA), `flavor`, `timeout`, `max_train_samples`, `max_eval_samples`, `epochs`, `batch_size`, `learning_rate`.  
  - If Hugging Face returns **402 Payment Required** for Jobs, add billing/credits on your HF account or train locally and publish with `scripts/publish_hf_artifact.py` (see `texts/HUGGING_FACE_DEPLOYMENT_INTERNAL.md`).

### Optional: train via Kaggle

| Workflow | File |
| -------- | ---- |
| **Train via Kaggle and publish to Hugging Face** | [`train-via-kaggle-to-hf.yml`](https://github.com/HyperlinksSpace/TinyModel/blob/main/.github/workflows/train-via-kaggle-to-hf.yml) |

- **[`train-via-kaggle-to-hf.yml`](https://github.com/HyperlinksSpace/TinyModel/blob/main/.github/workflows/train-via-kaggle-to-hf.yml)** — Creates a Kaggle kernel run, trains, downloads outputs, and pushes **`{namespace}/TinyModel{version}`** to the Hub.  
  - **Secrets:** `KAGGLE_USERNAME`, `KAGGLE_KEY`, and **`HF_TOKEN`** (for upload to Hugging Face).  
  - **Workflow inputs:** `version`, `namespace`, `max_train_samples`, `max_eval_samples`, `epochs`, `batch_size`, `learning_rate`.  
  - **External quota:** Kaggle GPU/CPU weekly limits and any **Kaggle compute credits** your account uses; not covered by GitHub Actions alone.

## 4) Further development

Illustrative directions for evolving the TinyModel line (pick what matches your product goals):

- **Accuracy and capacity** — Train on more AG News samples or epochs; adjust the tiny BERT config (depth, width, sequence length); add LR schedules, warmup, or regularization suited to your budget.
- **Domains and label sets** — Fine-tune on proprietary or niche corpora; replace the four AG News classes with your own taxonomy and a labeled dataset.
- **Shipping inference** — Document ONNX or quantized exports for edge and serverless; add batch-inference examples; optionally wire a Hugging Face Inference Endpoint for a stable HTTP API.
- **Space and API UX** — Batch inputs, per-class thresholds, richer examples, or client snippets (Python and JavaScript) for integrators.
- **Evaluation discipline** — Fixed test split, confusion matrix, calibration, and versioned eval reports alongside `artifact.json`.
- **Repository hygiene** — Lightweight CI (lint, script smoke tests) that never pulls large weights; optional Hub Collections or docs that link model, Space, and release notes.

Nothing here is committed on a fixed timeline; treat it as a backlog of sensible next steps for a small text understanding stack.
