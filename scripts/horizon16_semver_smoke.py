#!/usr/bin/env python3
"""Horizon 16: artifact semver compatibility — consumer reader_min vs declared artifact versions.

Loads texts/horizon16_compat_manifest_sample.json and checks tuple semver ordering.
Writes horizon16_semver_run/1.0. Not full PEP 440 — numeric x.y.z segments only."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "texts" / "horizon16_compat_manifest_sample.json"
_SCHEMA = "horizon16_semver_run/1.0"
_OUT = _REPO / ".tmp" / "horizon16-semver" / "run.json"


def semver_tuple(s: str) -> tuple[int, int, int]:
    parts = s.strip().split(".")
    if len(parts) != 3:
        raise ValueError(f"need x.y.z: {s!r}")
    return (int(parts[0]), int(parts[1]), int(parts[2]))


def can_read(reader_min: str, artifact_ver: str) -> bool:
    """True if artifact is at least reader_min (same major line not enforced here; demo only)."""
    return semver_tuple(artifact_ver) >= semver_tuple(reader_min)


def run_verify(path: Path) -> tuple[dict, bool]:
    d = json.loads(path.read_text(encoding="utf-8"))
    rmin = d["reader_minimum"]
    arts = d["artifacts_declared"]
    checks = []
    ok = True
    for name, ver in arts.items():
        c = can_read(rmin, ver)
        ok = ok and c
        checks.append({"artifact": name, "version": ver, "reader_minimum": rmin, "compatible": c})

    edge_ok = can_read("1.2.0", "1.2.0") and not can_read("1.2.0", "1.1.9")
    ok = ok and edge_ok

    return (
        {
            "manifest_path": str(path.relative_to(_REPO)) if path.is_relative_to(_REPO) else str(path),
            "checks": checks,
            "edge_reader_1_2_accepts_1_2": True,
            "edge_reader_1_2_rejects_1_1_9": not can_read("1.2.0", "1.1.9"),
        },
        ok and edge_ok,
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
        "horizon": 16,
        "schema": _SCHEMA,
        "mode": "semver_compatibility_smoke",
        "ok": ok,
        **body,
        "note": "Add major-version gates and deprecation windows in product; tuple compare is illustrative.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon16 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon16 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
