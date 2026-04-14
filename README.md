# TinyModel

This repository is the single source code and release monorepo for TinyModels.
It publishes multiple Hugging Face artifacts (models/datasets/spaces) from one
GitHub repository, similar to projects that keep one codebase and many external Huggling Face repos.

## Repository layout

- `artifacts/` local folders that represent deployable HF artifacts
- `hf-artifacts.json` deploy manifest (artifact name, type, source folder)
- `scripts/publish_hf_artifact.py` uploader script
- `.github/workflows/deploy-hf-artifacts.yml` CI deploy workflow

## Configure once

1. Create a Hugging Face token with write access.
2. Add `HF_TOKEN` in GitHub repository secrets.
3. Edit `hf-artifacts.json`:
   - set `namespace` to your HF username or org
   - add/remove artifacts as needed
4. Put each artifact payload in its configured `source_dir`.

## Deploy flow

- Push changes to `main`.
- Workflow triggers when `artifacts/**` or deploy config changes.
- For each configured artifact, workflow:
  - ensures the target HF repo exists (`exist_ok=True`)
  - uploads the folder to that repo

## Build TinyModel1 artifact

Generate a useful TinyModel1 classifier using the public `ag_news` dataset:

```bash
python scripts/train_tinymodel1_agnews.py
```

This writes deployable files to `artifacts/TinyModel1/`:
- `model.safetensors`
- `config.json`
- tokenizer files
- model card (`README.md`)
- `artifact.json` with quick metrics

Then deploy by pushing to `main` (or triggering workflow manually).

