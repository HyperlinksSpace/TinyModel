#!/usr/bin/env python3
"""Horizon 29: SBOM semver bounds — pinned versions vs allowed intervals.

Loads texts/horizon29_sbom_bounds_sample.json; numeric semver tuples [min, max_exclusive).
Writes horizon29_sbom_bounds_run/1.0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "texts" / "horizon29_sbom_bounds_sample.json"
_SCHEMA = "horizon29_sbom_bounds_run/1.0"
_OUT = _REPO / ".tmp" / "horizon29-sbom-bounds" / "run.json"


def ver_tuple(s: str) -> tuple[int, ...]:
    parts: list[int] = []
    for seg in s.strip().split("."):
        if not seg.isdigit():
            raise ValueError(f"non-numeric semver segment: {s!r}")
        parts.append(int(seg))
    return tuple(parts) if parts else (0,)


def padded_ge(a: tuple[int, ...], b: tuple[int, ...]) -> bool:
    m = max(len(a), len(b))
    ap = a + (0,) * (m - len(a))
    bp = b + (0,) * (m - len(b))
    return ap >= bp


def padded_lt(a: tuple[int, ...], b: tuple[int, ...]) -> bool:
    m = max(len(a), len(b))
    ap = a + (0,) * (m - len(a))
    bp = b + (0,) * (m - len(b))
    return ap < bp


def satisfies(pinned: str, vmin: str, vmax_excl: str) -> bool:
    p, lo, hi = ver_tuple(pinned), ver_tuple(vmin), ver_tuple(vmax_excl)
    return padded_ge(p, lo) and padded_lt(p, hi)


def run_verify(path: Path) -> tuple[dict, bool]:
    m = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    ok = True
    for pkg in m["packages"]:
        pin = pkg["pinned_version"]
        vmin = pkg["min_version"]
        vmax = pkg["max_exclusive"]
        exp = bool(pkg["expect_satisfies"])
        try:
            got = satisfies(pin, vmin, vmax)
        except ValueError:
            got = False
        row_ok = got == exp
        ok = ok and row_ok
        rows.append(
            {
                "name": pkg["name"],
                "pinned_version": pin,
                "min_version": vmin,
                "max_exclusive": vmax,
                "satisfies_bounds": got,
                "expect_satisfies": exp,
                "match": row_ok,
            }
        )
    body = {
        "manifest_path": str(path.relative_to(_REPO)) if path.is_relative_to(_REPO) else str(path),
        "packages": rows,
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
        "horizon": 29,
        "schema": _SCHEMA,
        "mode": "sbom_semver_bounds_smoke",
        "ok": ok,
        **body,
        "note": "Extend with PEP 440, prereleases, lockfile hashing, and CVE feeds.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon29 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon29 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
