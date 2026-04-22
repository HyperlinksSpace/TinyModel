# Phase 3 runtime benchmark (verify-phase2)

CPU timings (mean / p50 / p90 in ms). `retrieve` includes embedding the query and candidates, then a dot-product top-k (same work as `TinyModelRuntime.retrieve` but ONNX uses ORT for the encoder).

## Primary
- **Model:** `C:/1/1/1/1/1/TinyModel/.tmp/verify-phase2`
- **ONNX dir:** `C:/1/1/1/1/1/TinyModel/.tmp/verify-phase2/onnx`
- **Artifact sizes (MiB, selected files):** {"classifier.onnx": 0.425, "encoder.onnx": 0.358, "model.safetensors": 2.466}

### pytorch
- **classify_batch1** — mean 2.048 ms, p50 1.883 ms, p90 2.861 ms
- **embed_batch3** — mean 3.624 ms, p50 3.542 ms, p90 4.504 ms
- **retrieve_top2_query3cand** — mean 3.487 ms, p50 3.328 ms, p90 3.982 ms
### onnx
- **classify_batch1** — mean 1.677 ms, p50 1.520 ms, p90 2.012 ms
- **embed_batch3** — mean 6.039 ms, p50 5.747 ms, p90 6.904 ms
- **retrieve_top2_query3cand** — mean 8.370 ms, p50 8.043 ms, p90 10.403 ms

Re-run with: `python scripts/phase3_benchmark.py --model <path> [--compare-model <path2>]` (ensure `phase3_export_onnx.py` ran so ONNX numbers appear).
