# Phase 3 runtime benchmark (scratch)

CPU timings (mean / p50 / p90 in ms). `retrieve` includes embedding the query and candidates, then a dot-product top-k (same work as `TinyModelRuntime.retrieve` but ONNX uses ORT for the encoder).

## Primary
- **Model:** `artifacts/phase1/runs/smoke/ag_news/scratch`
- **ONNX dir:** `artifacts/phase1/runs/smoke/ag_news/scratch/onnx`
- **Artifact sizes (MiB, selected files):** {"classifier.onnx": 0.425, "encoder.onnx": 0.358, "model.safetensors": 3.104}

### pytorch
- **classify_batch1** — mean 2.478 ms, p50 2.761 ms, p90 2.958 ms
- **embed_batch3** — mean 4.014 ms, p50 4.128 ms, p90 4.519 ms
- **retrieve_top2_query3cand** — mean 4.728 ms, p50 4.684 ms, p90 5.162 ms
### onnx
- **classify_batch1** — mean 1.704 ms, p50 1.593 ms, p90 2.160 ms
- **embed_batch3** — mean 5.616 ms, p50 5.573 ms, p90 6.025 ms
- **retrieve_top2_query3cand** — mean 5.421 ms, p50 4.966 ms, p90 6.946 ms

Re-run with: `python scripts/phase3_benchmark.py --model <path> [--compare-model <path2>]` (ensure `phase3_export_onnx.py` ran so ONNX numbers appear).
