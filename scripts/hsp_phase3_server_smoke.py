#!/usr/bin/env python3
"""Live HTTP smoke for phase3_reference_server + HSP corpus retrieve (subprocess + stdlib).

Examples:
  python scripts/hsp_phase3_server_smoke.py --verify
  python scripts/hsp_phase3_server_smoke.py --verify --model .tmp/phase3-smoke
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

_scripts = Path(__file__).resolve().parent
_REPO = _scripts.parent
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))

from hsp_corpus_lib import chunk_title, load_chunks
from hsp_phase3_contract_smoke import (
    validate_classify_response,
    validate_healthz,
    validate_retrieve_response,
)
from rag_faq_smoke import _pick_model

_CORPUS = _REPO / "texts" / "hsp_program_corpus.md"
_OUT = _REPO / ".tmp" / "hsp-phase3-server-smoke" / "run.json"
_SCHEMA = "hsp_phase3_server_smoke_run/1.0"
_PROG = "hsp_phase3_server_smoke"
_DEFAULT_PORT = 18765

# Semantic cosine retrieve (TinyModelRuntime) — not hybrid lexical rank (see hsp_rag_hybrid_smoke).
_SPOT_CHECKS: list[tuple[str, str]] = [
    ("connect telegram messages TDLib gateway", "Connect Telegram messages"),
    ("sign in with Google or GitHub", "Sign in and accounts"),
    ("smart layout wide viewport panel", "Smart layout"),
]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verify", action="store_true", help="Exit 0 when live HTTP probes pass.")
    p.add_argument("--model", type=str, default=None, help="Checkpoint or Hub id.")
    p.add_argument("--port", type=int, default=_DEFAULT_PORT, help="Loopback port for subprocess.")
    p.add_argument("--output-json", type=str, default="", help=f"Write run JSON (default: {_OUT}).")
    return p


def _http_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: float = 60.0,
) -> tuple[int, Any]:
    data = None
    headers: dict[str, str] = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
        return resp.status, json.loads(raw) if raw else None


def _wait_health(base: str, proc: subprocess.Popen[str], timeout_s: float = 120.0) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"server exited early with code {proc.returncode}")
        try:
            status, body = _http_json(f"{base}/healthz", timeout=5.0)
            if status == 200:
                validate_healthz(body)
                return
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError):
            time.sleep(1.0)
    raise TimeoutError(f"healthz not ready within {timeout_s}s at {base}")


def run_verify(model_arg: str | None, port: int) -> tuple[bool, dict[str, Any]]:
    from phase3_common import resolve_checkpoint_or_hub

    if not _CORPUS.is_file():
        raise ValueError(f"missing corpus {_CORPUS}")

    chunks = load_chunks(_CORPUS)
    model_id = resolve_checkpoint_or_hub(_pick_model(model_arg))
    base = f"http://127.0.0.1:{port}"
    server_script = _scripts / "phase3_reference_server.py"
    proc = subprocess.Popen(
        [
            sys.executable,
            str(server_script),
            "--model",
            model_id,
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=_REPO,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    checks: list[dict[str, Any]] = []
    spot_results: list[dict[str, Any]] = []
    try:
        _wait_health(base, proc)
        checks.append({"name": "healthz", "ok": True})

        _, classify_body = _http_json(
            f"{base}/v1/classify",
            method="POST",
            payload={"texts": ["open swap page"]},
        )
        validate_classify_response(classify_body)
        checks.append({"name": "classify", "ok": True})

        for query, expect_title in _SPOT_CHECKS:
            _, retrieve_body = _http_json(
                f"{base}/v1/retrieve",
                method="POST",
                payload={"query": query, "candidates": chunks, "top_k": 3},
                timeout=90.0,
            )
            validate_retrieve_response(retrieve_body, num_candidates=len(chunks))
            top_title = chunk_title(retrieve_body["hits"][0]["text"]) if retrieve_body.get("hits") else ""
            ok = expect_title.lower() in top_title.lower()
            spot_results.append(
                {
                    "query": query,
                    "expect_title": expect_title,
                    "top_title": top_title,
                    "ok": ok,
                }
            )
            checks.append({"name": f"retrieve:{expect_title}", "ok": ok, "detail": top_title})

        failed = [c for c in checks if not c["ok"]]
        if failed:
            detail = ", ".join(
                f"{c['name']}" + (f" ({c.get('detail', '')})" if c.get("detail") else "")
                for c in failed
            )
            raise ValueError(f"one or more HTTP probes failed: {detail}")

        artifact = {
            "schema": _SCHEMA,
            "model": model_id,
            "base_url": base,
            "corpus": str(_CORPUS),
            "chunk_count": len(chunks),
            "checks": checks,
            "spot_checks": spot_results,
            "ok": True,
        }
        return True, artifact
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()


def main() -> None:
    args = build_parser().parse_args()
    try:
        ok, artifact = run_verify(args.model, args.port)
    except (ValueError, TimeoutError, urllib.error.URLError) as e:
        print(f"{_PROG}: FAIL {e}", file=sys.stderr)
        raise SystemExit(1) from e

    out_path = Path(args.output_json) if args.output_json else _OUT
    if args.verify or args.output_json:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {out_path}")

    passed = sum(1 for c in artifact["checks"] if c["ok"])
    print(f"{_PROG}: checks={passed}/{len(artifact['checks'])} ok={ok}")
    if args.verify:
        print(f"{_PROG} verify: OK")


if __name__ == "__main__":
    main()
