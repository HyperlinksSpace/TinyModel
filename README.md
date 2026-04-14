<div align="center">

# TinyModel

### Tiny, deployable text classification baseline for rapid product iteration

[![GitHub](https://img.shields.io/badge/GitHub-HyperlinksSpace%2FTinyModel-181717)](https://github.com/HyperlinksSpace/TinyModel)
[![Model](https://img.shields.io/badge/Hugging%20Face-TinyModel1-yellow)](https://huggingface.co/)
[![Status](https://img.shields.io/badge/Status-Active%20Development-blue)](https://github.com/HyperlinksSpace/TinyModel)

</div>

`TinyModel1` is a practical starter model line focused on one thing: fast iteration from training to deployment.
This repo keeps source code in GitHub and publishes release artifacts directly to Hugging Face from workflows.
Users should consume an already deployed product on Hugging Face. Deployment is handled by the maintainers.

Repository: [HyperlinksSpace/TinyModel](https://github.com/HyperlinksSpace/TinyModel)

## Why This Project

- Build a useful baseline quickly (`World`, `Sports`, `Business`, `Sci/Tech` classification)
- Keep source code versioned in GitHub and release artifacts versioned in Hugging Face
- Support a clean path to add dataset and Space artifacts in the same monorepo
- Enable market-oriented iteration loops: train -> deploy -> demo -> improve

## Current Artifacts

- `TinyModel1` (`model`) trained on `ag_news`
- Versioned model and Space deploy workflows via GitHub Actions
- Metadata and model card auto-generated after training

## For Users

- Use the deployed Hugging Face model/Space directly.
- No local training or deployment steps are required.
- Report prediction quality issues with concrete examples so the maintainers can retrain and redeploy.

## For Maintainers

- Deployment procedure is documented in `texts/HUGGING_FACE_DEPLOYMENT_INTERNAL.md`.
- Keep `main` always deployable and publicly consumable.

## Repository Layout

- `artifacts/` deployable Hugging Face payload folders
- `artifacts/TinyModel1/` local training output (dev/prototype)
- `scripts/train_tinymodel1_agnews.py` training/export script
- `scripts/build_space_artifact.py` Space artifact generator
- `scripts/publish_hf_artifact.py` artifact publisher
- `.github/workflows/deploy-hf-model-versioned.yml` model release workflow
- `.github/workflows/deploy-hf-space-versioned.yml` Space release workflow

## Quick Start

### 1) Train TinyModel1

```bash
python scripts/train_tinymodel1_agnews.py
```

Recommended stronger run:

```bash
python scripts/train_tinymodel1_agnews.py --max-train-samples 12000 --max-eval-samples 2000 --epochs 4 --batch-size 16 --learning-rate 1e-4
```

### 2) Inspect Output

Local training writes to `artifacts/TinyModel1/`:

- `model.safetensors`
- `config.json`
- `tokenizer.json`, `tokenizer_config.json`, `vocab.txt`
- `README.md` (model card)
- `artifact.json` (quick metrics and metadata)

Note: these local files are for development. Official releases are published to Hugging Face by workflows and do not require committing weight files.

## Deploy to Hugging Face (Maintainers)

### One-time setup

1. Create a Hugging Face token with write access.
2. Add `HF_TOKEN` in GitHub repository secrets.
3. Choose target `namespace` when running deployment workflows.

### Deploy flow

1. Run `Deploy versioned model artifact to Hugging Face` workflow:
   - choose `version` (1, 2, ...)
   - set `source_model_id` to a Hugging Face model repo that is already trained
2. Run `Deploy versioned space artifact to Hugging Face` workflow:
   - choose the same `version`
   - Space is published as `TinyModel{version}Space` and points to `TinyModel{version}`
3. Smoke-test both public endpoints.

Two supported maintainer paths:

- **HF training path:** train with Hugging Face jobs/infra, then set `source_model_id` to that trained model repo.
- **Local training path:** train locally after clone (`scripts/train_tinymodel1_agnews.py`), upload to a staging HF repo, then set `source_model_id` to that staging repo.

Local training + staging publish example:

```bash
python scripts/train_tinymodel1_agnews.py --output-dir .tmp/TinyModel-staging
python scripts/publish_hf_artifact.py --namespace HyperlinksSpace --name TinyModel1-staging --repo-type model --source-dir .tmp/TinyModel-staging
```

## Test in a Hugging Face Space (Maintainers)

Use the versioned Space workflow to create/update a public test surface with:

- single text input prediction
- confidence display
- business-friendly demo examples

This is the fastest path to gather user feedback and improve model-market fit.

## Configuration Reference

Model workflow examples:

- `version=1` -> `TinyModel1`
- `version=2` -> `TinyModel2`
- `source_model_id=HyperlinksSpace/TinyModel1-staging`

## Roadmap

- Add `TinyModel1-demo` Space artifact (Gradio)
- Add `TinyModel1-data` dataset artifact with curated production-like samples
- Introduce evaluation script and benchmark history
- Add domain-specialized variants (`TinyModel1-finance`, `TinyModel1-support`, etc.)

## Notes

- `TinyModel1` is a compact baseline and should be further fine-tuned for production domains.
- For commercial launch quality, prioritize data quality, eval coverage, and latency/error monitoring.

