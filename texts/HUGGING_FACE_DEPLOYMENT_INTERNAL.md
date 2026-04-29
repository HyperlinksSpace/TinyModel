# Internal Deployment Instruction (Hugging Face)

This document is for maintainers of `HyperlinksSpace/TinyModel`.
It is not intended for end users.

## Goal

Keep `TinyModel1` and related artifacts continuously deployed on Hugging Face so users can consume the product directly without manual setup.

## Ownership

- Deployment owner: TinyModel maintainers
- End users: consume model/Space endpoints only

## One-time setup checklist

1. Create a Hugging Face write token for the deployment account/org.
2. Add `HF_TOKEN` in GitHub repository secrets.
3. Ensure both workflows are enabled:
   - `.github/workflows/train-hf-job-versioned.yml`
   - `.github/workflows/deploy-hf-space-versioned.yml`
4. Verify repo visibility and naming on Hugging Face (`TinyModel1`, `TinyModel1Space`, etc.).

## Recommended deployment architecture

For production, do not keep large trained weights in Git history.

- GitHub is source-of-truth for code, training config, and CI logic.
- Hugging Face is source-of-truth for released model/dataset/Space artifacts.
- Release by version (`vX.Y.Z`) and publish model metadata with each release.

## Standard release flow (best practice)

1. Merge training code/config changes to `main` (no large weight files in repo).
2. Trigger `train-hf-job-versioned.yml` from GitHub Actions.
3. Publish model artifact as `TinyModel{version}`.
4. Trigger `deploy-hf-space-versioned.yml` for the same version.
5. Publish Space artifact as `TinyModel{version}Space`.
6. Run evaluation and smoke tests on Hugging Face infrastructure.
7. If gates pass, GitHub CI records release metadata and creates Git tag/release notes referencing:
   - dataset version
   - training commit SHA
   - metrics snapshot
   - Hugging Face model revision
8. Smoke-test public endpoints (model + Space).

## Hugging Face Space testing (required)

Space tests are part of release gating and must run after model publish.

### Space artifact setup

1. `scripts/build_space_artifact.py` bundles **Universal Brain chat** (`universal_brain_chat.py` + `horizon2_core`, `horizon3_store`, `rag_faq_smoke`, `tinymodel_runtime`, FAQ corpus) and a root `app.py` that listens on `0.0.0.0` and passes `--encoder` = released classifier id.
2. Space artifact is generated per release into temporary workflow output.
3. Configure the workflow `model_id` to the released classifier revision on the Hub.

### Test flow on Hugging Face

1. Deploy/update the Space from CI after model publish succeeds.
2. Run automated Space smoke tests against public Space endpoints:
   - app loads successfully (Gradio UI)
   - at least one chat interaction completes (HTTP 200 from API)
   - optional: `/status` or a routed tool path if automated UI tests exist
   - p95 latency is within release threshold
3. Golden checks can still target the **classifier** via natural-language “classify …” or `/classify` and expect label scores.
4. Mark release as failed if Space checks fail; do not promote release tag.

### Minimum pass criteria

- Space is reachable and healthy
- Chat / routing path works end-to-end (no startup tracebacks)
- No runtime errors in Space logs
- Latency and response sanity satisfy policy thresholds

## Current repo mode (transition state)

Historical approach mirrored artifacts under `artifacts/` and pushed them to Hugging Face.
Current approach is release-time generation/publish and should be used for all new releases.

Target state:

- keep only lightweight sample assets in Git
- train model weights on HF infra or local machine after git clone
- publish to Hugging Face without committing weight binaries to GitHub

## Operational quality gates

Before merging to `main`, verify:

- Training script runs successfully
- `artifact.json` metrics are updated
- Model card is coherent and user-facing
- Inference sanity checks pass on representative examples
- Space app loads and predicts without runtime errors

## Production policy

- Do not ask users to deploy manually.
- Main branch should always represent a releasable code state.
- Do not store large production weights in Git history.
- Breaking changes to artifact schema require migration notes in PR description.

## Incident response

If deployment fails:

1. Check GitHub Actions logs for `train-hf-job-versioned.yml` and `deploy-hf-space-versioned.yml`.
2. Validate token scope and expiration for `HF_TOKEN`.
3. Confirm workflow inputs (`namespace`, `version`, `commit_sha`) are correct.
4. Re-run workflow after fix.
5. If HF service-level issue exists, communicate status and ETA to users.

### Fallback for 402 Payment Required (HF Jobs credits)

If HF Jobs returns 402:

1. Add credits:
   - https://huggingface.co/settings/billing
2. Verify token:
   - https://huggingface.co/settings/tokens
3. Jobs reference:
   - https://huggingface.co/docs/huggingface_hub/en/guides/jobs
4. Continue release via local fallback:
   - `python scripts/train_tinymodel1_agnews.py --output-dir .tmp/TinyModel{version}`
   - `python scripts/publish_hf_artifact.py --namespace <namespace> --name TinyModel{version} --repo-type model --source-dir .tmp/TinyModel{version}`
   - then deploy Space with matching `model_id`.

