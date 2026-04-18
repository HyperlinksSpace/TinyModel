# Evaluation split reproducibility (TinyModel1 classifier)

Training uses `scripts/train_tinymodel1_classifier.py` with a **fixed random seed** (`--seed`, default `42`).

## How train/eval subsets are built

1. Load the Hub dataset with `--train-split` and `--eval-split` (defaults: `train` and `test`).
2. **Shuffle each split** with `datasets.Dataset.shuffle(seed=args.seed)`.
3. Take the **first N rows** after shuffle:  
   - train: `min(max_train_samples, len(split))`  
   - eval: `min(max_eval_samples, len(split))`

So the eval set is **not** the raw test split in file order; it is a **deterministic subsample** of the named eval split, controlled by `seed` and `max_eval_samples`.

## Matching a run

Use the **same** values for:

- `--dataset`, `--dataset-config`
- `--train-split`, `--eval-split`
- `--text-column`, `--label-column`, `--labels` (if any)
- `--seed`
- `--max-train-samples`, `--max-eval-samples`

The exported `eval_report.json` next to the model records these fields plus metrics so you can compare runs.

## Caveats

- If the Hub dataset revision changes (new rows or order), shuffled indices can change unless you pin a dataset revision in code or cache.
- For a **frozen** eval set independent of Hub updates, export a snapshot (e.g. local JSON/parquet or a pinned Hub revision) and point training at that source.
