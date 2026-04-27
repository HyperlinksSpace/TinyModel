#!/usr/bin/env python3
"""Horizon 10: resource & cost envelopes — simulated unit spend vs. a per-window cap.

Loads texts/horizon10_budget_sample.json and proves **throttle** when cumulative cost
exceeds max_units_per_window. Not real billing — a FinOps-shaped contract + smoke."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "texts" / "horizon10_budget_sample.json"
_SCHEMA = "horizon10_budget_run/1.0"
_OUT = _REPO / ".tmp" / "horizon10-budget" / "run.json"


def load_budget(path: Path) -> dict:
    d = json.loads(path.read_text(encoding="utf-8"))
    if "max_units_per_window" not in d or "per_action_cost_units" not in d:
        raise ValueError("budget: need max_units_per_window and per_action_cost_units")
    if not isinstance(d["per_action_cost_units"], dict):
        raise ValueError("per_action_cost_units must be an object")
    return d


def try_spend(cfg: dict, spent: int, action: str) -> tuple[int, str]:
    """Return (new_spent, allow|deny)."""
    cap = int(cfg["max_units_per_window"])
    cost = int(cfg["per_action_cost_units"].get(action, 1))
    n = spent + cost
    if n > cap:
        return spent, "deny"
    return n, "allow"


def run_verify(cfg_path: Path) -> tuple[dict, bool]:
    cfg = load_budget(cfg_path)
    checks: list[dict] = []
    ok = True

    # Fill to cap with model.generate @ 10 units, cap 100 => 10 calls = 100
    spent = 0
    for i in range(10):
        spent, verdict = try_spend(cfg, spent, "model.generate")
        want = "allow"
        step_ok = verdict == want
        ok = ok and step_ok
        checks.append({"step": i + 1, "action": "model.generate", "spent_after": spent, "verdict": verdict, "ok": step_ok})
    spent, verdict = try_spend(cfg, spent, "model.generate")
    ok = ok and verdict == "deny"
    checks.append({"step": 11, "action": "model.generate", "spent_after": spent, "verdict": verdict, "ok": verdict == "deny"})

    # Cheap embeds: 100 x model.embed @ 1 unit
    spent = 0
    for i in range(100):
        spent, verdict = try_spend(cfg, spent, "model.embed")
        ok = ok and verdict == "allow"
    spent, verdict = try_spend(cfg, spent, "model.embed")
    ok = ok and verdict == "deny"
    checks.append({"scenario": "embed_hundred_and_one", "final_verdict": verdict, "ok": verdict == "deny"})

    # Unknown action with explicit cost pushes 60 + 50 over cap 100
    cfg2 = json.loads(cfg_path.read_text(encoding="utf-8"))
    cfg2["per_action_cost_units"] = {**cfg2["per_action_cost_units"], "unknown.act": 50}
    spent = 60
    _, verdict = try_spend(cfg2, spent, "unknown.act")
    ok = ok and verdict == "deny"

    return (
        {
            "budget_path": str(cfg_path.relative_to(_REPO)) if cfg_path.is_relative_to(_REPO) else str(cfg_path),
            "checks": checks,
            "unknown_action_over_cap_ok": verdict == "deny",
        },
        ok,
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verify", action="store_true")
    p.add_argument("--budget", type=str, default=str(_DEFAULT))
    p.add_argument("--output-json", type=str, default=str(_OUT))
    return p.parse_args()


def main() -> int:
    a = parse_args()
    if not a.verify:
        print("Use --verify.", file=sys.stderr)
        return 2
    path = Path(a.budget)
    if not path.is_file():
        print(f"Missing budget file: {path}", file=sys.stderr)
        return 1
    body, ok = run_verify(path)
    out = Path(a.output_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "horizon": 10,
        "schema": _SCHEMA,
        "mode": "budget_envelope_smoke",
        "ok": ok,
        **body,
        "note": "Connect to real metering/billing elsewhere; this is cumulative unit arithmetic only.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon10 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon10 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
