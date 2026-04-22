# Phase 3: Serving profile (reference API and deployment)

This document is the **stable contract** for the minimal reference HTTP service used to integrate classifiers and retrieval without digging through Python internals.

## Reference implementation

- **Script:** `scripts/phase3_reference_server.py` (FastAPI + Uvicorn, uses `TinyModelRuntime` / PyTorch on CPU in-process).
- **Install:** `pip install -r optional-requirements-phase3.txt` (adds `fastapi`, `uvicorn`, `pydantic`, plus ONNX stack if you use export/benchmark tools).

**Run (local):**

```bash
python scripts/phase3_reference_server.py --model HyperlinksSpace/TinyModel1 --host 127.0.0.1 --port 8765
# Or local:  --model artifacts/phase1/runs/smoke/ag_news/scratch
# On Windows Git Bash, do not use /path/... (shell maps it under C:/Program Files/Git/...); use a relative or c:/... path.
```

- **Health:** `GET /healthz` → `{"status":"ok"}`.

### `POST /v1/classify`

**Request (JSON):**

| Field   | Type            | Description                |
| ------- | --------------- | -------------------------- |
| `texts` | `list[string]`  | One or more inputs; required, non-empty. |

**Response (JSON):**

| Field   | Type | Description |
| ------- | ---- | ----------- |
| `items` | list | One object per input text. |
| `items[].label_scores` | `object` | Map of label name → float probability in `[0,1]`; sums to ~1 per text. |

### `POST /v1/retrieve`

**Request (JSON):**

| Field         | Type           | Default | Description                    |
| ------------- | -------------- | ------- | ------------------------------ |
| `query`       | string         | —       | Query text.                    |
| `candidates`  | `list[string]` | `[]`    | Corpora to rank.               |
| `top_k`       | int            | `3`     | 1–100, capped by list length.  |

**Response (JSON):**

| Field  | Type | Description |
| ------ | ---- | ----------- |
| `hits` | list | Each: `index` (into `candidates`), `text`, `score` (cosine similarity, higher is closer). |

## Production vs reference

- **ONNX** (`classifier.onnx` / `encoder.onnx` from `phase3_export_onnx.py`) is intended for **low-latency** inference with [ONNX Runtime](https://onnxruntime.ai/); the reference server still uses **PyTorch** for fewer moving parts. Swap the model execution layer behind the same API shape when you need ORT.
- **Default dynamo export** in this repository traces **batch=1** and a fixed **max sequence length** (aligned with training). Multi-string batches use repeated ORT runs (see `phase3_benchmark.py`); a future export with true dynamic batch/seq is possible via newer `dynamic_shapes` options.
- **Int8** dynamic quantization is **optional** (`--dynamic-quantize` on export); it may fail on some graphs—FP32 ONNX remains the supported default.

## Hardening checklist

- **Auth** — not included; add API keys or mTLS in front of Uvicorn (reverse proxy, API gateway, or cloud load balancer).
- **Workers** — one process per GPU/CPU is typical; for CPU-only, 1 Uvicorn worker per core or scale replicas behind a load balancer; avoid sharing mutable model state without care.
- **Time limits** — add request timeouts and max body size in the proxy.
- **Observability** — log `request_id`, latency, and error class; do not log raw user text in production without policy.

## Related artifacts

- `artifacts/phase3/reports/benchmark_*.md` — reproducible **CPU** latency (PyTorch vs ONNX paths).
- `scripts/phase3_onnx_parity.py` — confirms ONNX matches PyTorch for sample inputs.
- `optional-requirements-phase3.txt` — exact optional dependency pins (project root).
