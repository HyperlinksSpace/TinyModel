"""Stdlib unit tests for Strategy ↔ TinyModel handshake."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from hsp_strategy_handshake import (  # noqa: E402
    HANDSHAKE_INTENT,
    HANDSHAKE_TOKEN,
    build_handshake_reply,
    is_strategy_handshake,
    strategy_handshake_plan,
)


class TestStrategyHandshake(unittest.TestCase):
    def test_detects_ping_phrases(self) -> None:
        self.assertTrue(is_strategy_handshake("sidecar ping strategy ai core"))
        self.assertTrue(is_strategy_handshake("SIDECAR PING"))
        self.assertTrue(is_strategy_handshake("handshake with strategy AI CORE"))
        self.assertFalse(is_strategy_handshake("open the roadmap section"))
        self.assertFalse(is_strategy_handshake("explain TinyModel sidecar composer"))

    def test_plan_shape(self) -> None:
        plan = strategy_handshake_plan(
            "sidecar ping",
            context={"locale": "en", "surface": "ai-core"},
        )
        self.assertEqual(plan["intent"], HANDSHAKE_INTENT)
        self.assertIn(HANDSHAKE_TOKEN, plan["reply_text"])
        self.assertIn(HANDSHAKE_TOKEN, plan["retrieval"]["chunk_preview"])
        self.assertEqual(plan["routing"]["reason"], "strategy_handshake")
        self.assertIn(HANDSHAKE_TOKEN, build_handshake_reply())


if __name__ == "__main__":
    unittest.main()
