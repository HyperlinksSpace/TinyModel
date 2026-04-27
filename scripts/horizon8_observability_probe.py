#!/usr/bin/env python3
"""Horizon 8: observability probe bundle — build snapshot + run dependent health (H7) in one JSON.

Collects Python/platform (and optional git revision), runs horizon7_assured_smoke --verify as a
dependency probe, and writes horizon8_probe_run/1.0. Not a full APM stack; a correlation-friendly
artifact for incidents and CI."""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_SCHEMA = "horizon8_probe_run/1.0"
_OUT = _REPO / ".tmp" / "horizon8-probe" / "run.json"


def _git_rev() -> str | None:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(_REPO),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def _run_h7_probe(py: str) -> dict:
    t0 = time.perf_counter()
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    r = subprocess.run(
        [py, str(_REPO / "scripts" / "horizon7_assured_smoke.py"), "--verify"],
        cwd=str(_REPO),
        env=env,
    )
    return {
        "name": "horizon7_tenant_isolation",
        "ok": r.returncode == 0,
        "exit_code": r.returncode,
        "seconds": round(time.perf_counter() - t0, 3),
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--verify",
        action="store_true",
        help="Run H7 probe and write .tmp/horizon8-probe/run.json",
    )
    p.add_argument("--output-json", type=str, default=str(_OUT))
    return p.parse_args()


def main() -> int:
    a = parse_args()
    if not a.verify:
        print("Use --verify.", file=sys.stderr)
        return 2
    py = sys.executable
    env_snapshot = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "git_rev": _git_rev(),
    }
    h7 = _run_h7_probe(py)
    ok = h7["ok"]
    out = Path(a.output_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "horizon": 8,
        "schema": _SCHEMA,
        "mode": "observability_probe_bundle",
        "ok": ok,
        "environment": env_snapshot,
        "probes": [h7],
        "note": "Wire these fields to your log pipeline; this script only standardizes a JSON shape.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon8 verify: FAILED (H7 probe did not pass)", file=sys.stderr)
        print(f"wrote {out}", file=sys.stderr)
        return 1
    print(f"horizon8 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
