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

    def test_step_style_numbered(self) -> None:
        a = parse_control_action("Step by step")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_step_style")
        self.assertEqual(a.value, "numbered")

    def test_step_style_continuous(self) -> None:
        a = parse_control_action("No numbered steps")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_step_style")
        self.assertEqual(a.value, "continuous")

    def test_confidence_transparent(self) -> None:
        a = parse_control_action("Flag your assumptions")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_confidence_tone")
        self.assertEqual(a.value, "transparent")

    def test_confidence_assertive(self) -> None:
        a = parse_control_action("Don't hedge")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_confidence_tone")
        self.assertEqual(a.value, "assertive")

    def test_followup_suggest(self) -> None:
        a = parse_control_action("Suggest next steps")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_followup_close")
        self.assertEqual(a.value, "suggest")

    def test_followup_minimal(self) -> None:
        a = parse_control_action("No follow-up questions")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_followup_close")
        self.assertEqual(a.value, "minimal")

    def test_exposition_definitions_first(self) -> None:
        a = parse_control_action("Definitions first")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_exposition_order")
        self.assertEqual(a.value, "definitions_first")

    def test_exposition_intuition_first(self) -> None:
        a = parse_control_action("Intuition first")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_exposition_order")
        self.assertEqual(a.value, "intuition_first")

    def test_example_density_rich(self) -> None:
        a = parse_control_action("Include examples")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_example_density")
        self.assertEqual(a.value, "rich")

    def test_example_density_sparse(self) -> None:
        a = parse_control_action("Skip examples")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_example_density")
        self.assertEqual(a.value, "sparse")

    def test_comparison_pros_cons(self) -> None:
        a = parse_control_action("Use pros and cons")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_comparison_frame")
        self.assertEqual(a.value, "pros_cons")

    def test_comparison_narrative(self) -> None:
        a = parse_control_action("Compare in flowing prose")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_comparison_frame")
        self.assertEqual(a.value, "narrative")

    def test_register_formal(self) -> None:
        a = parse_control_action("Formal tone")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_register_tone")
        self.assertEqual(a.value, "formal")

    def test_register_casual(self) -> None:
        a = parse_control_action("Speak casually")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_register_tone")
        self.assertEqual(a.value, "casual")

    def test_code_fenced(self) -> None:
        a = parse_control_action("Use code fences")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_code_block_style")
        self.assertEqual(a.value, "fenced")

    def test_code_inline(self) -> None:
        a = parse_control_action("Inline code only")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_code_block_style")
        self.assertEqual(a.value, "inline")

    def test_analogy_prefer(self) -> None:
        a = parse_control_action("Use analogies")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_analogy_use")
        self.assertEqual(a.value, "prefer")

    def test_analogy_avoid(self) -> None:
        a = parse_control_action("No analogies")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_analogy_use")
        self.assertEqual(a.value, "avoid")

    def test_acronym_spell_out(self) -> None:
        a = parse_control_action("Spell out acronyms")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_acronym_style")
        self.assertEqual(a.value, "spell_out")

    def test_acronym_terse(self) -> None:
        a = parse_control_action("Assume I know acronyms")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_acronym_style")
        self.assertEqual(a.value, "terse")

    def test_clarify_first_on(self) -> None:
        a = parse_control_action("Clarify first")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_clarify_first")
        self.assertEqual(a.value, "on")

    def test_clarify_first_off(self) -> None:
        a = parse_control_action("No clarifying questions")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_clarify_first")
        self.assertEqual(a.value, "off")

    def test_speculation_strict(self) -> None:
        a = parse_control_action("No speculation")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_speculation")
        self.assertEqual(a.value, "strict")

    def test_speculation_creative(self) -> None:
        a = parse_control_action("Brainstorm freely")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_speculation")
        self.assertEqual(a.value, "creative")

    def test_math_detail_show_work(self) -> None:
        a = parse_control_action("Show your work")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_math_detail")
        self.assertEqual(a.value, "show_work")

    def test_math_detail_final_only(self) -> None:
        a = parse_control_action("Final answer only")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_math_detail")
        self.assertEqual(a.value, "final_only")

    def test_output_format_json(self) -> None:
        a = parse_control_action("Answer in JSON")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_output_format")
        self.assertEqual(a.value, "json")

    def test_output_format_plain(self) -> None:
        a = parse_control_action("Plain text only")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_output_format")
        self.assertEqual(a.value, "plain")

    def test_risk_posture_conservative(self) -> None:
        a = parse_control_action("Be risk averse")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_risk_posture")
        self.assertEqual(a.value, "conservative")

    def test_risk_posture_pragmatic(self) -> None:
        a = parse_control_action("Be pragmatic")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_risk_posture")
        self.assertEqual(a.value, "pragmatic")

    def test_actionability_commands(self) -> None:
        a = parse_control_action("Make it actionable")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_actionability")
        self.assertEqual(a.value, "commands")

    def test_actionability_conceptual(self) -> None:
        a = parse_control_action("No commands")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_actionability")
        self.assertEqual(a.value, "conceptual")

    def test_quote_style_quote(self) -> None:
        a = parse_control_action("Quote the FAQ excerpts")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_quote_style")
        self.assertEqual(a.value, "quote")

    def test_quote_style_paraphrase(self) -> None:
        a = parse_control_action("Paraphrase only")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_quote_style")
        self.assertEqual(a.value, "paraphrase")

    def test_quote_style_normal(self) -> None:
        a = parse_control_action("Default quote style")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_quote_style")
        self.assertEqual(a.value, "normal")

    def test_table_style_prefer(self) -> None:
        a = parse_control_action("Use tables")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_table_style")
        self.assertEqual(a.value, "prefer")

    def test_table_style_avoid(self) -> None:
        a = parse_control_action("Avoid tables")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_table_style")
        self.assertEqual(a.value, "avoid")

    def test_table_style_normal(self) -> None:
        a = parse_control_action("Reset tables")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_table_style")
        self.assertEqual(a.value, "normal")


if __name__ == "__main__":
    unittest.main()
