#!/usr/bin/env python3
"""Horizon 11: human outcome capture — validated JSONL for corrections / labels-in-the-loop.

Writes sample feedback rows (newline-delimited JSON), validates required keys, reads back.
Schema: horizon11_feedback_record/1.0 fields per line."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_SCHEMA_RUN = "horizon11_feedback_run/1.0"
_SCHEMA_ROW = "horizon11_feedback_record/1.0"
_REQUIRED = frozenset({"prediction_id", "corrected_label", "timestamp_iso", "source"})
_OUT_DIR = _REPO / ".tmp" / "horizon11-feedback"
_DEFAULT_JSONL = _OUT_DIR / "sample_feedback.jsonl"
_DEFAULT_RUN = _OUT_DIR / "run.json"


def validate_row(obj: dict) -> tuple[bool, str]:
    if not isinstance(obj, dict):
        return False, "not an object"
    keys = set(obj.keys())
    if not _REQUIRED.issubset(keys):
        return False, f"missing keys: {_REQUIRED - keys}"
    if obj["source"] not in ("human", "moderator", "import"):
        return False, "source must be human|moderator|import"
    return True, ""


def run_verify(jsonl_path: Path) -> tuple[dict, bool]:
    samples = [
        {
            "prediction_id": "pred_smoke_001",
            "corrected_label": "positive",
            "timestamp_iso": "2026-04-26T12:00:00Z",
            "source": "human",
            "schema": _SCHEMA_ROW,
        },
        {
            "prediction_id": "pred_smoke_002",
            "corrected_label": "refund",
            "timestamp_iso": "2026-04-26T12:01:00Z",
            "source": "moderator",
            "schema": _SCHEMA_ROW,
        },
    ]
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    lines_written = []
    for row in samples:
        ok_row, err = validate_row(row)
        if not ok_row:
            return {"error": err}, False
        line = json.dumps(row, separators=(",", ":"), ensure_ascii=False)
        lines_written.append(line)
    jsonl_path.write_text("\n".join(lines_written) + "\n", encoding="utf-8")

    loaded = []
    ok = True
    for i, ln in enumerate(jsonl_path.read_text(encoding="utf-8").splitlines()):
        if not ln.strip():
            continue
        obj = json.loads(ln)
        vr, er = validate_row(obj)
        ok = ok and vr
        loaded.append({"line": i + 1, "ok": vr, "detail": er})

    return (
        {
            "jsonl_path": str(jsonl_path.relative_to(_REPO)) if jsonl_path.is_relative_to(_REPO) else str(jsonl_path),
            "lines_validated": loaded,
            "row_count": len(loaded),
        },
        ok and len(loaded) == 2,
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verify", action="store_true")
    p.add_argument("--jsonl", type=str, default=str(_DEFAULT_JSONL))
    p.add_argument("--output-json", type=str, default=str(_DEFAULT_RUN))
    return p.parse_args()


def main() -> int:
    a = parse_args()
    if not a.verify:
        print("Use --verify.", file=sys.stderr)
        return 2
    body, ok = run_verify(Path(a.jsonl))
    out = Path(a.output_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "horizon": 11,
        "schema": _SCHEMA_RUN,
        "mode": "feedback_jsonl_smoke",
        "required_row_keys": sorted(_REQUIRED),
        "ok": ok,
        **body,
        "note": "Production needs secure ingestion, PII rules, and join keys to training pipelines.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon11 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon11 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
