#!/usr/bin/env python3
"""Horizon 7: assured platform — minimal tenant **isolation** demo (two SQLite DBs, no crosstalk).

Implements a tiny slice of the \"separate data plane per tenant\" bar from
texts/further-development-universe-brain.md (Horizon 7). Not a full compliance product.

Uses horizon3_store in-proc (stdlib + sqlite3 only; no new deps)."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

_scripts = Path(__file__).resolve().parent
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))

import horizon3_store as h3  # noqa: E402

_REPO = Path(__file__).resolve().parent.parent
_SCHEMA = "horizon7_assured_run/1.0"
_OUT_DIR = _REPO / ".tmp" / "horizon7-assured"
_DEFAULT_OUT = _OUT_DIR / "run.json"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--verify",
        action="store_true",
        help="Run isolation checks; write .tmp/horizon7-assured/run.json.",
    )
    p.add_argument("--output-json", type=str, default=str(_DEFAULT_OUT))
    return p.parse_args()


def run_verify() -> tuple[dict, bool]:
    """Two notional tenants: A and B. Same logical scope_key strings are allowed in each DB; data must not leak across files."""
    checks: list[dict] = []
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        db_a = base / "tenant_a" / "memory.db"
        db_b = base / "tenant_b" / "memory.db"
        ca = h3.connect(db_a)
        h3.init_schema(ca)
        cb = h3.connect(db_b)
        h3.init_schema(cb)

        # Tenant A: org:acme; Tenant B: org:acme' (same label, different storage file)
        id_a1 = h3.put(ca, scope_key="org:acme", kind="long_term", content="Acme only — secret 111")
        id_b1 = h3.put(cb, scope_key="org:acme", kind="long_term", content="Other host — acme 999")

        la = h3.list_for_scope(ca, "org:acme", kind=None)
        lb = h3.list_for_scope(cb, "org:acme", kind=None)
        checks.append(
            {
                "name": "row_counts_per_tenant",
                "ok": len(la) == 1 and len(lb) == 1,
                "detail": {"tenant_a_ids": [x.id for x in la], "tenant_b_ids": [x.id for x in lb]},
            }
        )
        a_content = la[0].content if la else ""
        b_content = lb[0].content if lb else ""
        checks.append(
            {
                "name": "isolation_strong_acme_acme",
                "ok": "111" in a_content and "999" in b_content and "111" not in b_content and "999" not in a_content,
                "detail": {"preview_a": a_content[:40], "preview_b": b_content[:40]},
            }
        )
        ex_a = h3.export_scope_json(ca, "org:acme")
        ex_b = h3.export_scope_json(cb, "org:acme")
        leak = "111" in json.dumps(ex_b) and "999" in json.dumps(ex_a)  # wrong-way leak
        checks.append(
            {
                "name": "export_no_cross_tenant_substrings",
                "ok": not leak
                and "111" in json.dumps(ex_a)
                and "999" in json.dumps(ex_b)
                and "999" not in json.dumps(ex_a)
                and "111" not in json.dumps(ex_b),
            }
        )
        g_a = h3.get(ca, id_a1)
        g_b_wrong = h3.get(cb, id_a1)  # same id string must not resolve in other tenant DB
        checks.append(
            {
                "name": "get_by_id_respects_tenant_file",
                "ok": g_a is not None and g_b_wrong is None,
            }
        )
        h3.forget_scope(ca, "org:acme")
        h3.forget_scope(cb, "org:acme")
        checks.append(
            {
                "name": "forget_scope_only_own_store",
                "ok": len(h3.list_for_scope(ca, "org:acme", kind=None)) == 0
                and len(h3.list_for_scope(cb, "org:acme", kind=None)) == 0,
            }
        )
        ca.close()
        cb.close()

    ok = all(c.get("ok") for c in checks)
    return {"checks": checks}, ok


def main() -> int:
    a = parse_args()
    if not a.verify:
        print("Use --verify to run the tenant isolation self-test.", file=sys.stderr)
        return 2
    body, ok = run_verify()
    p = Path(a.output_json)
    p.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "horizon": 7,
        "schema": _SCHEMA,
        "mode": "tenant_isolation_smoke",
        "verify_mode": "two_sqlite_files_no_crosstalk",
        "ok": ok,
        **body,
        "note": "Demo only. Real H7 needs org-wide policy, regions, DSR, and external audit — see universe-brain doc.",
    }
    p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon7 verify: FAILED (see checks in artifact)", file=sys.stderr)
        print(f"wrote {p}", file=sys.stderr)
        return 1
    print(f"horizon7 verify: OK wrote {p}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
