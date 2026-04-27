<div align="center">

# TinyModel

### Tiny, deployable text classification baseline for rapid product iteration

[![Model](https://img.shields.io/badge/Hugging%20Face-TinyModel1-yellow)](https://huggingface.co/HyperlinksSpace/TinyModel1)
[![Space Hub](https://img.shields.io/badge/Space%20Hub-TinyModel1Space-orange)](https://huggingface.co/spaces/HyperlinksSpace/TinyModel1Space)
[![Live preview](https://img.shields.io/badge/Live%20preview-Gradio%20app-brightgreen)](https://hyperlinksspace-tinymodel1space.hf.space)

</div>

`TinyModel` is a practical starter model line for text classification.
End users consume deployed Hugging Face model and Space endpoints. Maintainer deployment policy lives in `texts/HUGGING_FACE_DEPLOYMENT_INTERNAL.md`.

Repository: [HyperlinksSpace/TinyModel](https://github.com/HyperlinksSpace/TinyModel)

**TinyModel1 on Hugging Face**

- **Model weights & model card** — [HyperlinksSpace/TinyModel1](https://huggingface.co/HyperlinksSpace/TinyModel1): Safetensors, tokenizer, and `README.md` on the Hugging Face Hub (load with `transformers` or the Inference API where available).
- **Space project (Hub)** — [HyperlinksSpace/TinyModel1Space](https://huggingface.co/spaces/HyperlinksSpace/TinyModel1Space): Space repository (app code, build logs, settings, community).
- **Live Gradio app** — **Direct app URL:** [https://hyperlinksspace-tinymodel1space.hf.space](https://hyperlinksspace-tinymodel1space.hf.space) · **Same app on the Hub:** [huggingface.co/spaces/HyperlinksSpace/TinyModel1Space](https://huggingface.co/spaces/HyperlinksSpace/TinyModel1Space). If the direct link fails or is blocked, use the Hub link or see **Availability in Russia** below.

**Availability in Russia**

Some features may not work reliably from Russia—for example **live preview** or other flows that depend on third-party hosts or regions that are blocked or throttled. If you hit that, you can try third-party tools such as the free tier of [1VPN](https://1vpn.org/) (browser extension or app), or **Happ** (paid subscription). One place people buy Happ subscriptions is [this Telegram bot](https://t.me/tylervpsbot). These are all **third-party** services; use at your own discretion and follow applicable laws.

**Model card (README)** — On the Hub, the model card is the **`README.md`** file at the root of the model repo (same URL as the model). In this repository, the template is implemented by `write_model_card()` in [`scripts/train_tinymodel1_classifier.py`](https://github.com/HyperlinksSpace/TinyModel/blob/main/scripts/train_tinymodel1_classifier.py); training writes `README.md`, [`artifact.json`](https://github.com/HyperlinksSpace/TinyModel/blob/main/scripts/train_tinymodel1_classifier.py), and `eval_report.json` next to the weights. We do **not** run CI that downloads full model weights into the repo or runner caches for republish; update the card by retraining and publishing, or edit `README.md` on the Hub and keep weights unchanged.

## 1) Local testing

Train locally after cloning the repo:

```bash
python scripts/train_tinymodel1_agnews.py --output-dir .tmp/TinyModel-local
```

Quick local inference sanity check:

```bash
python -c "from transformers import pipeline; p=pipeline('text-classification', model='.tmp/TinyModel-local', tokenizer='.tmp/TinyModel-local'); print(p('Stocks rallied after central bank comments', top_k=None))"
```

### Phase 1 presets and comparison matrix

`scripts/phase1_compare.py` standardizes run profiles and prevents ad-hoc parameter drift.
It executes matching-seed runs and writes a comparison matrix with `accuracy`, `macro_f1`,
and per-class F1 for each run.

Presets:

- `smoke`: quickest reproducibility/health check (`120/80`, `1 epoch`)
- `dev`: day-to-day iteration (`1000/300`, `2 epochs`)
- `full`: heavier baseline (`6000/1200`, `3 epochs`)

Run full Phase 1 baseline comparison (scratch vs pretrained) on both AG News and Emotion:

```bash
python scripts/phase1_compare.py --preset smoke --seed 42
```

Outputs:

- `artifacts/phase1/runs/<preset>/<dataset>/<model>/...` (model artifacts per run)
- `artifacts/phase1/reports/phase1_<preset>_seed<seed>.md` (human-readable table)
- `artifacts/phase1/reports/phase1_<preset>_seed<seed>.csv` (spreadsheet-friendly)
- `artifacts/phase1/reports/phase1_<preset>_seed<seed>.json` (machine-readable)

CI smoke check (no heavy pretrained download by default):

```bash
python scripts/phase1_compare.py \
  --preset smoke \
  --models scratch \
  --datasets ag_news,emotion \
  --seed 42
```

This same default check is wired in `.github/workflows/phase1-smoke.yml`.

## Phase 2: Evaluation quality (datasets, errors, calibration)

Training and pretrained fine-tuning now emit richer evaluation artifacts so reports support decisions beyond headline accuracy.

| Artifact | What it contains |
| -------- | ---------------- |
| **`eval_report.json`** | Existing `reproducibility` + `metrics`, plus **`dataset_quality.class_distribution`** (train/eval counts and proportions per label on the capped subsets), **`error_analysis.top_confusions`** (largest off-diagonal confusion pairs), **`calibration.max_prob_histogram`** (bins over the winner softmax probability per eval example), and **`routing`** (documented fallback behavior for low-confidence routing; thresholds are not fixed by training). |
| **`misclassified_sample.jsonl`** | Up to **`--max-misclassified-examples`** wrong predictions with `text`, `true_label`, `predicted_label`, `max_prob` (one JSON object per line). Use `0` to skip writing the file content beyond an empty run. |

**Routing threshold example (Phase 2 exit):** a worked **min_confidence** + **fallback** policy for triage is documented in [`texts/phase2-routing-threshold-scenario.md`](texts/phase2-routing-threshold-scenario.md) (tune on your own validation data).

CLI knobs (scratch and [`finetune_pretrained_classifier.py`](scripts/finetune_pretrained_classifier.py)):

- `--max-misclassified-examples` (default `100`)
- `--confidence-histogram-bins` (default `10`)
- `--top-confusions` (default `20`)

**Third reference dataset (SST-2)** — binary sentiment on GLUE, useful as an additional domain check:

```bash
python scripts/train_tinymodel1_sst2.py \
  --output-dir .tmp/TinyModel-sst2 \
  --max-train-samples 500 \
  --max-eval-samples 200 \
  --epochs 1 \
  --batch-size 8 \
  --seed 42
```

Quick Phase 2 smoke (AG News, small caps):

```bash
python scripts/train_tinymodel1_classifier.py \
  --output-dir .tmp/phase2-smoke \
  --max-train-samples 64 \
  --max-eval-samples 32 \
  --epochs 1 \
  --batch-size 8 \
  --seed 42 \
  --max-misclassified-examples 20
```

Then inspect `.tmp/phase2-smoke/eval_report.json` (new sections) and `.tmp/phase2-smoke/misclassified_sample.jsonl`.

Expected local output folder:

- `.tmp/TinyModel-local/model.safetensors`
- `.tmp/TinyModel-local/config.json`
- `.tmp/TinyModel-local/tokenizer.json`
- `.tmp/TinyModel-local/README.md`
- `.tmp/TinyModel-local/artifact.json`
- `.tmp/TinyModel-local/eval_report.json` — evaluation metrics, confusion matrix, reproducibility, and Phase 2 fields (class distribution, top confusions, calibration histogram, routing notes)
- `.tmp/TinyModel-local/misclassified_sample.jsonl` — optional sample of errors for review (see Phase 2 section)

## Phase 3: ONNX, CPU benchmarks, reference HTTP API

**Optional dependencies:** `optional-requirements-phase3.txt` (ONNX, ONNX Runtime, `onnxscript` for export, `fastapi`/`uvicorn` for the reference server). PyTorch 2.6+ uses `torch.onnx.export(..., dynamo=True)`.

1. **Export** — from a training output directory or Hub id:

   ```bash
   python scripts/phase3_export_onnx.py --model artifacts/phase1/runs/smoke/ag_news/scratch
   # or: --model HyperlinksSpace/TinyModel1
   ```

   On **Windows Git Bash**, do **not** use a Unix-style placeholder like `/path/to/checkpoint` — the shell rewrites it under `C:/Program Files/Git/...`. Use a **relative** path from the repo or a `c:/...` path.

   Writes `onnx/classifier.onnx` (logits) and `onnx/encoder.onnx` (pooled token for embeddings). The default dynamo path traces at **batch size 1**; use tokenizer **padding to `max_seq_length`** (e.g. 128) to match. Optional `--dynamic-quantize` attempts INT8 sidecars (may be skipped on some graphs).

2. **Parity (PyTorch vs ONNX Runtime):**

   ```bash
   python scripts/phase3_onnx_parity.py --model artifacts/phase1/runs/smoke/ag_news/scratch
   ```

3. **CPU benchmark report** (PyTorch `TinyModelRuntime` vs ORT, classify / embed / retrieve patterns):

   ```bash
   python scripts/phase3_benchmark.py --model artifacts/phase1/runs/smoke/ag_news/scratch --compare-model .tmp/phase3-smoke
   ```

   Artifacts: `artifacts/phase3/reports/benchmark_<name>.{json,md}`. (Example report may be present under that folder after a run.)

4. **Serving contract + minimal API** — [`texts/phase3-serving-profile.md`](texts/phase3-serving-profile.md) (`GET /healthz`, `POST /v1/classify`, `POST /v1/retrieve`). Reference process:

   ```bash
   pip install -r optional-requirements-phase3.txt
   python scripts/phase3_reference_server.py --model HyperlinksSpace/TinyModel1
   ```

5. **CI** — `.github/workflows/phase3-smoke.yml` trains a tiny model, exports ONNX, runs parity, and writes a benchmark under `artifacts/phase3/reports/`.

**Optional R&D spike ideas (not part of the release path)** — see [`texts/optional-rd-backlog.md`](texts/optional-rd-backlog.md).

## Horizon 1 (short term): one-shot verify, three tasks, RAG smoke

This is the **A–C** tranche from [`texts/further-development-universe-brain.md`](texts/further-development-universe-brain.md) (baseline closure, multi-dataset eval breadth, minimal FAQ-style retrieval). Full commands, what gets written, and how to test manually: **[`texts/horizon1-short-term-handbook.md`](texts/horizon1-short-term-handbook.md)**.

| Block | What you run | Why it helps |
| ----- | ------------ | ------------ |
| **A — Verify** | **Two commands** (do not put `then` on the `pip` line): `pip install -r optional-requirements-phase3.txt` then a **new** line: `python scripts/horizon1_verify_short_term_a.py`. Or: `pip install -r optional-requirements-phase3.txt && python scripts/horizon1_verify_short_term_a.py` (Git Bash / PowerShell 7+). Add `--skip-phase3` to skip ONNX. | Proves Phases 1–2 plus export/parity/benchmark in **one** local pass, aligned with `phase1-smoke` / `phase3-smoke` CI. |
| **B — Three tasks** | `python scripts/horizon1_three_datasets.py` (use `--offline-datasets` if Hugging Face download times out but data is already cached) | **AG News**, **Emotion**, and **SST-2** with shared caps; summary table: [`texts/horizon1-three-tasks-summary.md`](texts/horizon1-three-tasks-summary.md). Weights go under `artifacts/horizon1/three-tasks/` (gitignored; commit the `texts/` summary). |
| **C — RAG smoke** | `python scripts/rag_faq_smoke.py` (optional `--model`; defaults to a local checkpoint if present, else `HyperlinksSpace/TinyModel1` on the Hub) | Hybrid lexical + `TinyModelRuntime` retrieval over [`texts/rag_faq_corpus.md`](texts/rag_faq_corpus.md); template for support/FAQ products. |

## Horizon 2: generative core (open causal LM, JSON runs, optional API)

**What it is:** a **local** [transformers](https://github.com/huggingface/transformers) path that turns text into new text: **summarize**, **reformulate**, and **grounded** (RAG context + answer) — aligned with the “Generative core” line in [`texts/further-development-universe-brain.md`](texts/further-development-universe-brain.md). It **does not** replace your classifier; it **complements** Horizon 1 (retrieval) and your Phase 1–3 stack.

| Piece | What you run | Why it helps |
| ----- | ------------ | ------------ |
| **Install** | `pip install -r optional-requirements-horizon2.txt` (plus your existing `torch`) | Picks up `transformers` / `accelerate` for `AutoModelForCausalLM`. |
| **Smoke verify** | `python scripts/horizon2_generative.py --verify` | One greedy generation with `sshleifer/tiny-gpt2` → proves downloads + wiring (not demo quality). |
| **Real run** | `python scripts/horizon2_generative.py` or set `HORIZON2_MODEL=HuggingFaceTB/SmolLM2-360M-Instruct` | Writes `horizon2` JSON under `.tmp/horizon2/last_run.json` with per-sample **latency** and **token counts** for cost and tier planning. |
| **Side-by-side** | add `--compare-with <other-hf-id>` | Same inputs, two model outputs in one JSON (Horizon 2 **exit** shaped like “A/B on domain tasks”). |
| **+ RAG** | `--task grounded --context-file <chunk>` (or `--context "..."`) | Pairs [FAQ / retrieval](texts/rag_faq_corpus.md) with generation. |
| **HTTP** | `pip install -r optional-requirements-phase3.txt` then `python scripts/horizon2_server.py --smoke` | `GET /` lists routes; **Swagger UI:** `http://127.0.0.1:8766/docs` — `POST /v1/generate` (same product pattern as the Phase 3 reference server). |

**Benefits (product / engineering):**

- **Drafts and summaries** on top of the same org data and policies you already use for classification.
- **One JSON contract** per run (`horizon2_generative_run/1.0`) for dashboards and regression checks (see [`texts/horizon2-handbook.md`](texts/horizon2-handbook.md)).
- **Tier awareness:** smoke vs. default Instruct vs. your own API — documented in the handbook; latencies are recorded in the artifact.

**CI:** `.github/workflows/horizon2-smoke.yml` runs `--verify` on pushes to `main` (requires Hub access in GitHub’s network; local verify is the fallback).

## Horizon 3: persistent mind (session + long-term memory, audit, DSR-shaped export)

**What it is:** a **local SQLite** memory layer for **org/user `scope_key`**, with **`session`** vs **`long_term`** rows, optional **TTL** + **`prune`**, an **audit log**, **export** (access-shaped JSON), and **`forget-scope`** (delete all data for a scope). See [`texts/further-development-universe-brain.md`](texts/further-development-universe-brain.md) — *Persistent mind*.

| Piece | What you run | Why it helps |
| ----- | ------------ | ------------ |
| **Self-test** | `python scripts/horizon3_memory_cli.py --verify` | No network; validates CRUD, export, session clear, TTL prune, forget. |
| **Daily use** | `python scripts/horizon3_memory_cli.py put|get|list|export|forget-scope|clear-session|prune|audit` (see `-h`) | Editable, auditable, deletable memory — not an opaque vector dump. |
| **Optional HTTP** | `pip install -r optional-requirements-phase3.txt` then `python scripts/horizon3_memory_api.py` | **http://127.0.0.1:8767/docs** — `put` / `list` / `export` / `forget` (default port **8767**; set `HORIZON3_DB`). |

**Benefits**

- **Product:** carry **continuity** across sessions (long-term) while **dropping chat noise** (session clear) or **expiring** junk (TTL + prune).
- **Governance:** **audit** trail for creates/updates/deletes; **export** supports access requests; **forget-scope** supports erasure for a tenant id (you still own legal review and scope design).
- **Engineering:** **stdlib-only** store and CLI — no new pip packages for the core; optional FastAPI matches Phase 3 patterns.

**Manual test recipe:** [`texts/horizon3-handbook.md`](texts/horizon3-handbook.md).

**CI:** `.github/workflows/horizon3-smoke.yml` runs `horizon3_memory_cli.py --verify` (offline).

## Horizon 4: multimodal grounding (image + text, CLIP alignment)

**What it is:** a **CLIP**-style path (Hugging Face `transformers`: **image + caption** → one alignment `logit`) for “does this picture go with this text?” — a narrow slice of **multimodal grounding** from [`texts/further-development-universe-brain.md`](texts/further-development-universe-brain.md). **Audio** and automated **moderation** are **not** in this script; add them in product layers.

| Piece | What you run | Why it helps |
| ----- | ------------ | ------------ |
| **Install** | `pip install -r optional-requirements-horizon4.txt` (and `torch` + `transformers` for real Hub models) | Adds **Pillow**; reuses the same PyTorch stack as the rest of the repo. |
| **CI / offline verify** | `python scripts/horizon4_multimodal.py --verify` | **No Hub download** — random `CLIPConfig` + `CLIPModel` forward; proves the wiring. On **Windows** this uses a **subprocess** and OpenMP env defaults to avoid native crashes; if PyTorch still fails, see the handbook. |
| **Pretrained check** | `python scripts/horizon4_multimodal.py --verify-pretrained` | Loads **`HORIZON4_CLIP_MODEL`** (default `openai/clip-vit-base-patch32`) if cached/online. |
| **Real photo + text** | `python scripts/horizon4_multimodal.py --image <file> --text "<caption>"` | JSON under `.tmp/horizon4/last_run.json` with `logit_image_text` for triage, QA, or internal benchmarks. |

**Benefits:** one **concrete** image–text score next to your text-only classifiers; **governance** still needs human/review for abuse; **smoke** stays **offline** and fast in CI.

**Manual steps:** [`texts/horizon4-handbook.md`](texts/horizon4-handbook.md)

**CI:** `.github/workflows/horizon4-smoke.yml` runs `horizon4_multimodal.py --verify` (no network).

## Horizon 6: converged stack (chain H2 + H3 + H4)

**What it is:** a **thin smoke orchestrator** from [`texts/further-development-universe-brain.md`](texts/further-development-universe-brain.md) (*Converged stack*)—one command runs the **existing** generative, memory, and CLIP smokes in order and writes **one** JSON file (`horizon6_converged_run/1.0`).

| Piece | What you run | Why it helps |
| ----- | ------------ | ------------ |
| **Install** | `pip install` **torch** (CPU is fine) + `pip install -r optional-requirements-horizon2.txt` + `pip install -r optional-requirements-horizon4.txt` | H2 and H4 share a **transformers** stack; H3 stays **stdlib**-only. |
| **Converged verify** | `python scripts/horizon6_converged_smoke.py --verify` | Chains: `horizon2_generative.py --verify` → `horizon3_memory_cli.py --verify` → `horizon4_multimodal.py --verify`. Output: `.tmp/horizon6-converge/run.json`. |
| **Optional RAG** | same command with `--with-rag` | Also runs `rag_faq_smoke.py` (needs a **trained** `config.json` dir or Hub **download**; can fail in air-gapped envs). |

**What is still *not* H6 (full exit):** a **single** production **runtime** and router, one **auth/tenant** story, and a real **incident runbook**—this repo only proves **component** smokes in sequence.

**How to test (local):** install deps as above, then `python scripts/horizon6_converged_smoke.py --verify`. Expect exit **0** and `ok: true` in the JSON; H2 may hit the Hub once for `sshleifer/tiny-gpt2` if not cached. **Faster one-offs:** run each horizon’s `--verify` alone (see Horizon 2–4 sections above).

**CI:** `.github/workflows/horizon6-smoke.yml` runs the same command on **CPU** in GitHub Actions.

## Horizon 7: assured platform (tenant isolation smoke)

**What it is:** a **stdlib-only** check that two **separate** SQLite files (two “tenants”) do **not** share memory rows or exports, using the same **Horizon 3** store as the rest of the repo. This is a **toy** for **H7 isolation** from [`texts/further-development-universe-brain.md`](texts/further-development-universe-brain.md)—not legal/compliance by itself.

| Piece | What you run | Why it helps |
| ----- | ------------ | ------------ |
| **Self-test** | `python scripts/horizon7_assured_smoke.py --verify` | No **torch**; output `.tmp/horizon7-assured/run.json` (`horizon7_assured_run/1.0`) with per-check `ok` flags. |

**What is still *not* H7 (full exit):** **repeatable** tenant onboarding, **regulatory** evidence packs, **external** audit, **SLAs**, **quotas**—treat the script as a **developer** check only.

**How to test (local):** `python scripts/horizon7_assured_smoke.py --verify` — should print `horizon7 verify: OK` and write JSON with all checks `ok: true`.

**CI:** `.github/workflows/horizon7-smoke.yml` runs the same command (no extra pip deps).

## Horizon 8: observability probe bundle (environment + H7 probe)

**What it is:** a **single JSON “build + health”** snapshot from [`texts/further-development-universe-brain.md`](texts/further-development-universe-brain.md) (*Observability & probe bundle*)—Python/platform, optional **git** short SHA, and a **real** run of **Horizon 7**’s verify as a dependency probe.

| Piece | What you run | Why it helps |
| ----- | ------------ | ------------ |
| **Probe verify** | `python scripts/horizon8_observability_probe.py --verify` | Writes `.tmp/horizon8-probe/run.json` (`horizon8_probe_run/1.0`). **No torch**; needs `git` only for `git_rev` when available. |

**What is still *not* H8 (full exit):** **SLOs**, **alerting**, streaming **metrics**, and **dashboards**—this is a **file-shaped** probe for CI and manual triage.

**How to test (local):** `python scripts/horizon8_observability_probe.py --verify` — expect `horizon8 verify: OK` and `ok: true` with a `probes` list.

**CI:** `.github/workflows/horizon8-smoke.yml`.

## Horizon 9: declarative policy (allow / deny matrix)

**What it is:** a **versioned sample policy** (`texts/horizon9_policy_sample.json`) and a **smoke** that checks **deny-over-allow** precedence and **default deny**—from the *Declarative policy & capability gates* horizon in [`texts/further-development-universe-brain.md`](texts/further-development-universe-brain.md).

| Piece | What you run | Why it helps |
| ----- | ------------ | ------------ |
| **Policy verify** | `python scripts/horizon9_policy_smoke.py --verify` | Writes `.tmp/horizon9-policy/run.json` (`horizon9_policy_run/1.0`). Optional `--policy path.json`. **Stdlib only.** |

**What is still *not* H9 (full exit):** **AuthN**, **OPA**, **signed** policy, **dynamic** attributes, **audit** of policy edits in production.

**How to test (local):** `python scripts/horizon9_policy_smoke.py --verify` — expect `horizon9 verify: OK` and all case rows `ok: true`.

**CI:** `.github/workflows/horizon9-smoke.yml`.

## Horizon 10: budget & unit caps (FinOps-shaped)

**What it is:** a **sample budget** (`texts/horizon10_budget_sample.json`) and smoke that accumulates **abstract units** per action until **deny**—see *Resource & cost envelopes* in [`texts/further-development-universe-brain.md`](texts/further-development-universe-brain.md).

| Piece | What you run | Why it helps |
| ----- | ------------ | ------------ |
| **Budget verify** | `python scripts/horizon10_budget_smoke.py --verify` | Writes `.tmp/horizon10-budget/run.json` (`horizon10_budget_run/1.0`). **Stdlib only.** |

**What is still *not* H10 (full exit):** live metering, distributed quotas, billing reconciliation.

**How to test (local):** `python scripts/horizon10_budget_smoke.py --verify`.

**CI:** `.github/workflows/horizon10-smoke.yml`.

## Horizon 11: human feedback capture (JSONL)

**What it is:** validated **newline-delimited JSON** for label corrections (`horizon11_feedback_record/1.0`)—see *Human outcome capture* in [`texts/further-development-universe-brain.md`](texts/further-development-universe-brain.md).

| Piece | What you run | Why it helps |
| ----- | ------------ | ------------ |
| **Feedback verify** | `python scripts/horizon11_feedback_smoke.py --verify` | Writes `.tmp/horizon11-feedback/` (`sample_feedback.jsonl` + `run.json`, `horizon11_feedback_run/1.0`). **Stdlib only.** |

**What is still *not* H11 (full exit):** secure pipelines, PII policy, automated retraining.

**How to test (local):** `python scripts/horizon11_feedback_smoke.py --verify`.

**CI:** `.github/workflows/horizon11-smoke.yml`.

## Horizon 12: provenance manifest (SHA-256 of pinned configs)

**What it is:** **Integrity fingerprints** for committed sample policies/budgets—see *Provenance & integrity manifest* in [`texts/further-development-universe-brain.md`](texts/further-development-universe-brain.md).

| Piece | What you run | Why it helps |
| ----- | ------------ | ------------ |
| **Provenance verify** | `python scripts/horizon12_provenance_smoke.py --verify` | Writes `.tmp/horizon12-provenance/run.json` (`horizon12_provenance_run/1.0`). **Stdlib only.** |

**What is still *not* H12 (full exit):** signing, timestamp authorities, in-toto/Sigstore.

**How to test (local):** `python scripts/horizon12_provenance_smoke.py --verify`.

**CI:** `.github/workflows/horizon12-smoke.yml`.

## Horizon 13: circuit breaker (resilience demo)

**What it is:** a **state-machine** exercise for **OPEN / HALF_OPEN / CLOSED** around a failing upstream—see *Resilience: circuit breaker* in [`texts/further-development-universe-brain.md`](texts/further-development-universe-brain.md).

| Piece | What you run | Why it helps |
| ----- | ------------ | ------------ |
| **Circuit verify** | `python scripts/horizon13_circuit_smoke.py --verify` | Writes `.tmp/horizon13-circuit/run.json` (`horizon13_circuit_run/1.0`). **Stdlib only.** |

**What is still *not* H13 (full exit):** async middleware, distributed coordination, production metrics.

**How to test (local):** `python scripts/horizon13_circuit_smoke.py --verify`.

**CI:** `.github/workflows/horizon13-smoke.yml`.

## Horizon 14: workflow DAG (topological order)

**What it is:** a **linear inference DAG** plus **cycle detection** and **parallel-root** sanity checks—see *Orchestrated workflows* in [`texts/further-development-universe-brain.md`](texts/further-development-universe-brain.md).

| Piece | What you run | Why it helps |
| ----- | ------------ | ------------ |
| **DAG verify** | `python scripts/horizon14_workflow_smoke.py --verify` | Writes `.tmp/horizon14-workflow/run.json` (`horizon14_workflow_run/1.0`). **Stdlib only.** |

**What is still *not* H14 (full exit):** retries, sagas, production orchestrator integration.

**How to test (local):** `python scripts/horizon14_workflow_smoke.py --verify`.

**CI:** `.github/workflows/horizon14-smoke.yml`.

## Horizon 15: export envelope (field allow-lists)

**What it is:** **`texts/horizon15_export_envelope_sample.json`** defines allowed keys per export kind; the smoke rejects extra fields—see *Data minimization & export envelopes* in [`texts/further-development-universe-brain.md`](texts/further-development-universe-brain.md).

| Piece | What you run | Why it helps |
| ----- | ------------ | ------------ |
| **Envelope verify** | `python scripts/horizon15_export_smoke.py --verify` | Writes `.tmp/horizon15-export/run.json` (`horizon15_export_run/1.0`). **Stdlib only.** |

**What is still *not* H15 (full exit):** encryption, legal sign-off, automated redaction pipelines.

**How to test (local):** `python scripts/horizon15_export_smoke.py --verify`.

**CI:** `.github/workflows/horizon15-smoke.yml`.

### Training script: evaluation and artifacts

The canonical training implementation is [`scripts/train_tinymodel1_classifier.py`](https://github.com/HyperlinksSpace/TinyModel/blob/main/scripts/train_tinymodel1_classifier.py). [`scripts/train_tinymodel1_agnews.py`](https://github.com/HyperlinksSpace/TinyModel/blob/main/scripts/train_tinymodel1_agnews.py) is a thin wrapper that calls the same `main()` with AG News–friendly defaults.

| Function / area | Role |
| ---------------- | ---- |
| **`parse_args()`** | CLI for dataset id, splits, text/label columns, caps, hyperparameters, `--seed`, and Hub card metadata. |
| **`set_seed()`** | Sets Python, NumPy, and PyTorch RNGs so runs are repeatable for a given `--seed`. |
| **`load_splits()`** | Loads the Hub dataset, selects train/eval split names, **shuffles each split with `seed`**, then takes the first *N* rows (`--max-train-samples`, `--max-eval-samples`). |
| **`infer_text_column()`** | Picks the text column if you do not pass `--text-column`. |
| **`resolve_label_names()`** / **`build_label_maps()`** / **`rows_to_model_inputs()`** | Resolve class names, map raw labels to contiguous ids, and build `Dataset` columns for training. |
| **`build_tokenizer()`** | Trains a WordPiece tokenizer on training texts and writes tokenizer files under the output dir. |
| **`evaluate()`** / **`evaluate_with_details()`** | Runs eval, builds the confusion matrix and **`EvalMetrics`**; **`evaluate_with_details`** also records per-example **max softmax** (winner) probability for calibration histograms. |
| **`write_eval_report()`** | Writes **`eval_report.json`**: `reproducibility`, `metrics`, plus optional **`dataset_quality`**, **`error_analysis`**, **`calibration`**, **`routing`** (see Phase 2 section). |
| **`write_misclassified_jsonl()`** | Writes **`misclassified_sample.jsonl`** (up to N lines) for manual error review. |
| **`write_manifest()`** | Writes **`artifact.json`**: training config, labels, and summary metrics for downstream tooling. |
| **`write_model_card()`** | Writes Hub-style **`README.md`** next to the weights (model card with eval summary). |
| **`copy_model_card_image()`** | Optionally copies `TinyModel1Image.png` into the output dir for the card banner. |

How the eval subset is defined (same script, same seed → same rows) is documented in [`texts/eval-reproducibility.md`](texts/eval-reproducibility.md).

### Second reference dataset (Emotion)

Besides AG News ([`train_tinymodel1_agnews.py`](https://github.com/HyperlinksSpace/TinyModel/blob/main/scripts/train_tinymodel1_agnews.py)), this repo includes a **second** single-label task on the Hub **[`emotion`](https://huggingface.co/datasets/emotion)** (English short text, 6 classes: sadness, joy, love, anger, fear, surprise). It uses the **same** training code path; only dataset id, eval split, and label names are preset.

| Entry point | Dataset | Eval split (default) |
| ----------- | ------- | -------------------- |
| [`scripts/train_tinymodel1_agnews.py`](https://github.com/HyperlinksSpace/TinyModel/blob/main/scripts/train_tinymodel1_agnews.py) | `fancyzhx/ag_news` | `test` |
| [`scripts/train_tinymodel1_emotion.py`](https://github.com/HyperlinksSpace/TinyModel/blob/main/scripts/train_tinymodel1_emotion.py) | `emotion` | `validation` |
| [`scripts/train_tinymodel1_sst2.py`](https://github.com/HyperlinksSpace/TinyModel/blob/main/scripts/train_tinymodel1_sst2.py) | `glue` (`sst2`) | `validation` |

**Equivalent explicit CLI** (if you prefer not to use the wrapper):

```bash
python scripts/train_tinymodel1_classifier.py \
  --dataset emotion \
  --eval-split validation \
  --labels sadness,joy,love,anger,fear,surprise \
  --output-dir .tmp/TinyModel-emotion
```

**Instant smoke test** (small samples, ~1 minute on CPU; needs network to download `emotion` once):

```bash
python scripts/train_tinymodel1_emotion.py \
  --output-dir artifacts/emotion-smoke \
  --max-train-samples 200 \
  --max-eval-samples 100 \
  --epochs 1 \
  --batch-size 8 \
  --seed 42
```

Then check `artifacts/emotion-smoke/eval_report.json` — `reproducibility.dataset` should be `emotion` and `label_order` should list the six emotion names. For other Hub datasets, pass `--dataset`, splits, and optional `--labels` / `--text-column` to [`train_tinymodel1_classifier.py`](https://github.com/HyperlinksSpace/TinyModel/blob/main/scripts/train_tinymodel1_classifier.py) directly.

### Embeddings smoke test (routing / search-shaped)

[`scripts/embeddings_smoke_test.py`](https://github.com/HyperlinksSpace/TinyModel/blob/main/scripts/embeddings_smoke_test.py) runs [`TinyModelRuntime`](https://github.com/HyperlinksSpace/TinyModel/blob/main/scripts/tinymodel_runtime.py) on a few queries: **classification probabilities**, **pairwise similarity**, and **retrieval** over a toy candidate list (support/triage scenario).

**What these terms mean**

- **Classification probabilities** — Output of `TinyModelRuntime.classify(...)`: for each input text, the model returns a probability distribution across all labels (values sum to ~1.0). Use this for routing decisions and confidence-aware thresholds.
- **Pairwise similarity** — Output of `TinyModelRuntime.similarity(text_a, text_b)`: cosine similarity between two sentence embeddings (from the encoder). Higher values mean semantically closer text under this model.
- **Retrieval** — Output of `TinyModelRuntime.retrieve(query, candidates, top_k=...)`: ranks candidate texts by embedding similarity to a query and returns top matches with scores and indices.

**Instant test** (needs a checkpoint — train the tiny eval run first, or pass a Hub id):

```bash
python scripts/train_tinymodel1_classifier.py \
  --output-dir artifacts/eval-smoke --max-train-samples 120 --max-eval-samples 80 \
  --epochs 1 --batch-size 8 --seed 42
python scripts/embeddings_smoke_test.py --model artifacts/eval-smoke
# Or: python scripts/embeddings_smoke_test.py --model HyperlinksSpace/TinyModel1
```

### Pretrained encoder fine-tune (compare to scratch baseline)

[`scripts/finetune_pretrained_classifier.py`](https://github.com/HyperlinksSpace/TinyModel/blob/main/scripts/finetune_pretrained_classifier.py) fine-tunes **`AutoModelForSequenceClassification`** from `--base-model` (default `distilbert-base-uncased`) using the **same** splits and metrics as the scratch trainer. Use matching `--seed` and sample caps, then compare `eval_report.json` / `artifact.json` to a scratch run.

**Instant test** (downloads base weights once; CPU-friendly small run):

```bash
python scripts/finetune_pretrained_classifier.py \
  --output-dir artifacts/finetune-smoke \
  --base-model distilbert-base-uncased \
  --max-train-samples 400 --max-eval-samples 200 \
  --epochs 1 --batch-size 8 --seed 42
```

### Custom labels and data hygiene

For proprietary or weakly labeled data: use a short **label guide**, **versioned snapshots**, and **leakage-safe splits**. See [`texts/labeling-and-data-hygiene.md`](texts/labeling-and-data-hygiene.md).

### Current implementation status (what, why, how to run)

This section summarizes the currently implemented components and their practical purpose.

| Part | What it is for | How to launch | What to verify |
| ---- | ---- | ---- | ---- |
| **Scratch baseline training** (`scripts/train_tinymodel1_classifier.py`) | Build a small from-scratch text classifier baseline and export all model artifacts. | `python scripts/train_tinymodel1_classifier.py --output-dir artifacts/eval-smoke --max-train-samples 120 --max-eval-samples 80 --epochs 1 --batch-size 8 --seed 42` | `artifacts/eval-smoke/eval_report.json` exists and includes `accuracy`, `macro_f1`, `per_class_f1`, `confusion_matrix`. |
| **Second dataset path** (`scripts/train_tinymodel1_emotion.py`) | Prove the same pipeline works on another Hub dataset without forking core training code. | `python scripts/train_tinymodel1_emotion.py --output-dir artifacts/emotion-smoke --max-train-samples 200 --max-eval-samples 100 --epochs 1 --batch-size 8 --seed 42` | `reproducibility.dataset == "emotion"` and 6 labels in `label_order`. |
| **Embeddings/runtime smoke** (`scripts/embeddings_smoke_test.py`) | Validate product-shaped runtime behavior: classify, similarity, retrieval. | `python scripts/embeddings_smoke_test.py --model artifacts/eval-smoke` (or `--model HyperlinksSpace/TinyModel1`) | Script prints all 3 blocks and ends with `Embeddings smoke test completed.` |
| **Pretrained fine-tune path** (`scripts/finetune_pretrained_classifier.py`) | Compare a pretrained encoder baseline (DistilBERT/BERT-family) against scratch training using same eval reporting format. | `python scripts/finetune_pretrained_classifier.py --output-dir artifacts/finetune-smoke --base-model distilbert-base-uncased --max-train-samples 400 --max-eval-samples 200 --epochs 1 --batch-size 8 --seed 42` | `artifacts/finetune-smoke/eval_report.json` + `artifact.json` exist; compare metrics to scratch run on same caps/seed. |
| **Data hygiene guide** (`texts/labeling-and-data-hygiene.md`) | Lightweight rules for label quality, versioning, and leakage prevention when moving to custom/proprietary data. | Read the file and apply before collecting custom labels. | Label guide versioning and split hygiene rules are defined before annotation scale-up. |
| **Kaggle→HF training workflow hardening** (`.github/workflows/train-via-kaggle-to-hf.yml`) | Make CI training/publish flow robust: stable auth handling, unique kernel slugs, resilient status polling, and clearer diagnostics. | Trigger workflow from GitHub Actions with `version`, `namespace`, train hyperparameters. | Workflow reaches model publish step and uploads `{namespace}/TinyModel{version}`. |
| **Phase 3: ONNX, bench, API** (`scripts/phase3_*.py`, `texts/phase3-serving-profile.md`) | Export to ONNX, verify parity, CPU latency report, reference HTTP API. | Install **once** (`pip install -r optional-requirements-phase3.txt`); **then** in separate shell commands, run `python scripts/phase3_export_onnx.py --model <dir>`, `python scripts/phase3_onnx_parity.py`, `python scripts/phase3_benchmark.py` (see **Phase 3** section). Never append `then python` to the same line as `pip install`. | `onnx/*.onnx` present; benchmark under `artifacts/phase3/reports/`; parity exits 0. |

## 2) Using the Hub model and Space

Load the published model by id (no local files required):

```bash
python -c "from transformers import pipeline; p=pipeline('text-classification', model='HyperlinksSpace/TinyModel1', tokenizer='HyperlinksSpace/TinyModel1'); print(p('Stocks rallied after central bank comments', top_k=None))"
```

Use the general-purpose runtime helpers (classification + embeddings + semantic search):

```python
from scripts.tinymodel_runtime import TinyModelRuntime

rt = TinyModelRuntime("HyperlinksSpace/TinyModel1")

# 1) Classification
print(rt.classify(["Oil prices fell after a demand forecast update."])[0])

# 2) Embeddings (shape: [batch, hidden_size])
emb = rt.embed(
    [
        "The team won the cup final in extra time.",
        "Central bank policy affected bond yields.",
    ]
)
print(emb.shape)

# 3) Pairwise semantic similarity
score = rt.similarity(
    "Stocks rose after inflation cooled.",
    "Markets rallied as price growth slowed.",
)
print("similarity:", round(score, 4))

# 4) Retrieval: nearest texts to a query
hits = rt.retrieve(
    "Chipmaker launches a new AI processor.",
    [
        "Parliament debated tax policy in the capital.",
        "Semiconductor company unveils next-gen accelerator.",
        "Team signs striker before the derby.",
    ],
    top_k=2,
)
for h in hits:
    print(h.index, round(h.score, 4), h.text)
```

### TinyModelRuntime function outputs

| Function | Return type | Output values |
| ---- | ---- | ---- |
| `classify(texts)` | `list[dict[str, float]]` | One dict per input text. Keys are label names from `model.config.id2label`; values are probabilities in `[0, 1]` that sum to ~1.0 for each text. |
| `embed(texts, normalize=True)` | `torch.Tensor` | Shape `[batch_size, hidden_size]` (default TinyModel hidden size is `128`). If `normalize=True`, each row is L2-normalized (vector norm ~1.0). |
| `similarity(text_a, text_b)` | `float` | Cosine similarity between the two embeddings. Typical range is `[-1, 1]`: higher means more semantically similar under this model. |
| `retrieve(query, candidates, top_k=3)` | `list[RetrievalHit]` | Ranked top matches. Each item has: `index` (position in `candidates`), `text` (candidate string), `score` (cosine similarity; higher is closer). Length is `min(top_k, len(candidates))`. |

Or open the demo: [direct app](https://hyperlinksspace-tinymodel1space.hf.space) · [on the Hub](https://huggingface.co/spaces/HyperlinksSpace/TinyModel1Space).

Quick checks:

- Space loads; inference returns labels and scores; no errors in Space logs.

## 3) GitHub Actions workflows

Workflow definitions live under [`.github/workflows/`](https://github.com/HyperlinksSpace/TinyModel/tree/main/.github/workflows). Trigger them from **Actions →** select the workflow → **Run workflow**. Runners use **`ubuntu-latest`** unless you change the workflow.

### Repository secrets (Settings → Secrets and variables → Actions)

Configure these once per repository (or organization). They are **not** committed to git.

| Secret | Used by | Purpose |
| ------ | ------- | ------- |
| **`HF_TOKEN`** | Workflows below | Hugging Face [access token](https://huggingface.co/settings/tokens) with **write** permission to create/update models and Spaces in the target namespace. |
| **`KAGGLE_USERNAME`** | [`train-via-kaggle-to-hf.yml`](https://github.com/HyperlinksSpace/TinyModel/blob/main/.github/workflows/train-via-kaggle-to-hf.yml) only | Your Kaggle username (same value as in Kaggle **Account** → API). |
| **`KAGGLE_KEY`** | [`train-via-kaggle-to-hf.yml`](https://github.com/HyperlinksSpace/TinyModel/blob/main/.github/workflows/train-via-kaggle-to-hf.yml) only | Kaggle API key from **Account** → **Create New API Token**. |

No other GitHub secrets are read by these workflows. Internal step outputs (`GITHUB_ENV`) such as `KAGGLE_OWNER` / `KAGGLE_KERNEL_SLUG` are set automatically during the Kaggle run.

### Core flows (validated on the GitHub Actions free tier)

| Workflow | File |
| -------- | ---- |
| **PR smoke: Phase 1 matrix** (scratch, small caps) | [`phase1-smoke.yml`](https://github.com/HyperlinksSpace/TinyModel/blob/main/.github/workflows/phase1-smoke.yml) |
| **PR smoke: Phase 3** (train tiny → ONNX → parity → bench) | [`phase3-smoke.yml`](https://github.com/HyperlinksSpace/TinyModel/blob/main/.github/workflows/phase3-smoke.yml) |
| **Deploy versioned Space to Hugging Face** | [`deploy-hf-space-versioned.yml`](https://github.com/HyperlinksSpace/TinyModel/blob/main/.github/workflows/deploy-hf-space-versioned.yml) |
| **Train on Hugging Face Jobs and publish versioned model** | [`train-hf-job-versioned.yml`](https://github.com/HyperlinksSpace/TinyModel/blob/main/.github/workflows/train-hf-job-versioned.yml) |

- **[`deploy-hf-space-versioned.yml`](https://github.com/HyperlinksSpace/TinyModel/blob/main/.github/workflows/deploy-hf-space-versioned.yml)** — Builds the Gradio Space with `scripts/build_space_artifact.py` and uploads **`{namespace}/TinyModel{version}Space`**.  
  - **Secrets:** `HF_TOKEN`.  
  - **Workflow inputs:** `version`, `namespace`, `model_id` (for example `HyperlinksSpace/TinyModel1`).

- **[`train-hf-job-versioned.yml`](https://github.com/HyperlinksSpace/TinyModel/blob/main/.github/workflows/train-hf-job-versioned.yml)** — Submits training on **Hugging Face Jobs**, then publishes **`{namespace}/TinyModel{version}`**.  
  - **Secrets:** `HF_TOKEN` (also passed into the remote job so it can run `publish_hf_artifact.py`).  
  - **Workflow inputs:** `version`, `namespace`, optional `commit_sha` (empty = current workflow SHA), `flavor`, `timeout`, `max_train_samples`, `max_eval_samples`, `epochs`, `batch_size`, `learning_rate`.  
  - If Hugging Face returns **402 Payment Required** for Jobs, add billing/credits on your HF account or train locally and publish with `scripts/publish_hf_artifact.py` (see `texts/HUGGING_FACE_DEPLOYMENT_INTERNAL.md`).

### Optional: train via Kaggle

| Workflow | File |
| -------- | ---- |
| **Train via Kaggle and publish to Hugging Face** | [`train-via-kaggle-to-hf.yml`](https://github.com/HyperlinksSpace/TinyModel/blob/main/.github/workflows/train-via-kaggle-to-hf.yml) |

- **[`train-via-kaggle-to-hf.yml`](https://github.com/HyperlinksSpace/TinyModel/blob/main/.github/workflows/train-via-kaggle-to-hf.yml)** — Creates a Kaggle kernel run, trains, downloads outputs, and pushes **`{namespace}/TinyModel{version}`** to the Hub.  
  - **Secrets:** `KAGGLE_USERNAME`, `KAGGLE_KEY`, and **`HF_TOKEN`** (for upload to Hugging Face).  
  - **Workflow inputs:** `version`, `namespace`, `max_train_samples`, `max_eval_samples`, `epochs`, `batch_size`, `learning_rate`.  
  - **External quota:** Kaggle GPU/CPU weekly limits and any **Kaggle compute credits** your account uses; not covered by GitHub Actions alone.

## 4) Further development

Illustrative directions for evolving the TinyModel line (pick what matches your product goals):

- **Accuracy and capacity** — Train on more AG News samples or epochs; adjust the tiny BERT config (depth, width, sequence length); add LR schedules, warmup, or regularization suited to your budget.
- **Domains and label sets** — Fine-tune on proprietary or niche corpora; replace the four AG News classes with your own taxonomy and a labeled dataset.
- **Shipping inference** — Document ONNX or quantized exports for edge and serverless; add batch-inference examples; optionally wire a Hugging Face Inference Endpoint for a stable HTTP API.
- **Space and API UX** — Batch inputs, per-class thresholds, richer examples, or client snippets (Python and JavaScript) for integrators.
- **Evaluation discipline** — Fixed test split, confusion matrix, calibration, and versioned eval reports alongside `artifact.json`.
- **Repository hygiene** — Lightweight CI (lint, script smoke tests) that never pulls large weights; optional Hub Collections or docs that link model, Space, and release notes.

Nothing here is committed on a fixed timeline; treat it as a backlog of sensible next steps for a small text understanding stack.

## 5) Further development plan: what was added and how to exit-check

The living plan is in [`texts/further-development-plan.md`](texts/further-development-plan.md). Recent updates there:

- **Exit steps (verification)** for **Phase 1–3**, **optional R&D**, and each **decision gate** (concrete commands, **exit status 0**, artifacts).
- **Phase 2 routing:** [`texts/phase2-routing-threshold-scenario.md`](texts/phase2-routing-threshold-scenario.md).
- **Phase 3 (done in repo):** ONNX export, parity, CPU benchmark, reference API, serving doc — see **Phase 3** in this `README` and `texts/phase3-serving-profile.md`. CI: `.github/workflows/phase3-smoke.yml`.
- **Optional R&D** backlog: [`texts/optional-rd-backlog.md`](texts/optional-rd-backlog.md).
- **Plan status** and **What is left (if any)** at the end of the plan file (mostly optional follow-ups).

**Quick Phase 1 exit check (local, matches CI):**

```bash
python scripts/phase1_compare.py \
  --preset smoke \
  --models scratch \
  --datasets ag_news,emotion \
  --seed 42
echo $?
# Expect: 0; reports under artifacts/phase1/reports/phase1_smoke_seed42.*
```

For the up-to-date list of optional or future work, see **“What is left (if any)”** at the end of the same plan file.
