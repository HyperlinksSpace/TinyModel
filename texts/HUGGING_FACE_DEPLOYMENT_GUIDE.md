# Deploying TinyModel to Hugging Face (Hub + Spaces)

This guide explains how to deploy the **latest version** of TinyModel to the Hugging Face **Hub** (model) and **Spaces** (Gradio app) using the repository **GitHub Actions workflows**, and how to access the full functionality after deployment.

## What you deploy (two artifacts)

- **Model repo**: `"{namespace}/TinyModel{version}"`  
  Published by **one** of the training workflows:
  - `train-via-kaggle-to-hf.yml` (Kaggle kernel → publish)
  - `train-hf-job-versioned.yml` (Hugging Face Jobs → publish)
- **Space repo**: `"{namespace}/TinyModel{version}Space"`  
  Published by the workflow `deploy-hf-space-versioned.yml`. The Space bundles the in-repo Gradio app (“Universal Brain chat”) and points it at your model via `--encoder {model_id}`.

## One-time setup

### 1) Create a Hugging Face token

Create a token at Hugging Face settings → tokens, with **write** permissions (it must be able to create/update model and space repos in your namespace).

### 2) Add repo secret in GitHub

In your GitHub repo:

- Settings → Secrets and variables → Actions → New repository secret
- Name: `HF_TOKEN`
- Value: the Hugging Face token created above

That is the only required secret for the two deployment workflows.

## Deploy the latest model to the Hub (workflow options)

You can publish `"{namespace}/TinyModel{version}"` in two supported ways. Pick the one you already use operationally.

### Option A (what you used): Train via Kaggle → publish to Hugging Face

Workflow: `.github/workflows/train-via-kaggle-to-hf.yml`  
Action: GitHub → **Actions** → “Train via Kaggle and publish to Hugging Face” → **Run workflow**

#### Required inputs

- **`version`**: integer (e.g. `1`, `2`, `3`) → publishes `TinyModel{version}`.
- **`namespace`**: HF user/org to publish into.
- **Training knobs**: `max_train_samples`, `max_eval_samples`, `epochs`, `batch_size`, `learning_rate`.

#### Required GitHub secrets

- **`KAGGLE_USERNAME`** and **`KAGGLE_KEY`** (to run the Kaggle kernel)
- **`HF_TOKEN`** (to publish the resulting artifact to the Hub)

#### What the workflow does (high level)

- Creates/starts a Kaggle kernel run with the training script and your chosen hyperparameters.
- Waits for completion, downloads the artifact outputs, then uploads them to Hugging Face as:
  - `"{namespace}/TinyModel{version}"` (repo type: **model**)

Use this path if you already rely on Kaggle quotas/GPUs or want the training to run fully in Kaggle.

### Option B: Train on Hugging Face Jobs → publish to the Hub

Workflow: `.github/workflows/train-hf-job-versioned.yml`  
Action: GitHub → **Actions** → “Train on Hugging Face Jobs and publish versioned model” → **Run workflow**

### Required inputs (what they mean)

- **`version`**: integer (e.g. `1`, `2`, `3`). This becomes the repo name suffix: `TinyModel{version}`.
- **`namespace`**: HF user or org (e.g. `HyperlinksSpace`, `MyOrg`).
- **`commit_sha`** (optional): pin training to a specific commit. If empty, it trains from the workflow run’s commit.
- **`flavor`**: HF Jobs hardware (e.g. `a10g-small`, `l40sx1`).
- **`timeout`**: HF Jobs timeout (e.g. `2h`, `6h`).
- **Training knobs**: `max_train_samples`, `max_eval_samples`, `epochs`, `batch_size`, `learning_rate`.

### What the workflow does

- Submits a Hugging Face **Job** that:
  - clones this GitHub repo at `commit_sha`
  - runs `scripts/train_tinymodel1_agnews.py` writing outputs under `.tmp/TinyModel{version}`
  - publishes the artifact to the Hub as a **model repo** `"{namespace}/TinyModel{version}"` via `scripts/publish_hf_artifact.py`
- Monitors the job until it completes (and prints logs on failure).

### If HF Jobs returns “402 Payment Required”

That means the namespace does not have Jobs credits. The workflow already prints a fallback. The manual fallback is:

```bash
python scripts/train_tinymodel1_agnews.py --output-dir ".tmp/TinyModel{version}"
python scripts/publish_hf_artifact.py --namespace "{namespace}" --name "TinyModel{version}" --repo-type model --source-dir ".tmp/TinyModel{version}"
```

