#!/usr/bin/env python3
"""Horizon 42: egress allow-list — outbound URL hostname gate.

Loads texts/horizon42_egress_allow_sample.json; allowed iff URL hostname matches
allowed_hosts (exact match, or hostname.endswith('.' + host) when host contains a dot).
Writes horizon42_egress_allow_run/1.0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "texts" / "horizon42_egress_allow_sample.json"
_SCHEMA = "horizon42_egress_allow_run/1.0"
_OUT = _REPO / ".tmp" / "horizon42-egress-allow" / "run.json"


def hostname_allowed(hostname: str, allowed_hosts: list[str]) -> bool:
    hn = (hostname or "").lower().strip(".")
    if not hn:
        return False
    for raw in allowed_hosts:
        h = raw.lower().strip(".")
        if not h:
            continue
        if hn == h:
            return True
        if "." in h and hn.endswith("." + h):
            return True
    return False


def host_from_url(url: str) -> str:
    u = url.strip()
    if "://" not in u:
        u = "https://" + u
    p = urlparse(u)
    return (p.hostname or "").strip()


def run_verify(path: Path) -> tuple[dict, bool]:
    m = json.loads(path.read_text(encoding="utf-8"))
    allowed = m["allowed_hosts"]
    rows = []
    ok = True
    for ch in m["checks"]:
        url = ch["url"]
        exp = bool(ch["expect_allowed"])
        host = host_from_url(url)
        got = hostname_allowed(host, allowed)
        row_ok = got == exp
        ok = ok and row_ok
        rows.append(
            {
                "url": url,
                "hostname": host,
                "allowed": got,
                "expect_allowed": exp,
                "match": row_ok,
            }
        )
    body = {
        "manifest_path": str(path.relative_to(_REPO)) if path.is_relative_to(_REPO) else str(path),
        "allowed_host_rules": len(allowed),
        "checks": rows,
    }
    return body, ok


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verify", action="store_true")
    p.add_argument("--manifest", type=str, default=str(_DEFAULT))
    p.add_argument("--output-json", type=str, default=str(_OUT))
    return p.parse_args()


def main() -> int:
    a = parse_args()
    if not a.verify:
        print("Use --verify.", file=sys.stderr)
        return 2
    path = Path(a.manifest)
    if not path.is_file():
        print(f"Missing: {path}", file=sys.stderr)
        return 1
    body, ok = run_verify(path)
    out = Path(a.output_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "horizon": 42,
        "schema": _SCHEMA,
        "mode": "egress_allow_smoke",
        "ok": ok,
        **body,
        "note": "Production adds DNS pinning, mTLS, egress proxies, and signed policy bundles.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon42 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon42 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
