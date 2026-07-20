#!/usr/bin/env python3
"""Smoke test a deployed TinyModel sidecar (e.g. Railway tinymodel.hyperlinks.space).

Examples:
  python scripts/hsp_railway_deploy_smoke.py --verify
  python scripts/hsp_railway_deploy_smoke.py --verify --base-url https://tinymodel.hyperlinks.space
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

_scripts = Path(__file__).resolve().parent
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))

from hsp_corpus_lib import corpus_fingerprint
from hsp_phase3_contract_smoke import validate_healthz, validate_meta_response, validate_plan_response

_CORPUS = Path(__file__).resolve().parent.parent / "texts" / "hsp_program_corpus.md"
_DEFAULT_URL = os.environ.get(
    "TINYMODEL_PUBLIC_URL",
    "https://tinymodel.hyperlinks.space",
)
_OUT = Path(__file__).resolve().parent.parent / ".tmp" / "hsp-railway-deploy-smoke" / "run.json"
_PROG = "hsp_railway_deploy_smoke"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--base-url",
        type=str,
        default=_DEFAULT_URL,
        help=f"Public sidecar URL (default: {_DEFAULT_URL}).",
    )
    p.add_argument("--verify", action="store_true")
    p.add_argument("--output-json", type=str, default="")
    return p


def _get(url: str, timeout: float = 30.0) -> tuple[int, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
        return resp.status, json.loads(raw) if raw else None


def _post(url: str, payload: dict[str, Any], timeout: float = 120.0) -> tuple[int, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
        return resp.status, json.loads(raw) if raw else None


def run_verify(base_url: str) -> dict[str, Any]:
    base = base_url.rstrip("/")
    checks: list[dict[str, Any]] = []

    _, root = _get(f"{base}/", timeout=30.0)
    if not isinstance(root, dict) or not root.get("service"):
        raise ValueError("GET / did not return service map")
    checks.append({"name": "root", "ok": True})

    _, health = _get(f"{base}/healthz")
    validate_healthz(health)
    checks.append({"name": "healthz", "ok": True})

    expected_version = corpus_fingerprint(_CORPUS) if _CORPUS.is_file() else None
    _, meta = _get(f"{base}/v1/meta")
    validate_meta_response(meta, expected_version=expected_version)
    checks.append(
        {
            "name": "meta:corpus_version",
            "ok": True,
            "version": meta.get("corpus", {}).get("version"),
        }
    )

    _, plan_nav = _post(f"{base}/v1/plan", {"text": "open swap page"}, timeout=180.0)
    validate_plan_response(plan_nav)
    nav_ok = plan_nav.get("intent") == "navigate" and bool(plan_nav.get("actions"))
    checks.append({"name": "plan:navigate", "ok": nav_ok})

    _, plan_screen = _post(
        f"{base}/v1/plan",
        {"text": "what is this", "context": {"route": "/shield", "locale": "en"}},
        timeout=180.0,
    )
    validate_plan_response(plan_screen)
    screen_ok = plan_screen.get("intent") == "explain_screen"
    checks.append({"name": "plan:explain_screen", "ok": screen_ok})

    _, plan_hs = _post(
        f"{base}/v1/plan",
        {"text": "sidecar ping strategy ai core", "context": {"locale": "en", "surface": "ai-core"}},
        timeout=30.0,
    )
    validate_plan_response(plan_hs)
    reply = str(plan_hs.get("reply_text") or "")
    hs_ok = (
        plan_hs.get("intent") == "strategy_handshake"
        and "TM1-SIDECAR-OK" in reply
    )
    checks.append({"name": "plan:strategy_handshake", "ok": hs_ok, "reply_text": reply[:120]})

    failed = [c for c in checks if not c["ok"]]
    if failed:
        raise ValueError(f"checks failed: {failed}")

    return {
        "base_url": base,
        "checks": checks,
        "ok": True,
    }


def main() -> None:
    args = build_parser().parse_args()
    try:
        artifact = run_verify(args.base_url)
    except (ValueError, urllib.error.URLError, TimeoutError) as e:
        print(f"{_PROG}: FAIL {e}", file=sys.stderr)
        raise SystemExit(1) from e
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:500]
        print(f"{_PROG}: FAIL HTTP {e.code} {e.reason}: {body}", file=sys.stderr)
        raise SystemExit(1) from e

    out = Path(args.output_json) if args.output_json else _OUT
    if args.verify or args.output_json:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {out}")

    passed = sum(1 for c in artifact["checks"] if c["ok"])
    print(f"{_PROG}: {artifact['base_url']} checks={passed}/{len(artifact['checks'])} ok=True")
    if args.verify:
        print(f"{_PROG} verify: OK")


if __name__ == "__main__":
    main()
