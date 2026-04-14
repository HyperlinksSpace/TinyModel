<div align="center">

# TinyModel

### Tiny, deployable text classification baseline for rapid product iteration

[![GitHub](https://img.shields.io/badge/GitHub-HyperlinksSpace%2FTinyModel-181717)](https://github.com/HyperlinksSpace/TinyModel)
[![Model](https://img.shields.io/badge/Hugging%20Face-TinyModel1-yellow)](https://huggingface.co/)
[![Status](https://img.shields.io/badge/Status-Active%20Development-blue)](https://github.com/HyperlinksSpace/TinyModel)

</div>

`TinyModel1` is a practical starter model line for text classification.
End users consume deployed Hugging Face model and Space endpoints. Maintainer deployment policy lives in `texts/HUGGING_FACE_DEPLOYMENT_INTERNAL.md`.

Repository: [HyperlinksSpace/TinyModel](https://github.com/HyperlinksSpace/TinyModel)

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

Model release workflow promotes an existing HF model repo into a versioned artifact name.

- Workflow: `Deploy versioned model artifact to Hugging Face`
- Required inputs:
  - `version` (for example `1`, `2`)
  - `namespace` (for example `HyperlinksSpace`)
  - `source_model_id` (for example `HyperlinksSpace/TinyModel1-staging`)

Naming result:

- `version=1` -> `TinyModel1`
- `version=2` -> `TinyModel2`

If workflow returns `401 Unauthorized` or repository not found:

- Ensure `HF_TOKEN` secret is set in GitHub Actions
- Ensure token has access to `source_model_id`
- Ensure `source_model_id` exists and is spelled correctly

## 3) Testing in Hugging Face Space

Space release workflow creates a versioned Space and points it to the matching model version.

- Workflow: `Deploy versioned space artifact to Hugging Face`
- Required inputs:
  - `version`
  - `namespace`

Naming result:

- `version=1` -> `TinyModel1Space`
- `version=2` -> `TinyModel2Space`

Minimum validation after publish:

- Space loads successfully
- Inference returns HTTP 200
- Output contains labels and confidence scores
- No runtime errors in Space logs