## Deploy the matching Space (workflow)

Workflow: `.github/workflows/deploy-hf-space-versioned.yml`  
Action: GitHub → **Actions** → “Deploy versioned space artifact to Hugging Face” → **Run workflow**

### Required inputs

- **`version`**: the same integer you deployed for the model.
- **`namespace`**: same HF user/org.
- **`model_id`**: the **Hub model id** the Space should use as its encoder, e.g. `"{namespace}/TinyModel{version}"`.

### What the workflow does

- Runs fast unit tests (stdlib-only) first.
- Builds a Space folder with `scripts/build_space_artifact.py` into:
  - `.tmp/TinyModel{version}Space`
- Publishes that folder to Hugging Face as a **Space repo**:
  - `"{namespace}/TinyModel{version}Space"`

## How to use the deployed Hub model

### Transformers (local / server)

```python
from transformers import pipeline

p = pipeline(
    "text-classification",
    model="{namespace}/TinyModel{version}",
    tokenizer="{namespace}/TinyModel{version}",
)
print(p("Stocks rallied after central bank comments", top_k=None))
```

### Runtime helper in this repo

If you want the “whole product-like behavior” locally (classification + similarity + retrieval helpers), use `TinyModelRuntime`:

```python
from scripts.tinymodel_runtime import TinyModelRuntime

rt = TinyModelRuntime("{namespace}/TinyModel{version}")
print(rt.classify("Stocks rallied after central bank comments"))
```

## How to use the deployed Space (whole functionality)

### 1) UI (recommended)

Open the Space on the Hub: `https://huggingface.co/spaces/{namespace}/TinyModel{version}Space`

The Space runs **Universal Brain chat**:

- **Classifier context**: uses `--encoder {model_id}` to infer topics/intent and optionally prints probability tables.
- **NL routing**: routes between tasks like summarization, FAQ/RAG retrieval, memory actions, and normal chat.
- **Session controls (no slash needed)**: you can type plain phrases to change behavior. Examples:
  - **Scope / sessions**: “What is my current scope?”, “Start a new private session”, “Switch to scope my-key”
  - **Answer style**: “Be brief”, “More detail please”, “Use bullet points”, “Reset reply style”
  - **FAQ grounding**: “Strict FAQ”, “Balanced FAQ”, “Turn off FAQ context”
  - **Ops / debug**: “Show the brain trace”, “Turn off smart routing”
  - **Memory**: “Export my memories”, “Delete all my memories for this chat”

### 2) API (Gradio endpoints)

On the Space page, click **Use via API** to see the available endpoints and their descriptions.

You can call the Space via HTTP (or the official Gradio client) using the endpoint shown there. The primary endpoint is exposed as **`chat`**.

## Space configuration knobs (optional)

The generated Space `app.py` supports:

- **`HF_TOKEN`** (Space secret): recommended to avoid rate limits / gated downloads during model pulls.
- **`HORIZON2_MODEL`** (Space variable): optionally override the **generative** model id used for replies.

## Troubleshooting: `deploy-hf-space-versioned` failed (exit code 1)

1. **Ignore the Node.js 20 “deprecated” annotation by itself.** GitHub prints that warning for `actions/checkout` / `actions/setup-python`; it does **not** explain an exit-code failure unless the job actually fails inside those steps.

2. **Open the failed step** in the Actions log (expand **deploy-space** → each step). The first step that turns red is the real error.

   | Step | Typical failure |
   | ---- | ---------------- |
   | **Unit tests** | A test failed—scroll up for `FAILED` / `ERROR`. Run locally: `python -m unittest discover -s tests -p "test_*.py" -v` |
   | **Verify Hugging Face token** | Missing `HF_TOKEN` secret, expired token, or wrong scopes |
   | **Publish …** | Namespace mismatch (token user/org vs `--namespace`), no write access to org repos, or Hub API error—read the Python traceback |

3. **`HF_TOKEN` on forks:** If you run the workflow on a **fork**, GitHub does **not** use upstream secrets. Add **`HF_TOKEN`** (and any others) under **your fork** → Settings → Secrets and variables → Actions.

4. **Org namespaces:** Publishing to an organization repo requires a token whose account has **write** access to that org on Hugging Face (role/membership), not only a personal token.

