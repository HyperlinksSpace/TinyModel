# Horizon 1 (short term): three-dataset run summary

Trained with shared caps: train=300, eval=150, epochs=1, batch=8, seed=42.

| Task | dataset (Hub) | accuracy | macro_f1 |
| ---- | -------------- | -------- | -------- |
| ag_news | fancyzhx/ag_news | 0.266667 | 0.200481 |
| emotion | emotion | 0.386667 | 0.092949 |
| sst2 | glue | 0.54 | 0.350649 |

Per-task directories (each has `eval_report.json`, `misclassified_sample.jsonl`, model files):

- **ag_news:** `artifacts/horizon1/three-tasks/ag_news`
- **emotion:** `artifacts/horizon1/three-tasks/emotion`
- **sst2:** `artifacts/horizon1/three-tasks/sst2`

## Phase 2 `routing` quick check

Each task directory contains **`eval_report.json`** with top-level **`routing`** when using current training scripts. Example for the **first table row** (`ag_news`):

`python scripts/routing_policy.py --from-checkpoint artifacts/horizon1/three-tasks/ag_news`

See **README** (Phase 2 and Horizon 1 route-to-RAG).

See [`further-development-universe-brain.md`](further-development-universe-brain.md) short-term block **B**.

