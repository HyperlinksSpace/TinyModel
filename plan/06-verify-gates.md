# Verify gates (run before shipping)

All commands from **TinyModel repo root** unless noted.

---

## Stdlib (no torch) — every PR

```bash
python scripts/hsp_integration_smoke.py --verify
```

Runs: corpus, lexical RAG, Phase 3 contract, corpus export, meta contract, screen context, reference client, `ub_eval_runner`.

**CI:** included via `tests/test_hsp_integration_smoke.py` in `stdlib-unittest`.

---

## Full HSP stack (torch + live HTTP)

```bash
python scripts/hsp_integration_smoke.py --verify --full
```

Adds: hybrid RAG, route-then-retrieve glue, live `phase3_reference_server` subprocess smoke.

**CI:** `phase3-smoke.yml` runs individual HSP steps after tiny train.

---

## Individual gates (debug)

| Gate | Command |
| ---- | ------- |
| Corpus chunks | `python scripts/hsp_corpus_smoke.py --verify` |
| Lexical RAG | `python scripts/hsp_rag_smoke.py --verify` |
| Hybrid RAG | `python scripts/hsp_rag_hybrid_smoke.py --verify` |
| Route → retrieve | `python scripts/hsp_route_then_retrieve.py --verify` |
| API JSON contract | `python scripts/hsp_phase3_contract_smoke.py --verify` |
| Live HTTP server | `python scripts/hsp_phase3_server_smoke.py --verify` |
| Screen context | `python scripts/hsp_screen_context_smoke.py --verify` |
| meta.tinymodel | `python scripts/hsp_meta_contract_smoke.py --verify` |
| TS reference files | `python scripts/hsp_reference_client_smoke.py --verify` |
| HSP intents golden | `python scripts/ub_eval_runner.py --verify` |
| Corpus JSON export | `python scripts/hsp_corpus_export.py --verify` |

---

## HSP staging (manual, when wired)

| Check | How |
| ----- | --- |
| Sidecar health | `curl $TINYMODEL_API_URL/healthz` |
| Plan navigate | `curl -X POST $TINYMODEL_API_URL/v1/plan -H 'Content-Type: application/json' -d '{"text":"open swap page"}'` |
| HSP meta | `/api/ai` response includes `meta.tinymodel` |
| Stream | `/api/ai/stream` returns tokens |
| Action | “open swap” navigates in app |

---

## Phase exit matrix

| Phase | Required green |
| ----- | -------------- |
| 0 | `hsp_integration_smoke.py --verify` |
| 1 | above + `--full` + staging `healthz` |
| 2 | staging hybrid flows (swap+explain, shield explain) |
| 3 | manual UI script + golden intents |
| 4 | UB eval on summarize/reformulate subset |

---

## Artifacts

Smoke runs write JSON under `.tmp/`:

- `hsp-integration-smoke/run.json`
- `hsp-phase3-server-smoke/run.json`
- `artifacts/hsp/hsp_program_corpus.json` (after export)

Do not commit `.tmp/`; export corpus is gitignored (regenerate in CI).
