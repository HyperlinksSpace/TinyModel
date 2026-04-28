#!/usr/bin/env python3
"""Horizon 27: prompt injection gate — deny-list substring checks (lite).

Loads texts/horizon27_prompt_gate_sample.json; case-insensitive substring match per rule set.
Writes horizon27_prompt_gate_run/1.0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "texts" / "horizon27_prompt_gate_sample.json"
_SCHEMA = "horizon27_prompt_gate_run/1.0"
_OUT = _REPO / ".tmp" / "horizon27-prompt-gate" / "run.json"


def blocked(text: str, rules: list[dict]) -> bool:
    low = text.lower()
    for rule in rules:
        for pat in rule["patterns"]:
            if pat.lower() in low:
                return True
    return False


def run_verify(path: Path) -> tuple[dict, bool]:
    m = json.loads(path.read_text(encoding="utf-8"))
    rules = m["rules"]
    rows = []
    ok = True
    for vec in m["vectors"]:
        txt = vec["text"]
        exp = bool(vec["expect_blocked"])
        got = blocked(txt, rules)
        row_ok = got == exp
        ok = ok and row_ok
        rows.append(
            {
                "text_preview": txt[:80] + ("..." if len(txt) > 80 else ""),
                "expect_blocked": exp,
                "got_blocked": got,
                "match": row_ok,
            }
        )
    body = {
        "manifest_path": str(path.relative_to(_REPO)) if path.is_relative_to(_REPO) else str(path),
        "rule_sets": len(rules),
        "vectors": rows,
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
        "horizon": 27,
        "schema": _SCHEMA,
        "mode": "prompt_gate_smoke",
        "ok": ok,
        **body,
        "note": "Extend with tokenizer-aware scans, allow-lists, and model-assisted moderation.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon27 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon27 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
