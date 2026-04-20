# Phase 1 runbook: stabilize and compare

This runbook documents the implemented Phase 1 flow from `texts/further-development-plan.md`.

## What is implemented

1. **Baseline comparison matrix**
   - Implemented by `scripts/phase1_compare.py`.
   - Runs scratch (`train_tinymodel1_classifier.py`) and pretrained (`finetune_pretrained_classifier.py`) with identical:
     - dataset split selection,
     - sample caps,
     - seed.
   - Produces one table with:
     - `accuracy`,
     - `macro_f1`,
     - per-class F1 columns.
   - Supports at least:
     - `ag_news` (`fancyzhx/ag_news`),
     - `emotion`.

2. **Run profile presets**
   - `smoke`: `max_train_samples=120`, `max_eval_samples=80`, `epochs=1`, `batch_size=8`
   - `dev`: `max_train_samples=1000`, `max_eval_samples=300`, `epochs=2`, `batch_size=16`
   - `full`: `max_train_samples=6000`, `max_eval_samples=1200`, `epochs=3`, `batch_size=16`

3. **Regression checks**
   - CI workflow: `.github/workflows/phase1-smoke.yml`
   - Runs `smoke` preset on both datasets in `scratch` mode by default (avoids heavy pretrained download in CI).
   - Verifies:
     - run command exits successfully,
     - comparison report files exist.

## How it works

`scripts/phase1_compare.py` orchestrates all Phase 1 runs:

- resolves preset config,
- loops through selected datasets and model types,
- launches the underlying training script with consistent args,
- validates required artifacts (`eval_report.json`, `artifact.json`, `config.json`),
- extracts metrics,
- writes consolidated report files (`.md`, `.csv`, `.json`).

Outputs are organized under:

- `artifacts/phase1/runs/<preset>/<dataset>/<model>/`
- `artifacts/phase1/reports/`

## How to test locally

### A) Fast reproducibility test (smoke)

```bash
python scripts/phase1_compare.py --preset smoke --seed 42
```

Expected:

- process exits without errors,
- both dataset/model combinations are executed,
- report files are created:
  - `artifacts/phase1/reports/phase1_smoke_seed42.md`
  - `artifacts/phase1/reports/phase1_smoke_seed42.csv`
  - `artifacts/phase1/reports/phase1_smoke_seed42.json`

### B) CI-equivalent local smoke (scratch only)

```bash
python scripts/phase1_compare.py \
  --preset smoke \
  --models scratch \
  --datasets ag_news,emotion \
  --seed 42
```

Expected:

- faster than full comparison (no pretrained model download),
- same report files generated with rows for `scratch` only.

### C) Development comparison (dev preset)

```bash
python scripts/phase1_compare.py --preset dev --seed 42
```

Use this when you need more stable signal than `smoke` before deciding between scratch and pretrained.

### D) Full baseline comparison (full preset)

```bash
python scripts/phase1_compare.py --preset full --seed 42
```

Use this for release-adjacent decisions where larger sample caps are required.

## How to read the matrix

- Compare rows where `dataset` and `seed` match and only `model` differs.
- Prefer `macro_f1` for balanced class-level assessment.
- Use per-class F1 columns to detect weak classes hidden by aggregate metrics.

## CI behavior

Workflow `.github/workflows/phase1-smoke.yml` runs on:

- pull requests,
- manual dispatch.

It intentionally keeps default CI load light by checking only scratch runs and artifact/report creation.
