<div align="center">

# TinyModel

### Tiny, deployable text classification baseline for rapid product iteration

[![GitHub](https://img.shields.io/badge/GitHub-HyperlinksSpace%2FTinyModel-181717)](https://github.com/HyperlinksSpace/TinyModel)
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

## 1) Local Testing

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

## 2) Exporting From Hugging Face

Model artifact creation is done by Hugging Face Jobs workflow.

- Workflow: `Train on Hugging Face Jobs and publish versioned model`
- Required inputs:
  - `version` (for example `1`, `2`)
  - `namespace` (for example `HyperlinksSpace`)
  - `commit_sha` (optional pinned commit)
  - training/eval params (`max_train_samples`, `max_eval_samples`, `epochs`, etc.)

Naming result:

- `version=1` -> `TinyModel1`
- `version=2` -> `TinyModel2`

If workflow returns `401 Unauthorized` or repository not found:

- Ensure `HF_TOKEN` secret is set in GitHub Actions
- Ensure token has write access to target namespace/model repo
- Ensure target namespace exists and is spelled correctly

If workflow returns `402 Payment Required`:

- Hugging Face Jobs credits are insufficient for the selected namespace
- Add credits and rerun:
  - Billing: [https://huggingface.co/settings/billing](https://huggingface.co/settings/billing)
  - Tokens: [https://huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
  - Jobs docs: [https://huggingface.co/docs/huggingface_hub/en/guides/jobs](https://huggingface.co/docs/huggingface_hub/en/guides/jobs)
- Fallback immediately with local training + publish:
  - `python scripts/train_tinymodel1_agnews.py --output-dir .tmp/TinyModel1`
  - `python scripts/publish_hf_artifact.py --namespace HyperlinksSpace --name TinyModel1 --repo-type model --source-dir .tmp/TinyModel1`

This workflow:

- launches an HF Job with selected `flavor` and `timeout`
- checks out the exact `commit_sha` (or current SHA)
- trains and publishes directly to `TinyModel{version}`

## 3) Testing in Hugging Face Space

Space release workflow creates a versioned Space and points it to the matching model version.

- Workflow: `Deploy versioned space artifact to Hugging Face`
- Required inputs:
  - `version`
  - `namespace`
  - `model_id` (for example `HyperlinksSpace/TinyModel1`)

Naming result:

- `version=1` -> `TinyModel1Space`
- `version=2` -> `TinyModel2Space`

Minimum validation after publish:

- Space loads successfully (for example [TinyModel1Space on the Hub](https://huggingface.co/spaces/HyperlinksSpace/TinyModel1Space) or the [live app](https://hyperlinksspace-tinymodel1space.hf.space))
- Inference returns HTTP 200
- Output contains labels and confidence scores
- No runtime errors in Space logs

