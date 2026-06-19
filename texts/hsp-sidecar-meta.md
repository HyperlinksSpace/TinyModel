# HSP sidecar `meta.tinymodel` contract (Phase 2 prep)

When Hyperlinks Space Program wires the TinyModel encoder sidecar into `/api/ai`, log debug telemetry under **`meta.tinymodel`** (no UI change required). Shape is produced by `scripts/hsp_meta_lib.py` from `POST /v1/plan` or `plan_hsp_request()`.

## Example `/api/ai` response fragment

```json
{
  "ok": true,
  "output_text": "…",
  "actions": [{ "type": "navigate", "path": "/swap" }],
  "meta": {
    "tinymodel": {
      "model": "HyperlinksSpace/TinyModel1",
      "route_hint": "navigate:/swap",
      "actions": [{ "type": "navigate", "path": "/swap" }],
      "routing": {
        "fallback": false,
        "label": "Business",
        "confidence": 0.55,
        "margin": 0.2,
        "reason": "accept"
      },
      "retrieval": null,
      "classify_top_label": "Business"
    }
  }
}
```

When routing abstains and hybrid RAG runs, `retrieval` contains `top_idx`, `top_title`, `hybrid_score`, `keyword_overlap`, and `chunk_preview` (same fields as `/v1/plan`).

When `POST /v1/plan` fails, log:

```json
"meta": {
  "tinymodel": {
    "error": "plan_unavailable",
    "fallback": "plan→heuristic"
  }
}
```

## Gates

- Stdlib contract: `python scripts/hsp_meta_contract_smoke.py --verify`
- All stdlib HSP gates: `python scripts/hsp_integration_smoke.py --verify`
- Full stack (torch + live HTTP): `python scripts/hsp_integration_smoke.py --verify --full`

See also: [`phase3-serving-profile.md`](phase3-serving-profile.md), [`hsp-tinymodel-integration-strategy.md`](hsp-tinymodel-integration-strategy.md).
