# Phase 3 runtime benchmark (horizon1-verify-a)

CPU timings (mean / p50 / p90 in ms). `retrieve` includes embedding the query and candidates, then a dot-product top-k (same work as `TinyModelRuntime.retrieve` but ONNX uses ORT for the encoder).

## Primary
- **Model:** `C:/1/1/1/1/1/TinyModel/.tmp/horizon1-verify-a`
- **ONNX dir:** `C:/1/1/1/1/1/TinyModel/.tmp/horizon1-verify-a/onnx`
- **Artifact sizes (MiB, selected files):** {"classifier.onnx": 0.425, "encoder.onnx": 0.358, "model.safetensors": 2.466}

### pytorch
- **classify_batch1** — mean 1.460 ms, p50 1.500 ms, p90 1.672 ms
- **embed_batch3** — mean 1.944 ms, p50 1.943 ms, p90 2.135 ms
- **retrieve_top2_query3cand** — mean 2.242 ms, p50 2.202 ms, p90 2.590 ms
### onnx
- **classify_batch1** — mean 1.467 ms, p50 1.390 ms, p90 1.704 ms
- **embed_batch3** — mean 4.853 ms, p50 4.732 ms, p90 6.386 ms
- **retrieve_top2_query3cand** — mean 6.614 ms, p50 6.747 ms, p90 7.648 ms

Re-run with: `python scripts/phase3_benchmark.py --model <path> [--compare-model <path2>]` (ensure `phase3_export_onnx.py` ran so ONNX numbers appear).
