# Phase 1 comparison matrix

| dataset | model | seed | max_train_samples | max_eval_samples | accuracy | macro_f1 | f1_Business | f1_Sci/Tech | f1_Sports | f1_World | f1_anger | f1_fear | f1_joy | f1_love | f1_sadness | f1_surprise |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ag_news | scratch | 42 | 120 | 80 | 0.2625 | 0.10396 | 0.0 | 0.0 | 0.415842 | 0.0 |  |  |  |  |  |  |
| ag_news | pretrained | 42 | 120 | 80 | 0.7125 | 0.604038 | 0.71875 | 0.0 | 0.954545 | 0.742857 |  |  |  |  |  |  |
| emotion | scratch | 42 | 120 | 80 | 0.2375 | 0.063973 |  |  |  |  | 0.0 | 0.0 | 0.0 | 0.0 | 0.383838 | 0.0 |
| emotion | pretrained | 42 | 120 | 80 | 0.25 | 0.075379 |  |  |  |  | 0.0 | 0.0 | 0.064516 | 0.0 | 0.387755 | 0.0 |

## Phase 2 `routing` quick check

Each run directory contains **`eval_report.json`** with a top-level **`routing`** object when using current training scripts. Dump the embedded policy notes (no model load), e.g. for the **first row** of this matrix:

`python scripts/routing_policy.py --from-checkpoint artifacts/phase1/runs/smoke/ag_news/scratch`

See **README** (Phase 2 and Horizon 1 route-to-RAG). CI (**`phase1-smoke.yml`**) runs the same check on **`ag_news/scratch`** when that cell is in the matrix.
