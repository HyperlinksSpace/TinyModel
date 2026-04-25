#!/usr/bin/env python3
"""Optional FastAPI for Horizon 3 memory store (CRUD + export + forget). Reuses `horizon3_store`.

  pip install -r optional-requirements-phase3.txt
  python scripts/horizon3_memory_api.py --db .tmp/horizon3/memory.db
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_scripts = Path(__file__).resolve().parent
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))

import horizon3_store as h3  # noqa: E402

_REPO = _scripts.parent
_DEFAULT = str(_REPO / ".tmp" / "horizon3" / "memory.db")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", type=str, default=os.environ.get("HORIZON3_DB", _DEFAULT))
    p.add_argument("--host", type=str, default="127.0.0.1")
    p.add_argument("--port", type=int, default=8767)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    try:
        from fastapi import FastAPI, HTTPException
        import uvicorn
        from pydantic import BaseModel
    except ImportError as e:
        print("Install: pip install -r optional-requirements-phase3.txt", file=sys.stderr)
        raise SystemExit(1) from e

    c = h3.connect(args.db)
    h3.init_schema(c)
    app = FastAPI(
        title="TinyModel Horizon3 memory API",
        version="0.1.0",
        description="Session + long-term store; see texts/horizon3-handbook.md",
    )

    class PutIn(BaseModel):
        scope_key: str
        kind: str
        content: str
        jurisdiction: str = ""
        ttl_seconds: int | None = None
        memory_id: str | None = None

    @app.get("/")
    def root() -> dict[str, str]:
        return {
            "service": "horizon3_memory",
            "docs": "/docs",
            "export": "GET /v1/export/{scope_key}",
        }

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok", "horizon3": "memory"}

    @app.post("/v1/put", response_model=dict[str, str])
    def v1_put(req: PutIn) -> dict[str, str]:  # type: ignore[no-untyped-def]
        if req.kind not in ("session", "long_term"):
            raise HTTPException(status_code=400, detail="kind must be session or long_term")
        try:
            mid = h3.put(
                c,
                scope_key=req.scope_key,
                kind=req.kind,  # type: ignore[arg-type]
                content=req.content,
                jurisdiction=req.jurisdiction,
                ttl_seconds=req.ttl_seconds,
                memory_id=req.memory_id,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        return {"id": mid}

    @app.get("/v1/memory/{memory_id}")
    def v1_get(memory_id: str) -> dict[str, object]:  # type: ignore[no-untyped-def]
        m = h3.get(c, memory_id)
        if not m:
            raise HTTPException(status_code=404, detail="not found")
        from dataclasses import asdict
        return asdict(m)  # type: ignore[return-value]

    @app.get("/v1/list")
    def v1_list(scope: str, kind: str | None = None) -> list[dict[str, object]]:  # type: ignore[no-untyped-def]
        from dataclasses import asdict
        k = kind if kind in ("session", "long_term") else None
        return [asdict(x) for x in h3.list_for_scope(c, scope, kind=k)]  # type: ignore[arg-type]

    @app.get("/v1/export/{scope_key}")
    def v1_export(scope_key: str) -> dict[str, object]:  # type: ignore[no-untyped-def]
        return h3.export_scope_json(c, scope_key)

    @app.delete("/v1/forget/{scope_key}")
    def v1_forget(scope_key: str) -> dict[str, int]:  # type: ignore[no-untyped-def]
        n = h3.forget_scope(c, scope_key)
        return {"deleted": n}

    @app.post("/v1/prune")
    def v1_prune() -> dict[str, int]:  # type: ignore[no-untyped-def]
        return {"deleted": h3.prune_expired(c)}

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
