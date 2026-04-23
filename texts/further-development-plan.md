# Further development and enhancement plan

This plan builds on the implemented baseline and targets practical quality gains before major architecture jumps.

**Long-horizon vision (multi-year “universe brain” target, horizons and gates):** see [`further-development-universe-brain.md`](further-development-universe-brain.md)—separate from the tactical Phases 1–3 below.

## Delivery dynamics update (actual pace)

- **Observed throughput:** Phase 1 completed + Phase 2 implementation prepared in changes in **~2 days total**.
- **Implication:** original week-based estimates were conservative for current scope and environment.
- **Planning baseline from now on:** estimate in **days** with a small buffer for validation/manual review.

## Phase 1 (completed in ~1 day): stabilize and compare

### Goals

- make current pipelines repeatable,
- establish fair baseline comparisons,
- remove ambiguity in model-selection decisions.

### Tasks

1. **Baseline comparison matrix**
   - Run scratch vs pretrained on matching seeds and sample caps.
   - Record results in a simple table (`accuracy`, `macro_f1`, per-class F1).
2. **Run profile presets**
   - Define standard run presets: `smoke`, `dev`, `full`.
   - Keep commands in README to avoid ad-hoc parameter drift.
3. **Regression checks**
   - Add a lightweight CI smoke check for scripts (no heavy model downloads in CI by default).
   - Verify command exits and artifact file creation.

### Exit criteria

- one documented comparison table for at least AG News and Emotion,
- no unresolved script crashes on the primary contributor environment,
- reproducible outputs for `smoke` and `dev` presets.

### Exit steps (verification)

- Run `python scripts/phase1_compare.py --preset smoke --models scratch --datasets ag_news,emotion --seed 42` and confirm the process **exits with status 0**.
- Confirm `artifacts/phase1/reports/phase1_smoke_seed42.md` (and matching `.json`) exist and list metrics for each run.
- Re-run with `--preset dev` on a best-effort basis when validating larger comparisons; same **zero exit** expectation.
- Confirm CI workflow `.github/workflows/phase1-smoke.yml` completes successfully when triggered (or equivalent local command above).

## Phase 2 (implemented in changes, ~1 day dev + 0.5-1 day validation): data and evaluation quality

### Goals

- improve robustness and class balance behavior,
- make eval reports useful for decision-making, not just sanity checks.

### Tasks

1. **Dataset quality pass**
   - Add one more domain-relevant dataset (or internal sample if available).
   - Add class-distribution summary to eval artifacts.
2. **Error analysis**
   - Add top confusions extraction from confusion matrix.
   - Save misclassified examples sample (small JSONL) for manual review.
3. **Calibration and thresholding**
   - Add confidence summary (e.g., max-prob histogram bins).
   - For routing use cases, define fallback threshold behavior.

### Exit criteria

- eval report includes confusion highlights,
- documented threshold strategy for at least one routing scenario,
- at least one iteration based on manual error review.

### Exit steps (verification)

- Run a small training job (e.g. Phase 2 smoke in the main `README.md`) and confirm **exit status 0**.
- Open `eval_report.json` and confirm `dataset_quality`, `error_analysis`, `calibration`, and `routing` sections are present.
- Confirm `misclassified_sample.jsonl` is created when `--max-misclassified-examples` is greater than 0.
- Open `texts/phase2-routing-threshold-scenario.md` and confirm it states a **concrete** `min_confidence`, **fallback** action, and link to **eval** artifacts (routing scenario doc — **done in repo**).

### Remaining time to close Phase 2 exit

- **Documented routing scenario:** **done** — see `texts/phase2-routing-threshold-scenario.md`.
- **~0.5 day (manual):** one explicit **human** error-review loop: inspect `misclassified_sample.jsonl`, decide on **one** concrete data or model change, re-run eval, and compare metrics. This cannot be closed by automation alone.

## Phase 3 (~3-5 working days): productization and performance

### Goals

- make inference predictable in production contexts,
- reduce latency/cost while keeping acceptable quality.

### Tasks

