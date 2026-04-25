#!/usr/bin/env python3
"""Horizon 3 CLI: session + long-term memory, audit, TTL, DSR export/forget — no extra dependencies."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

_scripts = Path(__file__).resolve().parent
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))

import horizon3_store as h3  # noqa: E402

_REPO = _scripts.parent
_DEFAULT_DB = str(_REPO / ".tmp" / "horizon3" / "memory.db")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", type=str, default=_DEFAULT_DB, help="SQLite path (created if missing).")
    p.add_argument(
        "--verify",
        action="store_true",
        help="Run an in-proc self-test (uses a temp db); exit 0 on success.",
    )

    sub = p.add_subparsers(dest="cmd")

    a_put = sub.add_parser("put", help="Add memory (or update with --id).")
    a_put.add_argument("--scope", required=True, help="e.g. user:alice, org:acme:team1")
    a_put.add_argument("--kind", choices=["session", "long_term"], required=True)
    a_put.add_argument("--text", type=str, required=True)
    a_put.add_argument("--jurisdiction", type=str, default="")
    a_put.add_argument("--ttl-seconds", type=int, default=None)
    a_put.add_argument("--id", type=str, default=None, dest="mem_id", help="Update existing id.")

    a_get = sub.add_parser("get", help="Get one by id.")
    a_get.add_argument("memory_id", type=str)

    a_list = sub.add_parser("list", help="List by scope.")
    a_list.add_argument("--scope", required=True)
    a_list.add_argument("--kind", choices=["session", "long_term"], default=None)

    a_exp = sub.add_parser("export", help="DSR: JSON export for scope (items + audit).")
    a_exp.add_argument("--scope", required=True)
    a_exp.add_argument("-o", "--output", type=str, default="")

    sub.add_parser("prune", help="Delete expired rows (TTL in the past).")

    a_del = sub.add_parser("delete", help="Delete one id.")
    a_del.add_argument("memory_id", type=str)

    a_forget = sub.add_parser("forget-scope", help="DSR: delete all for scope.")
    a_forget.add_argument("--scope", required=True)

    a_clear = sub.add_parser("clear-session", help="Delete only session memories for scope.")
    a_clear.add_argument("--scope", required=True)

    a_audit = sub.add_parser("audit", help="Print audit log lines (JSONL).")
    a_audit.add_argument("--scope", type=str, default="")

    return p.parse_args()


def _conn(db: str) -> sqlite3.Connection:
    c = h3.connect(db)
    h3.init_schema(c)
    return c


def run_verify() -> int:
    with tempfile.TemporaryDirectory() as td:
        db = str(Path(td) / "m.db")
        c = _conn(db)
        try:
            mid = h3.put(
                c, scope_key="user:test", kind="session", content="ephemeral", ttl_seconds=3600
            )
            m2 = h3.put(
                c,
                scope_key="user:test",
                kind="long_term",
                content="Remember: customer prefers email.",
            )
            assert h3.get(c, mid) is not None
            assert len(h3.list_for_scope(c, "user:test", kind="session")) == 1
            h3.put(
                c,
                scope_key="user:test",
                kind="long_term",
                content="Updated preference.",
                memory_id=m2,
            )
            ex = h3.export_scope_json(c, "user:test")
            assert ex["horizon"] == 3 and len(ex["items"]) == 2
            assert any(x["action"] == "update" for x in ex["audit_for_scope"])
            n = h3.clear_session(c, "user:test")
            assert n == 1
            m3 = h3.put(
                c,
                scope_key="user:test",
                kind="long_term",
                content="short ttl",
                ttl_seconds=86400,
            )
            c.execute("BEGIN")
            c.execute("UPDATE memory_item SET expires_at=? WHERE id=?", (0.0, m2))
            c.execute("UPDATE memory_item SET expires_at=? WHERE id=?", (0.0, m3))
            c.execute("COMMIT")
            pr = h3.prune_expired(c)
            assert pr >= 2
            h3.forget_scope(c, "user:test")
            assert h3.list_for_scope(c, "user:test") == []
        finally:
            c.close()
    print("horizon3_memory_cli: verify OK", file=sys.stderr)
    return 0


def main() -> int:
    a = parse_args()
    if a.verify:
        return run_verify()

    if not a.cmd:
        print("Give a subcommand or --verify (see -h).", file=sys.stderr)
        return 2

    c = _conn(a.db)

    if a.cmd == "put":
        mem_id = getattr(a, "mem_id", None)
        mid = h3.put(
            c,
            scope_key=a.scope,
            kind=a.kind,  # type: ignore[arg-type]
            content=a.text,
            jurisdiction=a.jurisdiction,
            ttl_seconds=a.ttl_seconds,
            memory_id=mem_id,
        )
        print(mid)
        return 0
    if a.cmd == "get":
        m = h3.get(c, a.memory_id)
        if not m:
            print("not found", file=sys.stderr)
            return 1
        print(json.dumps(asdict(m), indent=2))
        return 0
    if a.cmd == "list":
        items = h3.list_for_scope(c, a.scope, kind=a.kind)  # type: ignore[arg-type]
        print(json.dumps([asdict(x) for x in items], indent=2))
        return 0
    if a.cmd == "export":
        d = h3.export_scope_json(c, a.scope)
        s = json.dumps(d, indent=2)
        if a.output:
            Path(a.output).write_text(s + "\n", encoding="utf-8")
            print(a.output)
        else:
            print(s)
        return 0
    if a.cmd == "prune":
        n = h3.prune_expired(c)
        print(n)
        return 0
    if a.cmd == "delete":
        ok = h3.delete_item(c, a.memory_id)
        return 0 if ok else 1
    if a.cmd == "forget-scope":
        n = h3.forget_scope(c, a.scope)
        print(n)
        return 0
    if a.cmd == "clear-session":
        n = h3.clear_session(c, a.scope)
        print(n)
        return 0
    if a.cmd == "audit":
        scope = a.scope if a.scope else None
        for line in h3.iter_audit(c, scope_key=scope):
            print(json.dumps(line, ensure_ascii=False))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
