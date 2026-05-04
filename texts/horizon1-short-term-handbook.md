# Horizon 1 (short term): what was added and how to run it

This supports block **A–C** in [`further-development-universe-brain.md`](further-development-universe-brain.md): baseline closure, three-dataset eval breadth, and a minimal RAG-style retrieval path.

## What was added (scripts and files)

| Piece | File | Role |
| ----- | ---- | ---- |
| **A — verify** | `scripts/horizon1_verify_short_term_a.py` | One command: Phase 1 smoke + fresh AG News train (Phase 2 eval) + Phase 3 ONNX export, parity, benchmark; prints **`routing_policy.py --from-checkpoint`** for **`.tmp/horizon1-verify-a`** after Phase 2 keys pass. |
| **B — three tasks** | `scripts/horizon1_three_datasets.py` | Trains **AG News**, **Emotion**, **SST-2** with the same sample caps; writes [`horizon1-three-tasks-summary.md`](horizon1-three-tasks-summary.md) (with **Phase 2 `routing` quick check** footer) + `artifacts/horizon1/three-tasks-summary.json`; prints a **`routing_policy`** **Tip:** line after the summary. |
| **C — RAG smoke** | `scripts/rag_faq_smoke.py` + [`rag_faq_corpus.md`](rag_faq_corpus.md) | FAQ chunks + **hybrid** (lexical + encoder) retrieval and cheap “citation” checks; optional **`--show-train-routing`** (same **`eval_report_routing`** banner as glue / encoder smoke). |
| **C — route→RAG glue** | `scripts/horizon1_route_then_retrieve.py` | Same corpus/ranker; runs **`TinyModelRuntime.classify` → `route_from_probs`**, and on **fallback** runs hybrid retrieval (product-shaped triage path). |
| **C″ — encoder smoke + gates** | `scripts/embeddings_smoke_test.py` + `scripts/eval_report_routing.py` | **`--routing`** prints **`RoutingDecision`** next to classifier top‑k; **`--show-train-routing`** prints **`eval_report.json`** **`routing`** (same helper as **`horizon1_route_then_retrieve`**). |
| **Summary** | [`horizon1-three-tasks-summary.md`](horizon1-three-tasks-summary.md) | Table of `accuracy` / `macro_f1` per task (regenerated when you re-run B). |

Weights for B live under `artifacts/horizon1/three-tasks/` (see `.gitignore`); the **summary markdown** in `texts/` is the portable artifact to commit.

## How to test manually (success = exit code 0)

**Prereqs:** `pip install` the usual training stack; for Phase 3 in **A** also run `pip install -r optional-requirements-phase3.txt` **as its own command** (see below). On Windows, UTF-8 for ONNX logs is set inside the verify script.

**Common mistake:** do **not** paste `pip install -r optional-requirements-phase3.txt then python ...` as one line — `pip` will try to install a package named `then` and your script path. Use **two lines**, or one line with `&&` between the commands.

### A — end-to-end tactical stack

Full run (needs Phase 3 optional deps installed first):

```bash
pip install -r optional-requirements-phase3.txt
python scripts/horizon1_verify_short_term_a.py
```

Faster check without ONNX (no Phase 3 file needed):

```bash
python scripts/horizon1_verify_short_term_a.py --skip-phase3
```

**Expect:** last line `horizon1_verify_short_term_a: OK …` and, under `artifacts/phase3/reports/`, `benchmark_horizon1-verify-a.md` when Phase 3 runs. After Phase 2 keys are validated on **`.tmp/horizon1-verify-a`**, the script prints a copy-paste **`routing_policy.py --from-checkpoint …`** line (same JSON as **`eval_report.json`** → **`routing`**).

### B — three datasets (needs Hub data cached or network)

If `huggingface.co` times out, use offline cache only:

```bash
# Windows (cmd):  set HF_DATASETS_OFFLINE=1
# Git Bash:        export HF_DATASETS_OFFLINE=1
python scripts/horizon1_three_datasets.py --offline-datasets
```

**Expect:** `texts/horizon1-three-tasks-summary.md` updated (table + per-task paths + **`routing_policy.py --from-checkpoint`** example for **ag_news**); per-task `eval_report.json` with Phase 2 sections. Console ends with the same **`Tip:`** line as the summary footer.