1. **Inference packaging**
   - Add ONNX export path for selected checkpoints.
   - Validate output parity (ONNX vs PyTorch) on sample inputs.
2. **Runtime benchmarking**
   - Measure CPU latency for classify/embed/retrieve.
   - Track model size and throughput for scratch vs pretrained.
3. **Serving integration**
   - Provide reference API shape for classify + retrieval.
   - Add minimal deployment notes for a stable endpoint mode.

### Exit criteria

- one reproducible latency benchmark report,
- one quantized or ONNX test artifact,
- one documented serving profile for integration.

### Exit steps (verification)

- Export or build an ONNX (or quantized) artifact from a known checkpoint; run a parity check script and confirm **exit 0** and numeric tolerance met.
- Run benchmark commands documented next to the report, confirm **exit 0**, and archive outputs referenced by the report.
- Follow the serving profile doc end-to-end once (e.g. local or staging HTTP check) and confirm the process **exits 0** and responses match the reference API shape.

**Implemented in this repository:** `scripts/phase3_export_onnx.py` (dynamo ONNX + optional INT8 with graceful fallback), `scripts/phase3_onnx_parity.py`, `scripts/phase3_benchmark.py`, `scripts/phase3_reference_server.py`, `texts/phase3-serving-profile.md`, `optional-requirements-phase3.txt`, `artifacts/phase3/reports/` for benchmark output, and `.github/workflows/phase3-smoke.yml`. R&D follow-ups are listed in `texts/optional-rd-backlog.md` (spikes, not code requirements).

### Time split estimate for Phase 3

1. **Inference packaging (ONNX + parity):** ~1-2 days
2. **Runtime benchmarking:** ~1 day
3. **Serving integration notes/reference API:** ~1-2 days

## Optional R&D lane (parallel, low-risk commitment)

- explore parameter-efficient fine-tuning (LoRA/PEFT),
- test multilingual or domain adaptation experiments,
- prototype retrieval quality improvements with better embedding pooling.

**Backlog note:** concrete spike ideas and references live in `texts/optional-rd-backlog.md` (not scheduled with Phases 1–3).

Keep this lane isolated from release-critical timelines until metrics justify promotion.

### Optional R&D estimate

- **Per experiment spike:** ~1-2 days
- **Small batch (2-3 experiments):** ~3-5 days total

### Exit steps (verification)

- Each spike ends with a short written outcome (what was tried, metrics, **exit 0** or logged failure) and a decision to merge, drop, or schedule follow-up.
- No release branch depends on an unmerged R&D experiment without an explicit quality gate pass.

## Decision gates

Use these checks before moving to larger model/system complexity:

1. **Quality gate**: macro F1 and worst-class F1 improve meaningfully over current baseline.  
   **Exit step:** Compare `eval_report.json` / reported tables before vs after; record the delta in a PR or run log.
2. **Reliability gate**: runs are reproducible and crash-free in the target environment.  
   **Exit step:** Fixed-seed re-run matches prior metrics within expected float tolerance; all commands **exit 0**.
3. **Cost gate**: inference/training cost remains acceptable for intended usage.  
   **Exit step:** Note wall time, hardware, and (if applicable) cloud billing units for the documented run.
4. **Operations gate**: artifacts and docs are sufficient for another contributor to reproduce results.  
   **Exit step:** A second person (or clean checkout) runs the **documented** commands and gets **exit 0** and matching artifact layout; gaps are filed as issues.

## Plan status: Phase 1–3, R&D, and decision gates

