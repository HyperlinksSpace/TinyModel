"""Tests for scripts/hsp_intent_router.py."""

from __future__ import annotations

import unittest
from pathlib import Path
import sys

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from hsp_intent_router import (  # noqa: E402
    actions_from_route_hint,
    infer_hsp_route_hint,
    score_hsp_intent_row,
)


class TestHspIntentRouter(unittest.TestCase):
    def test_navigate_swap(self) -> None:
        self.assertEqual(infer_hsp_route_hint("open swap page"), "navigate:/swap")

    def test_navigate_send(self) -> None:
        self.assertEqual(
            infer_hsp_route_hint("send TON from my wallet"), "navigate:/send"
        )

    def test_navigate_get(self) -> None:
        self.assertEqual(
            infer_hsp_route_hint("show my wallet address"), "navigate:/get"
        )

    def test_feature_telegram(self) -> None:
        self.assertEqual(
            infer_hsp_route_hint("connect telegram messages"),
            "feature:connect_telegram",
        )

    def test_feature_shield(self) -> None:
        self.assertEqual(
            infer_hsp_route_hint("shield security settings"), "feature:shield"
        )

    def test_no_hint_for_general_chat(self) -> None:
        self.assertIsNone(infer_hsp_route_hint("Explain gas fees on TON"))

    def test_actions_from_navigate(self) -> None:
        actions = actions_from_route_hint("navigate:/swap")
        self.assertEqual(actions, [{"type": "navigate", "path": "/swap"}])

    def test_score_row_null_expect(self) -> None:
        ok, detail, detected = score_hsp_intent_row(
            {"prompt": "What is slippage when I swap tokens?", "expect_route": None}
        )
        self.assertTrue(ok, detail)
        self.assertIsNone(detected)


if __name__ == "__main__":
    unittest.main()
