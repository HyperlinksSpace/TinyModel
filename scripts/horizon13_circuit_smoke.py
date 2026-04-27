#!/usr/bin/env python3
"""Horizon 13: circuit breaker — simulate client resilience to an unhealthy upstream.

States: CLOSED -> OPEN after N consecutive failures; OPEN short-circuits; reset() -> HALF_OPEN;
one success in HALF_OPEN -> CLOSED. Writes horizon13_circuit_run/1.0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Literal

_REPO = Path(__file__).resolve().parent.parent
_SCHEMA = "horizon13_circuit_run/1.0"
_OUT = _REPO / ".tmp" / "horizon13-circuit" / "run.json"

State = Literal["CLOSED", "OPEN", "HALF_OPEN"]


class CircuitBreaker:
    def __init__(self, *, failure_threshold: int = 3) -> None:
        self.failure_threshold = failure_threshold
        self._state: State = "CLOSED"
        self._consecutive_failures = 0

    @property
    def state(self) -> State:
        return self._state

    def call(self, upstream_ok: bool) -> str:
        """Return outcome label for this request."""
        if self._state == "OPEN":
            return "short_circuit"
        if self._state == "HALF_OPEN":
            if upstream_ok:
                self._state = "CLOSED"
                self._consecutive_failures = 0
                return "recovery_ok"
            self._state = "OPEN"
            return "half_open_failed"

        # CLOSED
        if upstream_ok:
            self._consecutive_failures = 0
            return "ok"
        self._consecutive_failures += 1
        if self._consecutive_failures >= self.failure_threshold:
            self._state = "OPEN"
            self._consecutive_failures = 0
            return "opened"
        return "error"

    def reset(self) -> None:
        """Operator call: try again (e.g. after cooldown)."""
        if self._state == "OPEN":
            self._state = "HALF_OPEN"


def run_verify() -> tuple[dict, bool]:
    cb = CircuitBreaker(failure_threshold=3)
    trace: list[dict] = []
    ok = True

    def step(tag: str, success: bool, want: str) -> None:
        nonlocal ok
        got = cb.call(success)
        step_ok = got == want
        ok = ok and step_ok
        trace.append({"tag": tag, "upstream_ok": success, "got": got, "state_after": cb.state, "expect": want, "ok": step_ok})

    # Trip the breaker
    step("f1", False, "error")
    step("f2", False, "error")
    step("f3", False, "opened")
    ok = ok and cb.state == "OPEN"
    # Short-circuit while OPEN
    step("sc1", True, "short_circuit")
    step("sc2", False, "short_circuit")

    cb.reset()
    ok = ok and cb.state == "HALF_OPEN"
    step("h1", True, "recovery_ok")
    ok = ok and cb.state == "CLOSED"

    # Healthy traffic
    step("ok1", True, "ok")

    # Trip again then fail in HALF_OPEN
    cb2 = CircuitBreaker(failure_threshold=2)
    cb2.call(False)
    cb2.call(False)
    ok = ok and cb2.state == "OPEN"
    cb2.reset()
    cb2.call(False)
    ok = ok and cb2.state == "OPEN"
    trace.append(
        {
            "tag": "half_open_fail_reopens",
            "state_after": cb2.state,
            "ok": cb2.state == "OPEN",
        }
    )

    return ({"trace": trace, "scenario": "threshold_3_and_2"}, ok)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verify", action="store_true")
    p.add_argument("--output-json", type=str, default=str(_OUT))
    return p.parse_args()


def main() -> int:
    a = parse_args()
    if not a.verify:
        print("Use --verify.", file=sys.stderr)
        return 2
    body, ok = run_verify()
    out = Path(a.output_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "horizon": 13,
        "schema": _SCHEMA,
        "mode": "circuit_breaker_smoke",
        "ok": ok,
        **body,
        "note": "Add timeouts, jitter, and metrics in production; this is a state-machine demo.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon13 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon13 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
