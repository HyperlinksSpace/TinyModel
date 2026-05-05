# Horizon 2: generative core (local open LLM)

Implements the **Generative core** line from [`further-development-universe-brain.md`](further-development-universe-brain.md): go beyond “predict a label” to **text generation** (summaries, rewrites) with a **versioned JSON run artifact** (latency, token counts) so you can compare models and plan cost tiers.

| Piece | File | Role |
| ----- | ---- | ---- |
| **Core** | `scripts/horizon2_core.py` | Load causal LM, prompts for `summarize` / `reformulate` / `grounded`, generate, JSON structure. |
| **CLI** | `scripts/horizon2_generative.py` | Batch runs, `--verify` smoke, optional `--compare-with` for side-by-side in one file. |
| **API** | `scripts/horizon2_server.py` | FastAPI `POST /v1/generate` (needs Phase 3–style optional `fastapi` / `uvicorn`). |
| **Deps** | `optional-requirements-horizon2.txt` | `transformers` + `accelerate`; `torch` comes from your main environment. |

## Install

```bash
pip install -r optional-requirements-horizon2.txt
# optional HTTP server in addition:
pip install -r optional-requirements-phase3.txt
```

## Quick verification (no quality bar; wiring only)

```bash
python scripts/horizon2_generative.py --verify
```

**Expect:** exit code **0** and a file under `.tmp/horizon2-verify/horizon2_run.json` (gitignored) with `samples[0].output` non-empty. Uses the tiny public weights `sshleifer/tiny-gpt2` (first run downloads from the Hub; needs network unless cached).

## Manual tests that matter (quality + JSON contract)

**Shell:** Every example must be pasted as a **full** line starting with `python`. Do not paste a fragment like `--task grounded ...` by itself. In Bash, `python scripts/... --context-file <file.md>` is also wrong: `<` is **input redirection**, not “placeholder.” Use a real path, e.g. `--context-file texts/rag_faq_corpus.md`.

1. **Smokey quality check (still small, CPU-OK, ~360M instruct)**

   ```bash
   export HORIZON2_MODEL=HuggingFaceTB/SmolLM2-360M-Instruct
   # Windows: set HORIZON2_MODEL=HuggingFaceTB/SmolLM2-360M-Instruct
   python scripts/horizon2_generative.py --task reformulate --max-new-tokens 96
   ```

   **Expect:** `Wrote` message pointing at `.tmp/horizon2/last_run.json`; read `samples[].seconds` and `output`.

2. **RAG + LLM (grounded answer using Horizon 1 style context)**

   ```bash
   python scripts/horizon2_generative.py --task grounded \
     --text "How do refunds work?" \
     --context-file texts/rag_faq_corpus.md
   ```

   **Note:** the corpus file contains multiple `##` sections; for a tight test, create a one-paragraph `context` file. **Expect:** JSON with answers that do not invent facts *when* the model follows instructions (bigger Instruct models behave better than `--smoke`).

3. **Side-by-side (two model ids, same inputs)**

   ```bash
   python scripts/horizon2_generative.py --smoke --compare-with gpt2
   ```

   **Expect:** `side_by_side` in the output JSON (second model must load on the same `--device`).

4. **HTTP server** (in one terminal; load a small model for smoke)

   ```bash
   python scripts/horizon2_server.py --smoke --port 8766
   ```

   **Note:** `GET /` returns a small JSON map of routes (so the root is not a 404). **Interactive API:** open **http://127.0.0.1:8766/docs** in the browser to try `POST /v1/generate`. `GET /healthz` is the minimal liveness check: `curl -s http://127.0.0.1:8766/healthz`.

   In another terminal:

   ```bash
   curl -s -X POST http://127.0.0.1:8766/v1/generate -H "Content-Type: application/json" \
     -d "{\"task\":\"summarize\",\"text\":\"Short news here about markets.\"}" | head
   ```

## Tiers and expectations (rough)

| Tier | When | Notes |
| ---- | ---- | ----- |
| **Smoke** | `--smoke` or `--verify` | `sshleifer/tiny-gpt2`; proves pipeline; not for demos. |
| **Local Instruct (default env)** | `HORIZON2_MODEL=…SmolLM2-360M-Instruct` | Reasonable on CPU for short replies; faster on GPU. |
| **Larger / API** | Bigger open weights or hosted API | Not bundled here; use the same JSON fields from your own adapter; keep the **logging contract** (latency + tokens) consistent. |

## How this links to other horizons

- **Horizon 1** retrieval (`rag_faq_smoke`, FAQ corpus) supplies **context**; Horizon 2 answers or rewrites in a **grounded** task.
- **Phase 3** reference server is the pattern for the HTTP shape; Horizon 2 adds **`/v1/generate`**.

## Improving perceived quality

If generations are **too long**, **slow**, or **mis-routed** in **Universal Brain** / Space, read [`model-output-improvement-guide.md`](model-output-improvement-guide.md) (symptom table + **`--task-max-new-tokens`**, `build_user_prompt`, router flags) and the encoder/RAG angles in [`horizon1-short-term-handbook.md`](horizon1-short-term-handbook.md).

## CI

`horizon2-smoke.yml` runs `--verify` on the default branch when GitHub can reach the Hub. If the workflow fails with timeouts, re-run or rely on the local `--verify` command with a cached `tiny-gpt2`.
