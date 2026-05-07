"""Regression tests for natural-language Universal Brain control phrases (stdlib-only)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_SCRIPTS = _REPO / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from nl_controls import parse_control_action  # noqa: E402


class TestNlControls(unittest.TestCase):
    def test_show_session(self) -> None:
        a = parse_control_action("What is my current session scope?")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "show_session")

    def test_new_private_session(self) -> None:
        a = parse_control_action("Start a new private session")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "new_private_session")

    def test_set_scope(self) -> None:
        a = parse_control_action("Switch to scope demo-123")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_scope")
        self.assertEqual(a.value, "demo-123")

    def test_show_my_memories_lists(self) -> None:
        a = parse_control_action("Show my memories")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "list_memories")

    def test_export_memory(self) -> None:
        a = parse_control_action("Please export my memories as JSON.")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "export_memory")

    def test_forget_scope(self) -> None:
        a = parse_control_action("Delete all my memories for this chat.")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "forget_scope")

    def test_clear_session(self) -> None:
        a = parse_control_action("Clear my session notes.")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "clear_session")

    def test_set_trace(self) -> None:
        a = parse_control_action("Turn on the brain trace")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_trace")
        self.assertEqual(a.value, "on")

    def test_set_brief_verbosity(self) -> None:
        a = parse_control_action("Be brief")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_verbosity")
        self.assertEqual(a.value, "brief")

    def test_prefer_bullets(self) -> None:
        a = parse_control_action("Please use bullet points")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_reply_format")
        self.assertEqual(a.value, "bullets")

    def test_reset_reply_style(self) -> None:
        a = parse_control_action("Reset reply style")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "reset_reply_style")

    def test_faq_grounding_strict(self) -> None:
        a = parse_control_action("Strict FAQ")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_faq_grounding")
        self.assertEqual(a.value, "strict")

    def test_faq_grounding_normal(self) -> None:
        a = parse_control_action("Balanced FAQ")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_faq_grounding")
        self.assertEqual(a.value, "normal")

    def test_faq_grounding_relaxed(self) -> None:
        a = parse_control_action("FAQ plus general knowledge")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_faq_grounding")
        self.assertEqual(a.value, "relaxed")

    def test_long_line_not_faq_grounding_control(self) -> None:
        # Same intent words but over matcher length cap -> do not hijack real questions.
        long_line = (
            "For enterprise compliance we need strict faq alignment across every region and product line; "
            "summarize the gaps."
        )
        self.assertIsNone(parse_control_action(long_line))

    def test_audience_simple_explain_simply(self) -> None:
        a = parse_control_action("Explain simply")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_audience")
        self.assertEqual(a.value, "simple")

    def test_audience_simple_eli5(self) -> None:
        a = parse_control_action("eli5")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_audience")
        self.assertEqual(a.value, "simple")

    def test_audience_technical_expert_mode(self) -> None:
        a = parse_control_action("Expert mode")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_audience")
        self.assertEqual(a.value, "technical")

    def test_audience_normal(self) -> None:
        a = parse_control_action("Normal explanation level")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_audience")
        self.assertEqual(a.value, "normal")

    def test_answer_lead_tldr_first(self) -> None:
        a = parse_control_action("TLDR first")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_answer_lead")
        self.assertEqual(a.value, "tldr_first")

    def test_answer_lead_direct(self) -> None:
        a = parse_control_action("Answer directly")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_answer_lead")
        self.assertEqual(a.value, "direct")

    def test_answer_lead_default_opening(self) -> None:
        a = parse_control_action("Default answer structure")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_answer_lead")
        self.assertEqual(a.value, "normal")

    def test_explain_simply_not_in_long_question(self) -> None:
        self.assertIsNone(parse_control_action("Please explain simply what a transformer does in ML."))

    def test_long_question_not_style_control(self) -> None:
        # No brief/verbosity trigger phrase; ensures we do not treat deep questions as mode switches.
        self.assertIsNone(
            parse_control_action(
                "Explain quantum computing end-to-end including history, key experiments, and open problems."
            )
        )


if __name__ == "__main__":
    unittest.main()
