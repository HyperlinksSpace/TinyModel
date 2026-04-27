#!/usr/bin/env python3
"""Horizon 9: declarative capability policy — allow/deny matrix with deny precedence.

Evaluates a small JSON policy (default: texts/horizon9_policy_sample.json) and writes
horizon9_policy_run/1.0. Not a full authorization server; a contract + smoke for governance."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT_POLICY = _REPO / "texts" / "horizon9_policy_sample.json"
_SCHEMA = "horizon9_policy_run/1.0"
_OUT = _REPO / ".tmp" / "horizon9-policy" / "run.json"


def load_policy(path: Path) -> dict:
    d = json.loads(path.read_text(encoding="utf-8"))
    for k in ("deny_actions", "allow_actions"):
        if k not in d or not isinstance(d[k], list):
            raise ValueError(f"policy: missing or invalid {k!r}")
    return d


def decide(action: str, p: dict) -> str:
    """Return allow | deny. Deny list wins; then allow list; else default_deny."""
    if action in p["deny_actions"]:
        return "deny"
    if action in p["allow_actions"]:
        return "allow"
    if p.get("default_deny", True):
        return "deny"
    return "allow"


def run_verify(policy_path: Path) -> tuple[dict, bool]:
    p = load_policy(policy_path)
    cases = [
        ("model.generate", "allow"),
        ("model.toxic.generate", "deny"),
        ("memory.write", "allow"),
        ("horizon7.verify", "allow"),
        ("unknown.action", "deny"),
        ("tool.exec.shell", "deny"),
    ]
    results = []
    all_ok = True
    for action, want in cases:
        got = decide(action, p)
        ok = got == want
        all_ok = all_ok and ok
        results.append({"action": action, "expect": want, "got": got, "ok": ok})
    p_both = {
        **p,
        "deny_actions": list(p["deny_actions"]) + ["collision.probe"],
        "allow_actions": list(p["allow_actions"]) + ["collision.probe"],
    }
    cgot = decide("collision.probe", p_both)
    coll_ok = cgot == "deny"
    all_ok = all_ok and coll_ok
    results.append(
        {
            "action": "collision.probe",
            "expect": "deny",
            "got": cgot,
            "ok": coll_ok,
        }
    )
    return (
        {
            "policy_path": str(policy_path.relative_to(_REPO)) if policy_path.is_relative_to(_REPO) else str(policy_path),
            "precedence": "deny_actions over allow_actions; then allow; else default_deny",
            "cases": results,
        },
        all_ok,
    )


def parse_args() -> argparse.Namespace:
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument("--verify", action="store_true", help="Run policy table check; write run.json.")
    a.add_argument(
        "--policy",
        type=str,
        default=str(_DEFAULT_POLICY),
        help="Path to policy JSON (default: texts/horizon9_policy_sample.json).",
    )
    a.add_argument("--output-json", type=str, default=str(_OUT))
    return a.parse_args()


def main() -> int:
    a = parse_args()
    if not a.verify:
        print("Use --verify.", file=sys.stderr)
        return 2
    path = Path(a.policy)
    if not path.is_file():
        print(f"Missing policy: {path}", file=sys.stderr)
        return 1
    body, ok = run_verify(path)
    out = Path(a.output_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "horizon": 9,
        "schema": _SCHEMA,
        "mode": "declarative_policy_smoke",
        "ok": ok,
        **body,
        "note": "Product authZ still needs identity, context, and audit; this is a static matrix demo.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon9 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon9 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
