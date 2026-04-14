<div align="center">

# TinyModel

### Tiny, deployable text classification baseline for rapid product iteration

[![Model](https://img.shields.io/badge/Hugging%20Face-TinyModel1-yellow)](https://huggingface.co/HyperlinksSpace/TinyModel1)
[![Space](https://img.shields.io/badge/Hugging%20Face-TinyModel1Space-orange)](https://huggingface.co/spaces/HyperlinksSpace/TinyModel1Space)
[![Status](https://img.shields.io/badge/Status-Active%20Development-blue)](https://github.com/HyperlinksSpace/TinyModel)

</div>

`TinyModel1` is a practical starter model line for text classification.
End users consume deployed Hugging Face model and Space endpoints. Maintainer deployment policy lives in `texts/HUGGING_FACE_DEPLOYMENT_INTERNAL.md`.

Repository: [HyperlinksSpace/TinyModel](https://github.com/HyperlinksSpace/TinyModel)

**TinyModel1 on Hugging Face**

- Model: [HyperlinksSpace/TinyModel1](https://huggingface.co/HyperlinksSpace/TinyModel1)
- Space (Hub): [HyperlinksSpace/TinyModel1Space](https://huggingface.co/spaces/HyperlinksSpace/TinyModel1Space)
- Space (app): [hyperlinksspace-tinymodel1space.hf.space](https://hyperlinksspace-tinymodel1space.hf.space)

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

Or open the demo: [TinyModel1Space (app)](https://hyperlinksspace-tinymodel1space.hf.space).

Quick checks:

- Space loads; inference returns labels and scores; no errors in Space logs.

## 3) GitHub Actions workflows

Workflow definitions live under [`.github/workflows/`](https://github.com/HyperlinksSpace/TinyModel/tree/main/.github/workflows). Trigger them from **Actions →** select the workflow → **Run workflow**. Runners use **`ubuntu-latest`** unless you change the workflow.

### Repository secrets (Settings → Secrets and variables → Actions)

Configure these once per repository (or organization). They are **not** committed to git.

| Secret | Used by | Purpose |
| ------ | ------- | ------- |
| **`HF_TOKEN`** | All three workflows below | Hugging Face [access token](https://huggingface.co/settings/tokens) with **write** permission to create/update models and Spaces in the target namespace. |
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
