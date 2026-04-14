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
   - `.github/workflows/deploy-hf-model-versioned.yml`
   - `.github/workflows/deploy-hf-space-versioned.yml`
4. Verify repo visibility and naming on Hugging Face (`TinyModel1`, `TinyModel1Space`, etc.).

## Recommended deployment architecture

For production, do not keep large trained weights in Git history.

- GitHub is source-of-truth for code, training config, and CI logic.
- Hugging Face is source-of-truth for released model/dataset/Space artifacts.
- Release by version (`vX.Y.Z`) and publish model metadata with each release.

## Standard release flow (best practice)

1. Merge training code/config changes to `main` (no large weight files in repo).
2. Trigger `deploy-hf-model-versioned.yml` from GitHub Actions:
   - set `source_model_id` to a model already trained on HF infra or uploaded from local training
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

1. Keep Space template generator code in `scripts/build_space_artifact.py`.
2. Space artifact is generated per release into temporary workflow output.
3. Configure the Space to load the released model revision (not an unversioned draft).

### Test flow on Hugging Face

1. Deploy/update the Space from CI after model publish succeeds.
2. Run automated Space smoke tests against public Space endpoints:
   - app loads successfully
   - inference request returns HTTP 200
   - output format matches expected schema
   - p95 latency is within release threshold
3. Run semantic checks on fixed examples (golden set):
   - at least one sample for each target class
   - confidence scores are present and numeric
4. Mark release as failed if Space checks fail; do not promote release tag.

### Minimum pass criteria

- Space is reachable and healthy
- Prediction path works end-to-end
- No runtime errors in Space logs
- Latency and response schema satisfy policy thresholds

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

1. Check GitHub Actions logs for `deploy-hf-model-versioned.yml` and `deploy-hf-space-versioned.yml`.
2. Validate token scope and expiration for `HF_TOKEN`.
3. Confirm workflow inputs (`namespace`, `version`, `source_model_id`) are correct.
4. Re-run workflow after fix.
5. If HF service-level issue exists, communicate status and ETA to users.