### C — RAG smoke (after B, or any trained checkpoint)

```bash
python scripts/rag_faq_smoke.py
# or set the checkpoint explicitly:
python scripts/rag_faq_smoke.py --model artifacts/horizon1/three-tasks/ag_news
```

With no `--model`, the script picks the first default local dir that has `config.json` (e.g. `artifacts/horizon1/three-tasks/ag_news` after B), otherwise loads **`HyperlinksSpace/TinyModel1`** from the Hub (needs network once).

**Expect:** all three sample queries `ok` (hybrid ranker). Use `--semantic-only` to stress **pure** embedding retrieval (may fail on tiny encoders). Add **`--show-train-routing`** to print **`eval_report.json`** **`routing`** before the smoke lines (local checkpoints with Phase 2 reports only).

### C′ — classify, then retrieve only if policy abstains

```bash
python scripts/horizon1_route_then_retrieve.py --demo
python scripts/horizon1_route_then_retrieve.py --query "How do I reset my password?"
python scripts/horizon1_route_then_retrieve.py --verify
# Optional: print Phase 2 `routing` notes from eval_report.json next to live decisions:
python scripts/horizon1_route_then_retrieve.py --demo --show-train-routing --model artifacts/phase1/runs/smoke/ag_news/scratch
```

**Expect:** `--demo` prints news vs. FAQ-style examples with routing lines; `--verify` exits 0 if forced-fallback RAG matches the same cheap gates as `rag_faq_smoke`, and a sports headline is **accepted** when thresholds are set to zero inside the check. **`--show-train-routing`** only applies to **`--demo`** / **`--query`** (local dirs with **`eval_report.json`**); **`--json`** includes **`train_routing`** when present.

### C″ — embeddings smoke with routing lines (no FAQ file)

After any AG News–style checkpoint exists (Phase 1 smoke, three-tasks AG News, or `.tmp/phase3-smoke`):

```bash
python scripts/embeddings_smoke_test.py \
  --model artifacts/phase1/runs/smoke/ag_news/scratch \
  --routing
# Optional: Phase 2 training notes before the smoke output (needs `routing` in eval_report.json):
python scripts/embeddings_smoke_test.py \
  --model artifacts/phase1/runs/smoke/ag_news/scratch \
  --routing --show-train-routing
```

Optional: **`--min-confidence`** / **`--min-margin`** match your production gates.

**Expect:** each sample query prints **`routing_policy: RoutingDecision(...)`** after **`top labels`**; retrieval section unchanged (synthetic candidate strings).

**Routing CLI:** `python scripts/routing_policy.py --from-checkpoint <trained_dir>` prints the **`routing`** block from that directory’s **`eval_report.json`** (same helper as **`eval_report_routing.py`**; no forward pass).

## How you benefit

- **A:** Proves the same path CI uses works on your machine (matrices, Phase 2 eval, ONNX, bench).
- **B:** One table to compare **topic**, **emotion**, and **sentiment** tasks under identical training caps—good for “should we invest in more data or capacity?”
- **C:** A **template** for support/FAQ products: chunk corpus → embed with **your** `TinyModelRuntime` → rank; extend with a real vector DB or cross-encoder later.

## CI note

`phase1-smoke.yml` and `phase3-smoke.yml` on GitHub mirror parts of **A**; B is not in CI by default (longer, three dataset downloads). Run B locally or in a release workflow when needed.

`phase1-smoke.yml` runs **`horizon1_route_then_retrieve.py --verify`** and **`routing_policy.py --from-checkpoint`** on **`artifacts/phase1/runs/smoke/ag_news/scratch`** after the Phase 1 matrix (lightweight PR coverage).

`phase3-smoke.yml` runs the same pair against **`.tmp/phase3-smoke`** after its tiny train so the **C′** glue path and **Phase 2 `routing`** dump are covered on the ONNX workflow (no Hub download).

If **`routing_policy.py --from-checkpoint`** fails locally on an old **`artifacts/phase1/runs/...`** tree, re-run the smoke matrix so **`eval_report.json`** picks up the current Phase 2 **`routing`** block (same fix CI expects).
