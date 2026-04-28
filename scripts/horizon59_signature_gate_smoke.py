#!/usr/bin/env python3
"""Horizon 59: signature gate — signed artifacts for release channels.

Loads texts/horizon59_signature_gate_sample.json; allow iff channel does not require sig or signature_valid.
Writes horizon59_signature_gate_run/1.0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "texts" / "horizon59_signature_gate_sample.json"
_SCHEMA = "horizon59_signature_gate_run/1.0"
_OUT = _REPO / ".tmp" / "horizon59-signature-gate" / "run.json"


def run_verify(path: Path) -> tuple[dict, bool]:
    m = json.loads(path.read_text(encoding="utf-8"))
    req = {str(x).lower().strip() for x in m["channels_requiring_signature"]}
    rows = []
    ok = True
    for ch in m["checks"]:
        chan = str(ch["channel"]).lower().strip()
        sig = bool(ch["signature_valid"])
        exp = bool(ch["expect_allow"])
        needs_sig = chan in req
        got = (not needs_sig) or sig
        row_ok = got == exp
        ok = ok and row_ok
        rows.append(
            {
                "channel": chan,
                "requires_signature": needs_sig,
                "signature_valid": sig,
                "allow": got,
                "expect_allow": exp,
                "match": row_ok,
            }
        )
    body = {
        "manifest_path": str(path.relative_to(_REPO)) if path.is_relative_to(_REPO) else str(path),
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
        "horizon": 59,
        "schema": _SCHEMA,
        "mode": "signature_gate_smoke",
        "ok": ok,
        **body,
        "note": "Production adds key rotation, transparency logs, and dual signatures.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon59 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon59 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
