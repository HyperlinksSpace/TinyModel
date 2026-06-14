# Golden prompts (Universal Brain evaluation corpus)

Versioned test prompts for [`scripts/ub_eval_runner.py`](../../scripts/ub_eval_runner.py). Regenerate with:

```bash
python scripts/seed_golden_prompts.py
```

## Files

| File | Rows | Scored in `--verify`? |
| ---- | ---- | --------------------- |
| `nl_signals.jsonl` | 100 | **Yes** — embedded `prompt_signals` detection |
| `routing.jsonl` | 100 | Only with `--with-router` (needs torch + LM) |
| `hsp_intents.jsonl` | 100 | **Yes** — HSP shell route hints (`scripts/hsp_intent_router.py`) |
| `e2e.jsonl` | 100 | **No** — manual / future LLM-judge rubric |
| `manifest.json` | — | Schema + counts |

## JSONL fields

**nl_signals**

```json
{"id": "nl_001", "suite": "nl_signals", "prompt": "...", "expect_tags": ["comparison_frame=pros_cons"]}
```

**routing**

```json
{"id": "route_001", "suite": "routing", "prompt": "...", "expect_intent": "summarize"}
```

**hsp_intents**

```json
{"id": "hsp_001", "suite": "hsp_intents", "prompt": "open swap page", "expect_route": "navigate:/swap"}
```

Use `null` for `expect_route` when the prompt should not trigger navigation (general chat / token_info phrasing).

**e2e**

```json
{"id": "e2e_001", "suite": "e2e", "prompt": "...", "expect_intent": "chat", "note": "..."}
```

## Quick run

```bash
# CI-friendly (stdlib only)
python scripts/ub_eval_runner.py --verify

# Sample NL suite
python scripts/ub_eval_runner.py --suite nl_signals --limit 20

# HSP intent suite (stdlib)
python scripts/ub_eval_runner.py --suite hsp_intents --limit 20

# Routing with tiny model (slow; needs optional-requirements-horizon2.txt + torch)
python scripts/ub_eval_runner.py --suite routing --with-router --smoke --limit 10
```

Target pass rate: **≥95%** on scored cases (override with `--min-pass-rate`).

See also [`universal-brain-forward-plan-self-development.md`](../universal-brain-forward-plan-self-development.md) §9.
