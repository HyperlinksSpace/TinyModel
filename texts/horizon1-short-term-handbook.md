# Horizon 1 (short term): what was added and how to run it

This supports block **A–C** in [`further-development-universe-brain.md`](further-development-universe-brain.md): baseline closure, three-dataset eval breadth, and a minimal RAG-style retrieval path.

## What was added (scripts and files)

| Piece | File | Role |
| ----- | ---- | ---- |
| **A — verify** | `scripts/horizon1_verify_short_term_a.py` | One command: Phase 1 smoke + fresh AG News train (Phase 2 eval) + Phase 3 ONNX export, parity, benchmark. |
| **B — three tasks** | `scripts/horizon1_three_datasets.py` | Trains **AG News**, **Emotion**, **SST-2** with the same sample caps; writes [`horizon1-three-tasks-summary.md`](horizon1-three-tasks-summary.md) + `artifacts/horizon1/three-tasks-summary.json`. |
| **C — RAG smoke** | `scripts/rag_faq_smoke.py` + [`rag_faq_corpus.md`](rag_faq_corpus.md) | FAQ chunks + **hybrid** (lexical + encoder) retrieval and cheap “citation” checks. |
| **C — route→RAG glue** | `scripts/horizon1_route_then_retrieve.py` | Same corpus/ranker; runs **`TinyModelRuntime.classify` → `route_from_probs`**, and on **fallback** runs hybrid retrieval (product-shaped triage path). |
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

**Expect:** last line `horizon1_verify_short_term_a: OK …` and, under `artifacts/phase3/reports/`, `benchmark_horizon1-verify-a.md` when Phase 3 runs.

### B — three datasets (needs Hub data cached or network)

If `huggingface.co` times out, use offline cache only:

```bash
# Windows (cmd):  set HF_DATASETS_OFFLINE=1
# Git Bash:        export HF_DATASETS_OFFLINE=1
python scripts/horizon1_three_datasets.py --offline-datasets
```

**Expect:** `texts/horizon1-three-tasks-summary.md` updated; per-task `eval_report.json` with Phase 2 sections.

### C — RAG smoke (after B, or any trained checkpoint)

```bash
python scripts/rag_faq_smoke.py
# or set the checkpoint explicitly:
python scripts/rag_faq_smoke.py --model artifacts/horizon1/three-tasks/ag_news
```

With no `--model`, the script picks the first default local dir that has `config.json` (e.g. `artifacts/horizon1/three-tasks/ag_news` after B), otherwise loads **`HyperlinksSpace/TinyModel1`** from the Hub (needs network once).

**Expect:** all three sample queries `ok` (hybrid ranker). Use `--semantic-only` to stress **pure** embedding retrieval (may fail on tiny encoders).

### C′ — classify, then retrieve only if policy abstains

```bash
python scripts/horizon1_route_then_retrieve.py --demo
python scripts/horizon1_route_then_retrieve.py --query "How do I reset my password?"
python scripts/horizon1_route_then_retrieve.py --verify
```

**Expect:** `--demo` prints news vs. FAQ-style examples with routing lines; `--verify` exits 0 if forced-fallback RAG matches the same cheap gates as `rag_faq_smoke`, and a sports headline is **accepted** when thresholds are set to zero inside the check.

## How you benefit

- **A:** Proves the same path CI uses works on your machine (matrices, Phase 2 eval, ONNX, bench).
- **B:** One table to compare **topic**, **emotion**, and **sentiment** tasks under identical training caps—good for “should we invest in more data or capacity?”
- **C:** A **template** for support/FAQ products: chunk corpus → embed with **your** `TinyModelRuntime` → rank; extend with a real vector DB or cross-encoder later.

## CI note

`phase1-smoke.yml` and `phase3-smoke.yml` on GitHub mirror parts of **A**; B is not in CI by default (longer, three dataset downloads). Run B locally or in a release workflow when needed.
