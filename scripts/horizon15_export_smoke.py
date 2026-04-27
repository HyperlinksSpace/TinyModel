#!/usr/bin/env python3
"""Horizon 15: data minimization — export payloads must match allowed field envelopes.

Loads texts/horizon15_export_envelope_sample.json and validates sample dicts.
Writes horizon15_export_run/1.0. Not legal advice; a privacy-engineering-shaped contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "texts" / "horizon15_export_envelope_sample.json"
_SCHEMA = "horizon15_export_run/1.0"
_OUT = _REPO / ".tmp" / "horizon15-export" / "run.json"


def load_envelope(path: Path) -> dict:
    d = json.loads(path.read_text(encoding="utf-8"))
    if "export_kinds" not in d or not isinstance(d["export_kinds"], dict):
        raise ValueError("envelope needs export_kinds object")
    return d


def validate_payload(kind: str, payload: dict, env: dict) -> tuple[bool, str]:
    kinds = env["export_kinds"]
    if kind not in kinds:
        return False, f"unknown export_kind {kind!r}"
    spec = kinds[kind]
    allowed = set(spec["allowed_fields"])
    keys = set(payload.keys())
    if not keys.issubset(allowed):
        extra = keys - allowed
        return False, f"extra fields: {sorted(extra)}"
    return True, "ok"


def run_verify(env_path: Path) -> tuple[dict, bool]:
    env = load_envelope(env_path)
    cases: list[dict] = []
    ok = True

    good = {
        "scope_key": "org:acme",
        "items": [],
        "exported_at": "2026-04-26T00:00:00Z",
        "schema": "dsr_export/1.0",
    }
    g_ok, _ = validate_payload("dsr_access", good, env)
    ok = ok and g_ok
    cases.append({"case": "dsr_minimal_allow", "payload_keys": sorted(good.keys()), "ok": g_ok})

    bad = {**good, "national_id": "xxx"}
    b_ok, reason = validate_payload("dsr_access", bad, env)
    ok = ok and (not b_ok)
    cases.append({"case": "dsr_extra_field_denied", "ok": not b_ok, "reason": reason})

    agg_ok_payload = {"date": "2026-04-26", "counts": {"q": 1}, "schema": "analytics_agg/1.0"}
    a_ok, _ = validate_payload("analytics_agg", agg_ok_payload, env)
    ok = ok and a_ok
    cases.append({"case": "analytics_ok", "ok": a_ok})

    return ({"envelope_path": str(env_path.relative_to(_REPO)) if env_path.is_relative_to(_REPO) else str(env_path), "cases": cases}, ok)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verify", action="store_true")
    p.add_argument("--envelope", type=str, default=str(_DEFAULT))
    p.add_argument("--output-json", type=str, default=str(_OUT))
    return p.parse_args()


def main() -> int:
    a = parse_args()
    if not a.verify:
        print("Use --verify.", file=sys.stderr)
        return 2
    path = Path(a.envelope)
    if not path.is_file():
        print(f"Missing: {path}", file=sys.stderr)
        return 1
    body, ok = run_verify(path)
    out = Path(a.output_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "horizon": 15,
        "schema": _SCHEMA,
        "mode": "export_envelope_smoke",
        "ok": ok,
        **body,
        "note": "Pair with legal for DSR/analytics definitions; fields are illustrative.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon15 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon15 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
