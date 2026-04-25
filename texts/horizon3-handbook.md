# Horizon 3: persistent mind (memory + continuity) — MVP

Implements the **Persistent mind** line from [`further-development-universe-brain.md`](further-development-universe-brain.md): **session** vs **long-term** facts, **TTL**, an **append-only audit log**, **DSR-shaped** export and **forget-scope** (delete all for a user/org key). Stored in **SQLite** under your control — not an opaque remote vector DB.

| Piece | File | Role |
| ----- | ---- | ---- |
| **Store** | `scripts/horizon3_store.py` | Schema, `put`/`get`/`list`/`prune`/`export`/`forget_scope`/`clear_session` |
| **CLI** | `scripts/horizon3_memory_cli.py` | All operations; `--verify` self-test (temp db, no network) |
| **API** (optional) | `scripts/horizon3_memory_api.py` | FastAPI; needs [`optional-requirements-phase3.txt`](../optional-requirements-phase3.txt) |
| **Deps** | [`optional-requirements-horizon3.txt`](../optional-requirements-horizon3.txt) | Notes only (stdlib for CLI) |

**Conflict policy (MVP):** last write on `id` with scope check; updates append an **audit** row with old/new content fingerprints. Production systems may add merge rules or human review on top of this.

## Self-test (CI / local, no network)

```bash
python scripts/horizon3_memory_cli.py --verify
```

**Expect:** stderr ends with `horizon3_memory_cli: verify OK` and exit code **0**.

## Manual walkthrough (CLI)

Default DB: `.tmp/horizon3/memory.db` (gitignored; override with `--db`).

1. **Session vs long-term + export**

   ```bash
   python scripts/horizon3_memory_cli.py --db .tmp/horizon3/dev.db put --scope user:alice --kind session --text "In this chat we discussed refunds" --ttl-seconds 7200
   python scripts/horizon3_memory_cli.py --db .tmp/horizon3/dev.db put --scope user:alice --kind long_term --text "User prefers support in English" --jurisdiction EU
   python scripts/horizon3_memory_cli.py --db .tmp/horizon3/dev.db list --scope user:alice
   python scripts/horizon3_memory_cli.py --db .tmp/horizon3/dev.db export --scope user:alice
   ```

2. **Forget me (erasure for one scope)**

   ```bash
   python scripts/horizon3_memory_cli.py --db .tmp/horizon3/dev.db forget-scope --scope user:alice
   ```

3. **Clear only session (keep long-term)**

   Re-add items, then: `python scripts/horizon3_memory_cli.py --db .tmp/horizon3/dev.db clear-session --scope user:alice`

4. **Audit log**

   ```bash
   python scripts/horizon3_memory_cli.py --db .tmp/horizon3/dev.db audit
   python scripts/horizon3_memory_cli.py --db .tmp/horizon3/dev.db audit --scope user:alice
   ```

## Optional HTTP (same data file)

```bash
pip install -r optional-requirements-phase3.txt
python scripts/horizon3_memory_api.py --db .tmp/horizon3/dev.db
```

Open **http://127.0.0.1:8767/docs** (default port; change with `--port`).

**Env:** `HORIZON3_DB` can point to the SQLite path instead of `--db`.

## How this links to other horizons

- **Horizon 1/2** can **write** retrieved chunks or answers into this store (or pass `content` as RAG context only). The store does not embed text; add your own embedding layer if you need semantic recall over memories.

## Privacy and compliance (short)

- Treat `scope_key` as your **pseudonym / tenant id**; map to real users only in a separate, access-controlled system if needed.
- `export` is a starting point for **access** requests; `forget_scope` is a **delete** for that scope. Legal review is still required for your jurisdiction and product.
- **Risk:** leakage tests and monitoring are on you; this module only provides **auditable** structure.
