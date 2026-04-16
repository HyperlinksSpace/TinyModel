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

**Model card (README)** — On the Hub, the model card is the **`README.md`** file at the root of the model repo (same URL as the model). In this repository, the template is implemented by `write_model_card()` in [`scripts/train_tinymodel1_agnews.py`](https://github.com/HyperlinksSpace/TinyModel/blob/main/scripts/train_tinymodel1_agnews.py); training writes `README.md` and [`artifact.json`](https://github.com/HyperlinksSpace/TinyModel/blob/main/scripts/train_tinymodel1_agnews.py) next to the weights. We do **not** run CI that downloads full model weights into the repo or runner caches for republish; update the card by retraining and publishing, or edit `README.md` on the Hub and keep weights unchanged.

## 1) Local testing

Train locally after cloning the repo:

```bash
python scripts/train_tinymodel1_agnews.py --output-dir .tmp/TinyModel-local
```

Quick local inference sanity check:

```bash
python -c "from transformers import pipeline; p=pipeline('text-classification', model='.tmp/TinyModel-local', tokenizer='.tmp/TinyModel-local'); print(p('Stocks rallied after central bank comments', top_k=None))"
```

Expected local output folder:

- `.tmp/TinyModel-local/model.safetensors`
- `.tmp/TinyModel-local/config.json`
- `.tmp/TinyModel-local/tokenizer.json`
- `.tmp/TinyModel-local/README.md`
- `.tmp/TinyModel-local/artifact.json`

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
