#!/usr/bin/env python3
"""Horizon 20: feature flags — deterministic staged rollout (hash bucket vs percent).

Loads texts/horizon20_flags_sample.json, evaluates flags per subject, checks expect_vectors.
Writes horizon20_flags_run/1.0."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "texts" / "horizon20_flags_sample.json"
_SCHEMA = "horizon20_flags_run/1.0"
_OUT = _REPO / ".tmp" / "horizon20-flags" / "run.json"


def bucket_pct(subject: str, salt: str) -> int:
    raw = hashlib.sha256(f"{salt}:{subject}".encode("utf-8")).hexdigest()
    return int(raw[:16], 16) % 100


def flag_on(enabled: bool, rollout_percent: int, subject: str, salt: str) -> bool:
    if not enabled:
        return False
    if rollout_percent <= 0:
        return False
    if rollout_percent >= 100:
        return True
    return bucket_pct(subject, salt) < rollout_percent


def run_verify(path: Path) -> tuple[dict, bool]:
    m = json.loads(path.read_text(encoding="utf-8"))
    salt = m["salt"]
    flags_by_id = {f["id"]: f for f in m["flags"]}
    rows = []
    ok = True
    for ev in m["expect_vectors"]:
        fid = ev["flag_id"]
        subj = ev["subject"]
        expect = ev["expect_on"]
        fl = flags_by_id[fid]
        got = flag_on(fl["enabled"], fl["rollout_percent"], subj, salt)
        row_ok = got == expect
        ok = ok and row_ok
        rows.append(
            {
                "subject": subj,
                "flag_id": fid,
                "expect_on": expect,
                "got_on": got,
                "match": row_ok,
            }
        )
    ok = ok and not flag_on(True, 0, "__inv__", salt)
    ok = ok and flag_on(True, 100, "__inv__", salt)
    ok = ok and not flag_on(False, 100, "__inv__", salt)
    return (
        {
            "manifest_path": str(path.relative_to(_REPO)) if path.is_relative_to(_REPO) else str(path),
            "salt": salt,
            "vectors": rows,
        },
        ok,
    )


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
        "horizon": 20,
        "schema": _SCHEMA,
        "mode": "feature_flags_rollout_smoke",
        "ok": ok,
        **body,
        "note": "Replace salt per env; integrate with flag store / LaunchDarkly-style backends in prod.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon20 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon20 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
