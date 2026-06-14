#!/usr/bin/env python3
"""Universal Brain golden-prompt evaluation runner.

Runs stdlib suites (embedded NL signals) offline; optional torch suites (intent routing).

Examples:
  python scripts/ub_eval_runner.py --verify
  python scripts/ub_eval_runner.py --suite nl_signals --limit 20
  python scripts/ub_eval_runner.py --suite routing --with-router --smoke --limit 10
  python scripts/ub_eval_runner.py --output-json .tmp/ub-eval/run.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_scripts = Path(__file__).resolve().parent
_REPO = _scripts.parent
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))

_GOLDEN_DIR = _REPO / "texts" / "golden-prompts"
_SCHEMA_RUN = "ub_eval_run/1.0"
_PROG = "ub_eval_runner"
_DEFAULT_OUT = _REPO / ".tmp" / "ub-eval" / "run.json"


@dataclass(frozen=True)
class CaseResult:
    id: str
    suite: str
    ok: bool
    detail: str
    detected: str | None = None
    expected: str | None = None
    latency_ms: float | None = None


def build_parser() -> argparse.ArgumentParser:
    epilog = (
        "Examples:\n"
        "  python scripts/ub_eval_runner.py --verify\n"
        "  python scripts/ub_eval_runner.py --suite nl_signals\n"
        "  python scripts/ub_eval_runner.py --suite routing --with-router --smoke --limit 15\n"
        "  python scripts/ub_eval_runner.py --golden-dir texts/golden-prompts --output-json .tmp/ub-eval/run.json"
    )
    p = argparse.ArgumentParser(
        prog=_PROG,
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog,
    )
    p.add_argument(
        "--golden-dir",
        type=str,
        default=str(_GOLDEN_DIR),
        help="Directory with nl_signals.jsonl, routing.jsonl, e2e.jsonl, hsp_intents.jsonl (default: texts/golden-prompts).",
    )
    p.add_argument(
        "--suite",
        choices=("all", "nl_signals", "routing", "e2e", "hsp_intents"),
        default="all",
        help="Which suite to run (default: all).",
    )
    p.add_argument("--limit", type=int, default=0, help="Max cases per suite (0 = no limit).")
    p.add_argument(
        "--verify",
        action="store_true",
        help="Stdlib nl_signals + hsp_intents + manifest check; exit 0 if pass rate >= --min-pass-rate.",
    )
    p.add_argument(
        "--min-pass-rate",
        type=float,
        default=0.95,
        help="Minimum fraction of scored cases that must pass (default: 0.95).",
    )
    p.add_argument(
        "--with-router",
        action="store_true",
        help="Score routing suite with infer_route (requires torch + transformers).",
    )
    p.add_argument(
        "--smoke",
        action="store_true",
        help="Use sshleifer/tiny-gpt2 for routing (with --with-router).",
    )
    p.add_argument("--model", type=str, default=None, help="Generative model id for routing eval.")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument(
        "--output-json",
        type=str,
        default="",
        help=f"Write ub_eval_run artifact (default: {_DEFAULT_OUT} when --verify).",
    )
    p.add_argument(
        "--print-json-stdout",
        action="store_true",
        help="Print JSON artifact to stdout after writing.",
    )
    return p


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {e}") from e
            if not isinstance(obj, dict):
                raise ValueError(f"{path}:{line_no}: expected JSON object")
            rows.append(obj)
    return rows


def validate_manifest(golden_dir: Path) -> dict[str, Any]:
    manifest_path = golden_dir / "manifest.json"
    if not manifest_path.is_file():
        raise SystemExit(f"Missing {manifest_path}; run: python scripts/seed_golden_prompts.py")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for name in manifest.get("files", []):
        p = golden_dir / name
        if not p.is_file():
            raise SystemExit(f"Manifest lists missing file: {p}")
    return manifest


def format_detected_signals(overrides: dict[str, str], trace_tags: list[str]) -> str:
    bits = [f"{k}={v}" for k, v in sorted(overrides.items())]
    bits.extend(trace_tags)
    return "+".join(bits)


def score_nl_signals(rows: list[dict[str, Any]], limit: int) -> list[CaseResult]:
    from nl_controls import analyze_embedded_prompt_signals, parse_control_action

    out: list[CaseResult] = []
    for row in rows[: limit or len(rows)]:
        cid = str(row.get("id", "?"))
        prompt = str(row.get("prompt", ""))
        expect_tags = row.get("expect_tags") or []
        if not isinstance(expect_tags, list):
            expect_tags = [str(expect_tags)]
        expect_tags = [str(t) for t in expect_tags]

        t0 = time.perf_counter()
        if parse_control_action(prompt) is not None:
            ok = False
            detected = "(session control — not embedded signal)"
            detail = "line matched parse_control_action; not an embedded-signal case"
        else:
            overrides, _extras, trace_tags = analyze_embedded_prompt_signals(prompt)
            detected = format_detected_signals(overrides, trace_tags)
            missing = [t for t in expect_tags if t not in detected]
            ok = not missing
            detail = "ok" if ok else f"missing tags: {missing}"
        ms = (time.perf_counter() - t0) * 1000.0
        out.append(
            CaseResult(
                id=cid,
                suite="nl_signals",
                ok=ok,
                detail=detail,
                detected=detected,
                expected="+".join(expect_tags),
                latency_ms=round(ms, 2),
            )
        )
    return out


def score_routing(
    rows: list[dict[str, Any]],
    limit: int,
    *,
    model_id: str,
    seed: int,
) -> list[CaseResult]:
    from horizon2_core import load_causal_lm, pick_device
    from universal_brain_chat import infer_route

    device = pick_device("auto")
    lm = load_causal_lm(model_id, device=device)
    out: list[CaseResult] = []
    for row in rows[: limit or len(rows)]:
        cid = str(row.get("id", "?"))
        prompt = str(row.get("prompt", ""))
        expect = str(row.get("expect_intent", "chat"))
        t0 = time.perf_counter()
        route = infer_route(lm, prompt, seed=seed, max_new_tokens=192)
        got = route.get("intent", "chat")
        ok = got == expect
        ms = (time.perf_counter() - t0) * 1000.0
        out.append(
            CaseResult(
                id=cid,
                suite="routing",
                ok=ok,
                detail="ok" if ok else f"got {got!r}, expected {expect!r}",
                detected=got,
                expected=expect,
                latency_ms=round(ms, 2),
            )
        )
    return out


def score_hsp_intents(rows: list[dict[str, Any]], limit: int) -> list[CaseResult]:
    from hsp_intent_router import score_hsp_intent_row

    out: list[CaseResult] = []
    for row in rows[: limit or len(rows)]:
        cid = str(row.get("id", "?"))
        expect = row.get("expect_route")
        expect_str = None if expect is None else str(expect)
        t0 = time.perf_counter()
        ok, detail, detected = score_hsp_intent_row(row)
        ms = (time.perf_counter() - t0) * 1000.0
        out.append(
            CaseResult(
                id=cid,
                suite="hsp_intents",
                ok=ok,
                detail=detail,
                detected=detected,
                expected=expect_str,
                latency_ms=round(ms, 2),
            )
        )
    return out


def skip_suite(name: str, reason: str, rows: list[dict[str, Any]], limit: int) -> list[CaseResult]:
    out: list[CaseResult] = []
    for row in rows[: limit or len(rows)]:
        out.append(
            CaseResult(
                id=str(row.get("id", "?")),
                suite=name,
                ok=True,
                detail=f"skipped: {reason}",
            )
        )
    return out


def summarize(results: list[CaseResult]) -> dict[str, Any]:
    scored = [r for r in results if not r.detail.startswith("skipped:")]
    passed = sum(1 for r in scored if r.ok)
    total = len(scored)
    rate = (passed / total) if total else 1.0
    by_suite: dict[str, dict[str, Any]] = {}
    for r in results:
        bucket = by_suite.setdefault(r.suite, {"passed": 0, "failed": 0, "skipped": 0, "total": 0})
        bucket["total"] += 1
        if r.detail.startswith("skipped:"):
            bucket["skipped"] += 1
        elif r.ok:
            bucket["passed"] += 1
        else:
            bucket["failed"] += 1
    return {
        "scored": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(rate, 4),
        "by_suite": by_suite,
    }


def run_eval(args: argparse.Namespace) -> tuple[dict[str, Any], bool]:
    golden_dir = Path(args.golden_dir).resolve()
    manifest = validate_manifest(golden_dir)

    suites_to_run: set[str]
    if args.verify:
        suites_to_run = {"nl_signals", "hsp_intents"}
    elif args.suite == "all":
        suites_to_run = {"nl_signals", "routing", "e2e", "hsp_intents"}
    else:
        suites_to_run = {args.suite}

    results: list[CaseResult] = []

    if "nl_signals" in suites_to_run:
        nl_rows = load_jsonl(golden_dir / "nl_signals.jsonl")
        results.extend(score_nl_signals(nl_rows, args.limit))

    if "hsp_intents" in suites_to_run:
        hsp_rows = load_jsonl(golden_dir / "hsp_intents.jsonl")
        results.extend(score_hsp_intents(hsp_rows, args.limit))

    if "routing" in suites_to_run:
        route_rows = load_jsonl(golden_dir / "routing.jsonl")
        if args.with_router:
            from horizon2_core import DEFAULT_INSTRUCTION_MODEL, SMOKE_MODEL_ID

            mid = SMOKE_MODEL_ID if args.smoke else (args.model or DEFAULT_INSTRUCTION_MODEL)
            results.extend(score_routing(route_rows, args.limit, model_id=mid, seed=args.seed))
        else:
            results.extend(
                skip_suite(
                    "routing",
                    "pass --with-router to score (requires torch)",
                    route_rows,
                    args.limit,
                )
            )

    if "e2e" in suites_to_run:
        e2e_rows = load_jsonl(golden_dir / "e2e.jsonl")
        results.extend(
            skip_suite(
                "e2e",
                "manual/LLM-judge rubric not automated yet",
                e2e_rows,
                args.limit,
            )
        )

    summary = summarize(results)
    min_rate = args.min_pass_rate
    ok = summary["pass_rate"] >= min_rate if summary["scored"] else True

    artifact: dict[str, Any] = {
        "schema": _SCHEMA_RUN,
        "program": _PROG,
        "golden_dir": str(golden_dir),
        "manifest": manifest,
        "options": {
            "suite": args.suite,
            "verify": args.verify,
            "limit": args.limit,
            "with_router": args.with_router,
            "smoke": args.smoke,
            "min_pass_rate": min_rate,
        },
        "summary": summary,
        "cases": [
            {
                "id": r.id,
                "suite": r.suite,
                "ok": r.ok,
                "detail": r.detail,
                "detected": r.detected,
                "expected": r.expected,
                "latency_ms": r.latency_ms,
            }
            for r in results
        ],
    }
    return artifact, ok


def main() -> None:
    args = build_parser().parse_args()
    artifact, ok = run_eval(args)

    out_path = args.output_json
    if not out_path and args.verify:
        out_path = str(_DEFAULT_OUT)
    if out_path:
        p = Path(out_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Wrote {p}", flush=True)

    s = artifact["summary"]
    print(
        f"ub_eval: scored={s['scored']} passed={s['passed']} failed={s['failed']} "
        f"pass_rate={s['pass_rate']}",
        flush=True,
    )
    if args.print_json_stdout:
        print(json.dumps(artifact, ensure_ascii=False))

    if not ok:
        print(
            f"ub_eval: FAIL pass_rate {s['pass_rate']} < min {args.min_pass_rate}",
            file=sys.stderr,
        )
        raise SystemExit(1)
    if args.verify:
        print("ub_eval verify: OK", flush=True)


if __name__ == "__main__":
    main()