| Block | Status in this repo | What it means |
| ----- | ------------------- | ------------- |
| **Phase 1** | **Complete** for the documented smoke path (see *Latest verification*). | Baseline matrix, presets, CI-shaped command — done. Optional: run `dev` / `full` for heavier comparisons. |
| **Phase 2** | **Implemented** in training/eval code + docs. | `eval_report.json` extensions, `misclassified_sample.jsonl`, routing notes, and `texts/phase2-routing-threshold-scenario.md`. Optional: one **manual** error-review loop and per-deployment threshold tuning. |
| **Phase 3** | **Implemented** (scripts, docs, CI). | ONNX export (dynamo) + parity + CPU benchmark + reference FastAPI; see main `README` and `texts/phase3-serving-profile.md`. Optional INT8 may not apply to every graph. **Compare two checkpoints** with `phase3_benchmark.py --compare-model`. |
| **Optional R&D** | **Backlog only**; see `texts/optional-rd-backlog.md`. | Run spikes when metrics justify; not required for the baseline. |
| **Decision gates** | **Ongoing checks**, not a phase to “finish.” | Before you jump to much larger models or new systems, re-check quality, reliability, cost, and operations (list above). |

**Summary:** Phases **1–3** are implemented in the repo; remaining work is **optional** polish (e.g. human error review, your deployment’s threshold, larger Phase 1 presets) or **R&D spikes** as needed.

## Latest verification (Phases 1–3, reproducible)

Run these to confirm the same exit steps as in each phase (all commands **exit 0** on success).

| Area | Command / check |
| ---- | ----------------- |
| **Phase 1** | `python scripts/phase1_compare.py --preset smoke --models scratch --datasets ag_news,emotion --seed 42` — then confirm `artifacts/phase1/reports/phase1_smoke_seed42.md` and `.json`. |
| **Phase 2 (artifact shape)** | Train a current checkpoint (or use an output dir produced after Phase 2 landed in the trainer), e.g. `python scripts/train_tinymodel1_classifier.py --output-dir .tmp/verify-phase2 --max-train-samples 64 --max-eval-samples 32 --epochs 1 --batch-size 8 --seed 42 --max-misclassified-examples 5` — then `eval_report.json` must include **`dataset_quality`**, **`error_analysis`**, **`calibration`**, **`routing`**, and **`misclassified_sample.jsonl`** (if N>0). **Note:** older cached runs under `artifacts/phase1/runs/…` may still have a **minimal** `eval_report.json` without those sections; re-train to refresh. **`texts/phase2-routing-threshold-scenario.md`** is the written routing example. |
| **Phase 3** | From the same or any valid checkpoint: `python scripts/phase3_export_onnx.py --model <dir>`, `python scripts/phase3_onnx_parity.py --model <dir>`, `python scripts/phase3_benchmark.py --model <dir>` — expect `<dir>/onnx/classifier.onnx` and `encoder.onnx`, parity passed, and `artifacts/phase3/reports/benchmark_<slug>.md`. **Hub example:** `python scripts/phase3_export_onnx.py --model HyperlinksSpace/TinyModel1` (exit 0 after download). On Windows Git Bash, use a **relative** or `c:/…` model path, not `/path/...` (see `README` Phase 3). |

**Last full local run (representative):** Phase 1 smoke and reports OK; fresh train to **`.tmp/verify-phase2`** confirmed Phase 2 **JSON** sections; Phase 3 export + parity + benchmark from that directory completed, with benchmark written to `artifacts/phase3/reports/benchmark_verify-phase2.md`.

## What is left (if any)

**Nothing blocking** the **Phase 1–3** implementation in this repository. The table below is **optional** follow-up, not “missing” features.

| Item | Status |
| ---- | ------ |
| **Phase 1 — `dev` / `full` preset** | Optional: larger baseline tables when you need them (`phase1_compare.py` presets). |
| **CI on default branch** | Confirm `phase1-smoke.yml` and `phase3-smoke.yml` are green on `main` when you merge. |
| **Phase 2 — manual error-review iteration** | Optional: inspect `misclassified_sample.jsonl` and iterate on data/model. |
| **Phase 2 — deploy threshold** | Example only in `texts/phase2-routing-threshold-scenario.md`; validate on your data. |
| **Phase 3 — production hardening** | The reference server has **no** auth; add a gateway. Dynamic batch/seq in ONNX (beyond batch=1 trace) if you outgrow the current export. |
| **Optional R&D** | See `texts/optional-rd-backlog.md`. |
| **Operations gate (second person)** | Independent clean-clone run before a major release if you need it. |
