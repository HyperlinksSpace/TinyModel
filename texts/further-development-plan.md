# Further development and enhancement plan

This plan builds on the implemented baseline and targets practical quality gains before major architecture jumps.

## Phase 1 (next 1-2 weeks): stabilize and compare

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

## Phase 2 (2-4 weeks): data and evaluation quality

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

## Phase 3 (4-8 weeks): productization and performance

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

## Optional R&D lane (parallel, low-risk commitment)

- explore parameter-efficient fine-tuning (LoRA/PEFT),
- test multilingual or domain adaptation experiments,
- prototype retrieval quality improvements with better embedding pooling.

Keep this lane isolated from release-critical timelines until metrics justify promotion.

## Decision gates

Use these checks before moving to larger model/system complexity:

1. **Quality gate**: macro F1 and worst-class F1 improve meaningfully over current baseline.
2. **Reliability gate**: runs are reproducible and crash-free in the target environment.
3. **Cost gate**: inference/training cost remains acceptable for intended usage.
4. **Operations gate**: artifacts and docs are sufficient for another contributor to reproduce results.
