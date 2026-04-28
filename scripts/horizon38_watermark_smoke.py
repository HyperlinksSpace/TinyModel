#!/usr/bin/env python3
"""Horizon 38: monotonic watermarks — checkpoint series must not rewind.

Loads texts/horizon38_watermark_sample.json; non-decreasing adjacent pairs pass.
Writes horizon38_watermark_run/1.0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "texts" / "horizon38_watermark_sample.json"
_SCHEMA = "horizon38_watermark_run/1.0"
_OUT = _REPO / ".tmp" / "horizon38-watermark" / "run.json"


def is_non_decreasing(series: list[int]) -> bool:
    if len(series) <= 1:
        return True
    for i in range(1, len(series)):
        if series[i] < series[i - 1]:
            return False
    return True


def run_verify(path: Path) -> tuple[dict, bool]:
    m = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    ok = True
    for sc in m["scenarios"]:
        wm = [int(x) for x in sc["watermarks"]]
        exp = bool(sc["expect_non_decreasing"])
        got = is_non_decreasing(wm)
        row_ok = got == exp
        ok = ok and row_ok
        rows.append(
            {
                "watermarks": wm,
                "non_decreasing": got,
                "expect_non_decreasing": exp,
                "match": row_ok,
            }
        )
    body = {
        "manifest_path": str(path.relative_to(_REPO)) if path.is_relative_to(_REPO) else str(path),
        "scenarios": rows,
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
        "horizon": 38,
        "schema": _SCHEMA,
        "mode": "watermark_monotonic_smoke",
        "ok": ok,
        **body,
        "note": "Extend with vector clocks, Kafka ISR semantics, and exactly-once sinks.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon38 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon38 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
