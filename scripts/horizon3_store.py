"""Horizon 3: lightweight persistent memory store (auditable, deletable, TTL, session vs long-term).

All standard library + sqlite3 — no new pip deps for the core. Optional HTTP uses FastAPI (see horizon3_memory_api.py)."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterator, Literal

Kind = Literal["session", "long_term"]


@dataclass
class MemoryItem:
    id: str
    scope_key: str
    kind: Kind
    content: str
    content_fingerprint: str
    jurisdiction: str
    created_at: float
    updated_at: float
    expires_at: float | None
    extra: dict[str, Any]


def _now() -> float:
    return time.time()


def _fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]


def connect(db_path: str | Path, *, check_same_thread: bool = True) -> sqlite3.Connection:
    """Open SQLite. Set ``check_same_thread=False`` for Gradio/WSGI workers (default True for CLI)."""
    p = Path(db_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(
        str(p),
        isolation_level=None,
        check_same_thread=check_same_thread,
    )  # autocommit; we use BEGIN manually
    conn.row_factory = sqlite3.Row
    return conn


def init_schema(c: sqlite3.Connection) -> None:
    c.execute("BEGIN")
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS memory_item (
          id TEXT PRIMARY KEY,
          scope_key TEXT NOT NULL,
          kind TEXT NOT NULL CHECK(kind IN ('session','long_term')),
          content TEXT NOT NULL,
          content_fingerprint TEXT NOT NULL,
          jurisdiction TEXT NOT NULL DEFAULT '',
          created_at REAL NOT NULL,
          updated_at REAL NOT NULL,
          expires_at REAL,
          extra_json TEXT NOT NULL DEFAULT '{}'
        )
        """
    )
    c.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_mem_scope ON memory_item(scope_key)
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_log (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          memory_id TEXT,
          scope_key TEXT NOT NULL,
          action TEXT NOT NULL,
          detail_json TEXT NOT NULL,
          at REAL NOT NULL
        )
        """
    )
    c.execute("COMMIT")


def _audit(
    c: sqlite3.Connection,
    *,
    memory_id: str | None,
    scope_key: str,
    action: str,
    detail: dict[str, Any],
) -> None:
    c.execute("BEGIN")
    c.execute(
        "INSERT INTO audit_log(memory_id, scope_key, action, detail_json, at) VALUES (?,?,?,?,?)",
        (memory_id, scope_key, action, json.dumps(detail, ensure_ascii=False), _now()),
    )
    c.execute("COMMIT")


def _row_to_item(row: sqlite3.Row) -> MemoryItem:
    d = json.loads(row["extra_json"] or "{}")
    return MemoryItem(
        id=row["id"],
        scope_key=row["scope_key"],
        kind=row["kind"],
        content=row["content"],
        content_fingerprint=row["content_fingerprint"],
        jurisdiction=row["jurisdiction"] or "",
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        expires_at=row["expires_at"],
        extra=d,
    )


def put(
    c: sqlite3.Connection,
    *,
    scope_key: str,
    kind: Kind,
    content: str,
    jurisdiction: str = "",
    ttl_seconds: int | None = None,
    extra: dict[str, Any] | None = None,
    memory_id: str | None = None,
) -> str:
    """Insert, or update by id if it exists and scope_key matches."""
    extra = extra or {}
    t = _now()
    fp = _fingerprint(content)
    ex: float | None = None
    if ttl_seconds is not None and ttl_seconds > 0:
        ex = t + float(ttl_seconds)
    if memory_id:
        row = c.execute("SELECT * FROM memory_item WHERE id=?", (memory_id,)).fetchone()
        if row:
            old = _row_to_item(row)
            if old.scope_key != scope_key:
                raise ValueError("memory_id exists under a different scope_key; refusing update")
            c.execute("BEGIN")
            c.execute(
                "UPDATE memory_item SET content=?, content_fingerprint=?, jurisdiction=?, updated_at=?, "
                "expires_at=?, extra_json=? WHERE id=?",
                (content, fp, jurisdiction, t, ex, json.dumps(extra, ensure_ascii=False), memory_id),
            )
            c.execute("COMMIT")
            _audit(
                c,
                memory_id=memory_id,
                scope_key=scope_key,
                action="update",
                detail={"previous_fingerprint": old.content_fingerprint, "new_fingerprint": fp},
            )
            return memory_id
    mid = str(uuid.uuid4())
    c.execute("BEGIN")
    c.execute(
        "INSERT INTO memory_item(id, scope_key, kind, content, content_fingerprint, jurisdiction, "
        "created_at, updated_at, expires_at, extra_json) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (
            mid,
            scope_key,
            kind,
            content,
            fp,
            jurisdiction,
            t,
            t,
            ex,
            json.dumps(extra, ensure_ascii=False),
        ),
    )
    c.execute("COMMIT")
    _audit(c, memory_id=mid, scope_key=scope_key, action="create", detail={"kind": kind})
    return mid


def get(c: sqlite3.Connection, memory_id: str) -> MemoryItem | None:
    r = c.execute("SELECT * FROM memory_item WHERE id=?", (memory_id,)).fetchone()
    if not r:
        return None
    return _row_to_item(r)


def list_for_scope(
    c: sqlite3.Connection,
    scope_key: str,
    *,
    kind: Kind | None = None,
) -> list[MemoryItem]:
    if kind:
        q = "SELECT * FROM memory_item WHERE scope_key=? AND kind=? ORDER BY updated_at DESC"
        rows = c.execute(q, (scope_key, kind)).fetchall()
    else:
        q = "SELECT * FROM memory_item WHERE scope_key=? ORDER BY updated_at DESC"
        rows = c.execute(q, (scope_key,)).fetchall()
    return [_row_to_item(r) for r in rows]


def delete_item(c: sqlite3.Connection, memory_id: str) -> bool:
    row = c.execute("SELECT scope_key FROM memory_item WHERE id=?", (memory_id,)).fetchone()
    if not row:
        return False
    scope_key = row["scope_key"]
    c.execute("BEGIN")
    c.execute("DELETE FROM memory_item WHERE id=?", (memory_id,))
    c.execute("COMMIT")
    _audit(c, memory_id=None, scope_key=scope_key, action="delete", detail={"id": memory_id})
    return True


def forget_scope(c: sqlite3.Connection, scope_key: str) -> int:
    """DSR / right-to-erasure: remove all items for a scope. Returns number deleted."""
    c.execute("BEGIN")
    n = c.execute("SELECT count(*) FROM memory_item WHERE scope_key=?", (scope_key,)).fetchone()[0]
    c.execute("DELETE FROM memory_item WHERE scope_key=?", (scope_key,))
    c.execute("COMMIT")
    _audit(
        c,
        memory_id=None,
        scope_key=scope_key,
        action="forget_scope",
        detail={"deleted_count": n},
    )
    return int(n)


def clear_session(c: sqlite3.Connection, scope_key: str) -> int:
    """Delete only kind=session for scope."""
    c.execute("BEGIN")
    n = c.execute(
        "SELECT count(*) FROM memory_item WHERE scope_key=? AND kind='session'", (scope_key,)
    ).fetchone()[0]
    c.execute("DELETE FROM memory_item WHERE scope_key=? AND kind='session'", (scope_key,))
    c.execute("COMMIT")
    _audit(
        c,
        memory_id=None,
        scope_key=scope_key,
        action="clear_session",
        detail={"deleted_count": n},
    )
    return int(n)


def prune_expired(c: sqlite3.Connection) -> int:
    now = _now()
    c.execute("BEGIN")
    n = c.execute("SELECT count(*) FROM memory_item WHERE expires_at IS NOT NULL AND expires_at < ?", (now,)).fetchone()[0]
    c.execute("DELETE FROM memory_item WHERE expires_at IS NOT NULL AND expires_at < ?", (now,))
    c.execute("COMMIT")
    if n:
        _audit(
            c,
            memory_id=None,
            scope_key="*",
            action="prune_expired",
            detail={"deleted_count": n, "at": now},
        )
    return int(n)


def export_scope_json(c: sqlite3.Connection, scope_key: str) -> dict[str, Any]:
    """DSR access: all items + audit for scope."""
    items = [asdict(x) for x in list_for_scope(c, scope_key)]
    audit = [
        {
            "id": r["id"],
            "memory_id": r["memory_id"],
            "action": r["action"],
            "detail": json.loads(r["detail_json"] or "{}"),
            "at": r["at"],
        }
        for r in c.execute("SELECT * FROM audit_log WHERE scope_key=? ORDER BY id", (scope_key,)).fetchall()
    ]
    return {
        "horizon": 3,
        "schema": "horizon3_export/1.0",
        "scope_key": scope_key,
        "items": items,
        "audit_for_scope": audit,
    }


def iter_audit(
    c: sqlite3.Connection,
    scope_key: str | None = None,
) -> Iterator[dict[str, Any]]:
    if scope_key:
        rows = c.execute("SELECT * FROM audit_log WHERE scope_key=? ORDER BY id", (scope_key,)).fetchall()
    else:
        rows = c.execute("SELECT * FROM audit_log ORDER BY id").fetchall()
    for r in rows:
        yield {
            "id": r["id"],
            "memory_id": r["memory_id"],
            "scope_key": r["scope_key"],
            "action": r["action"],
            "detail": json.loads(r["detail_json"] or "{}"),
            "at": r["at"],
        }
