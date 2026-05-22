"""Regression tests for natural-language Universal Brain control phrases (stdlib-only)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_SCRIPTS = _REPO / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from nl_controls import analyze_embedded_prompt_signals, parse_control_action  # noqa: E402


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

    def test_emoji_style_include(self) -> None:
        a = parse_control_action("Use emoji")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_emoji_style")
        self.assertEqual(a.value, "include")

    def test_emoji_style_avoid(self) -> None:
        a = parse_control_action("No emoji")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_emoji_style")
        self.assertEqual(a.value, "avoid")

    def test_emoji_style_normal(self) -> None:
        a = parse_control_action("Default emoji style")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_emoji_style")
        self.assertEqual(a.value, "normal")

    def test_section_headings_prefer(self) -> None:
        a = parse_control_action("Use section headings")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_section_headings")
        self.assertEqual(a.value, "prefer")

    def test_section_headings_avoid(self) -> None:
        a = parse_control_action("Flat answer")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_section_headings")
        self.assertEqual(a.value, "avoid")

    def test_section_headings_normal(self) -> None:
        a = parse_control_action("Reset headings")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_section_headings")
        self.assertEqual(a.value, "normal")

    def test_term_emphasis_highlight(self) -> None:
        a = parse_control_action("Bold key terms")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_term_emphasis")
        self.assertEqual(a.value, "highlight")

    def test_term_emphasis_minimal(self) -> None:
        a = parse_control_action("Minimal bold")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_term_emphasis")
        self.assertEqual(a.value, "minimal")

    def test_term_emphasis_normal(self) -> None:
        a = parse_control_action("Default emphasis")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_term_emphasis")
        self.assertEqual(a.value, "normal")

    def test_counterpoint_challenge(self) -> None:
        a = parse_control_action("Challenge my assumptions")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_counterpoint_tone")
        self.assertEqual(a.value, "challenge")

    def test_counterpoint_supportive(self) -> None:
        a = parse_control_action("Be supportive")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_counterpoint_tone")
        self.assertEqual(a.value, "supportive")

    def test_counterpoint_normal(self) -> None:
        a = parse_control_action("Reset counterpoints")
        self.assertIsNotNone(a)
        self.assertEqual(a.name, "set_counterpoint_tone")
        self.assertEqual(a.value, "normal")


class TestEmbeddedPromptSignals(unittest.TestCase):
    def test_tradeoffs_imply_pros_cons(self) -> None:
        msg = (
            "We are choosing a primary datastore for OLTP. "
            "What are the practical tradeoffs between PostgreSQL and MySQL for our team?"
        )
        o, e, t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("comparison_frame"), "pros_cons")
        self.assertFalse(e)
        self.assertEqual(t, [])

    def test_compare_versus_imply_pros_cons(self) -> None:
        msg = "For a greenfield API, compare gRPC versus REST in terms of operability and client ergonomics."
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("comparison_frame"), "pros_cons")

    def test_embedded_comparison_frame_narrative(self) -> None:
        msg = (
            "We are choosing between Vitess and Citus for sharding our Postgres workload on GCP. "
            "Compare them in flowing prose for a narrative comparison—no pros and cons sections, just continuous prose."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("comparison_frame"), "narrative")

    def test_embedded_comparison_frame_conflict_skips(self) -> None:
        msg = (
            "Help me decide between Kafka and Pulsar for our event backbone. List pros and cons for each, "
            "but also compare in flowing prose with no pros/cons sections—pick one comparison layout."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertIsNone(o.get("comparison_frame"))

    def test_short_message_no_structural_signals(self) -> None:
        o, e, t = analyze_embedded_prompt_signals("What is the capital of France?")
        self.assertEqual(o, {})
        self.assertEqual(e, [])
        self.assertEqual(t, [])

    def test_how_to_install_numbered_steps(self) -> None:
        msg = (
            "I am on Ubuntu 22.04 and need TLS for an internal service. "
            "How do I install certbot and configure nginx for automatic renewals?"
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("step_style"), "numbered")

    def test_markdown_table_prefer(self) -> None:
        msg = (
            "Summarize the SLA tiers we discussed: latency budget, error rate, and support response time "
            "in a markdown table so I can paste it into a doc."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("table_style"), "prefer")

    def test_embedded_table_style_avoid(self) -> None:
        msg = (
            "Compare our three on-call escalation policies for the security review. "
            "Keep it in prose only—no tables and avoid tabular format so it reads well in email."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("table_style"), "avoid")

    def test_embedded_table_style_conflict_skips(self) -> None:
        msg = (
            "List feature flags for the billing service rollout. Put this in a markdown table, "
            "but also no tables and without a table—pick one table style only."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertIsNone(o.get("table_style"))

    def test_answer_in_spanish_short(self) -> None:
        msg = "What is 2+2? Please answer in spanish."
        o, e, t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o, {})
        self.assertEqual(len(e), 1)
        self.assertIn("Spanish", e[0])
        self.assertEqual(t, ["language"])

    def test_no_false_positive_explain_simply(self) -> None:
        msg = (
            "Our SRE team wants a calm incident review template. "
            "Explain simply how we should structure blameless postmortems for outages."
        )
        o, e, _t = analyze_embedded_prompt_signals(msg)
        self.assertNotIn("French", " ".join(e))
        self.assertIsNone(o.get("reply_format"))

    def test_code_only_trace(self) -> None:
        msg = (
            "I need a Python 3 function that returns the sha256 hex digest of a utf-8 string. "
            "Code only, no explanation."
        )
        o, e, t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o, {})
        self.assertIn("code_only", t)
        self.assertTrue(any("code-first" in x for x in e))

    def test_embedded_code_explained_trace(self) -> None:
        msg = (
            "I'm wiring a FastAPI endpoint that validates JWT bearer tokens against our OIDC issuer. "
            "Show me the Python code and explain what each part does—not code only, I need a walkthrough."
        )
        o, e, t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o, {})
        self.assertIn("code_explained", t)
        self.assertNotIn("code_only", t)
        self.assertTrue(any("code with explanation" in x.lower() for x in e))

    def test_code_only_vs_explained_conflict_skips(self) -> None:
        msg = (
            "Write a bash script that rotates nginx access logs daily with logrotate. "
            "Code only please, but also explain the code line by line for my team."
        )
        o, e, t = analyze_embedded_prompt_signals(msg)
        self.assertNotIn("code_only", t)
        self.assertNotIn("code_explained", t)
        self.assertEqual(o, {})

    def test_embedded_cite_sources_trace(self) -> None:
        msg = (
            "Our compliance team pasted several FAQ excerpts about enterprise refund windows and SLA credits. "
            "Please cite your sources and attribute each claim with links—I need audit-ready references."
        )
        o, e, t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o, {})
        self.assertIn("cite_sources", t)
        self.assertTrue(any("source attribution" in x.lower() for x in e))

    def test_embedded_cite_minimal_trace(self) -> None:
        msg = (
            "Using the policy excerpt below about international shipping times, summarize the key facts "
            "in plain prose with no source links or footnotes—just the answer for our support macro."
        )
        o, e, t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o, {})
        self.assertIn("cite_minimal", t)
        self.assertNotIn("cite_sources", t)

    def test_cite_sources_vs_minimal_conflict_skips(self) -> None:
        msg = (
            "We retrieved web search snippets about the latest EU AI Act enforcement timeline. "
            "Cite your sources with links, but also answer without citing and no source links please."
        )
        o, e, t = analyze_embedded_prompt_signals(msg)
        self.assertNotIn("cite_sources", t)
        self.assertNotIn("cite_minimal", t)

    def test_embedded_ranked_options_trace(self) -> None:
        msg = (
            "We are choosing a vector database for our RAG pipeline—Pinecone, Weaviate, pgvector, and Qdrant "
            "are on the table. Rank these options in order of priority for a small team with strict cost caps "
            "and tell me which platform we should pick first."
        )
        o, e, t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o, {})
        self.assertIn("ranked_options", t)
        self.assertTrue(any("ranked recommendation" in x.lower() for x in e))

    def test_ranked_options_vs_no_rank_conflict_skips(self) -> None:
        msg = (
            "Our architecture review compares three deployment approaches: blue-green, canary, and rolling. "
            "Rank them best to worst for our SLO, but also say order doesn't matter and no ranking—all equal."
        )
        o, e, t = analyze_embedded_prompt_signals(msg)
        self.assertNotIn("ranked_options", t)

    def test_embedded_checklist_trace(self) -> None:
        msg = (
            "We are rolling out SOC2 access reviews for engineering managers this quarter. "
            "Give me an actionable checklist format for quarterly user-access recertification with "
            "tick-box items I can paste into Notion."
        )
        o, e, t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o, {})
        self.assertIn("checklist", t)
        self.assertNotIn("no_checklist", t)
        self.assertTrue(any("markdown checklist" in x.lower() for x in e))

    def test_embedded_no_checklist_trace(self) -> None:
        msg = (
            "Our incident response playbook needs a concise postmortem outline for on-call engineers "
            "after a production outage. Write the steps in plain prose with no checklist and don't use checkboxes."
        )
        o, e, t = analyze_embedded_prompt_signals(msg)
        self.assertIn("no_checklist", t)
        self.assertNotIn("checklist", t)

    def test_checklist_vs_no_checklist_conflict_skips(self) -> None:
        msg = (
            "We're planning a Kubernetes cluster upgrade runbook for the platform team. "
            "Format as a checklist with tick boxes, but also say not a checklist and avoid checkboxes."
        )
        o, e, t = analyze_embedded_prompt_signals(msg)
        self.assertNotIn("checklist", t)
        self.assertNotIn("no_checklist", t)

    def test_embedded_pseudocode_trace(self) -> None:
        msg = (
            "I'm preparing for a algorithms interview and need to explain how merge sort works on linked lists. "
            "Give me pseudocode only—language agnostic, not runnable Python or Java."
        )
        o, e, t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o, {})
        self.assertIn("pseudocode", t)
        self.assertNotIn("runnable_code", t)
        self.assertTrue(any("pseudocode" in x.lower() for x in e))

    def test_embedded_runnable_code_trace(self) -> None:
        msg = (
            "Our CI pipeline needs a script to binary-search a sorted JSON lines file for a record id. "
            "Show runnable Python code I can copy-paste into pytest—executable working code, not abstract pseudocode."
        )
        o, e, t = analyze_embedded_prompt_signals(msg)
        self.assertIn("runnable_code", t)
        self.assertNotIn("pseudocode", t)

    def test_pseudocode_vs_runnable_conflict_skips(self) -> None:
        msg = (
            "Help me implement Dijkstra's algorithm for a weighted graph homework problem. "
            "Pseudocode only please, but also give runnable production-ready code I can execute."
        )
        o, e, t = analyze_embedded_prompt_signals(msg)
        self.assertNotIn("pseudocode", t)
        self.assertNotIn("runnable_code", t)

    def test_embedded_options_n_three_trace(self) -> None:
        msg = (
            "Our startup is picking a first observability stack for a five-person backend team on Kubernetes. "
            "Give me exactly three distinct options for tools—no more alternatives than that."
        )
        o, e, t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o, {})
        self.assertIn("options_n=3", t)
        self.assertTrue(any("exactly 3" in x for x in e))

    def test_embedded_options_n_top_five(self) -> None:
        msg = (
            "We're redesigning our API gateway and need a short list of vendor approaches for rate limiting "
            "and auth at the edge. Suggest the top five recommendations as separate options for leadership."
        )
        o, _e, t = analyze_embedded_prompt_signals(msg)
        self.assertIn("options_n=5", t)

    def test_options_n_conflict_two_counts_skips(self) -> None:
        msg = (
            "Help me choose a managed Postgres provider for our EU SaaS product with strict GDPR needs. "
            "Give me exactly three options but also provide exactly five alternatives in the same answer."
        )
        o, e, t = analyze_embedded_prompt_signals(msg)
        self.assertFalse(any(x.startswith("options_n=") for x in t))

    def test_embedded_diagram_mermaid_trace(self) -> None:
        msg = (
            "I'm documenting our event-driven order pipeline from the API gateway through Kafka to "
            "downstream fulfillment workers. Include a simple Mermaid sequence diagram showing the main "
            "services and retries—keep labels short for a design review."
        )
        o, e, t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o, {})
        self.assertIn("diagram", t)
        self.assertNotIn("no_diagram", t)
        self.assertTrue(any("mermaid" in x.lower() for x in e))

    def test_embedded_no_diagram_trace(self) -> None:
        msg = (
            "Explain how our three-tier web application handles session stickiness behind the load balancer "
            "for new engineers. Text-only answer please—no diagrams, flowcharts, or Mermaid blocks."
        )
        o, e, t = analyze_embedded_prompt_signals(msg)
        self.assertIn("no_diagram", t)
        self.assertNotIn("diagram", t)

    def test_diagram_vs_no_diagram_conflict_skips(self) -> None:
        msg = (
            "Map the CI/CD flow from GitHub Actions through staging to production for our platform team. "
            "Draw a Mermaid flowchart, but also say no diagrams and text only in the same message."
        )
        o, e, t = analyze_embedded_prompt_signals(msg)
        self.assertNotIn("diagram", t)
        self.assertNotIn("no_diagram", t)

    def test_embedded_risks_first_trace(self) -> None:
        msg = (
            "We're planning a phased rollout of real-time ML fraud scoring in our checkout service. "
            "Start with risks and downsides first—what could go wrong operationally before any benefits."
        )
        o, e, t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o, {})
        self.assertIn("risks_first", t)
        self.assertNotIn("benefits_first", t)
        self.assertTrue(any("risks" in x.lower() and "first" in x.lower() for x in e))

    def test_embedded_benefits_first_trace(self) -> None:
        msg = (
            "Our product team is pitching a migration from a Django monolith to a modular monolith architecture. "
            "Lead with benefits and upsides first for the steering committee, then note the main caveats."
        )
        o, e, t = analyze_embedded_prompt_signals(msg)
        self.assertIn("benefits_first", t)
        self.assertNotIn("risks_first", t)

    def test_risks_vs_benefits_first_conflict_skips(self) -> None:
        msg = (
            "We're evaluating whether to ship a public GraphQL API for partners on our B2B platform. "
            "Risks first in your answer, but also benefits first and lead with the positives please."
        )
        o, e, t = analyze_embedded_prompt_signals(msg)
        self.assertNotIn("risks_first", t)
        self.assertNotIn("benefits_first", t)

    def test_length_cap_words_trace(self) -> None:
        msg = (
            "Explain how TCP slow start interacts with modern BBR congestion control for a junior network engineer. "
            "Keep the answer in under 90 words."
        )
        o, e, t = analyze_embedded_prompt_signals(msg)
        self.assertIn("len_cap=90w", t)
        self.assertTrue(any("90" in x and "words" in x for x in e))

    def test_guided_discovery_hints_only(self) -> None:
        msg = (
            "I'm learning graph algorithms and stuck on why Dijkstra fails with negative edges. "
            "Please give hints only; don't hand me the full solution yet—I want to work it out myself."
        )
        o, e, t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o, {})
        self.assertIn("guided", t)
        self.assertTrue(any("guided discovery" in x.lower() for x in e))

    def test_embedded_full_solution_not_hints(self) -> None:
        msg = (
            "I'm stuck on this dynamic programming homework problem about longest increasing subsequence. "
            "Give me the full worked solution with the recurrence and an example—don't do hints only."
        )
        o, e, t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o, {})
        self.assertIn("full_solution", t)
        self.assertTrue(any("complete solution" in x.lower() for x in e))

    def test_embedded_guided_vs_full_solution_conflict_skips(self) -> None:
        msg = (
            "Help me prove why the greedy interval scheduling algorithm is optimal. "
            "Hints only please, but also give me the full complete solution now—pick one mode."
        )
        o, e, t = analyze_embedded_prompt_signals(msg)
        self.assertNotIn("guided", t)
        self.assertNotIn("full_solution", t)

    def test_embedded_red_team_sets_challenge(self) -> None:
        msg = (
            "We're about to launch a public API behind a single shared API key for our first 50 beta users. "
            "Red team this rollout plan: what am I missing on abuse, key rotation, and rate limits?"
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("counterpoint_tone"), "challenge")

    def test_embedded_critique_respects_soft_tone(self) -> None:
        msg = (
            "Here is my deployment design for the payments service. Don't challenge me too hard—be gentle—but "
            "sanity check whether the rollback story is credible."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertIsNone(o.get("counterpoint_tone"))

    def test_embedded_counterpoint_supportive(self) -> None:
        msg = (
            "I'm pitching a phased rollout plan to leadership next week for our new analytics API. "
            "Assume good intent and be supportive—give gentle feedback on my proposal and frame improvements as next steps."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("counterpoint_tone"), "supportive")

    def test_embedded_counterpoint_conflict_skips(self) -> None:
        msg = (
            "Review my migration plan for the billing database. Red team this rollout plan and poke holes, "
            "but also be supportive and assume good intent—pick one counterpoint tone only."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertIsNone(o.get("counterpoint_tone"))

    def test_ephemeral_off_the_record(self) -> None:
        msg = (
            "Off the record: if a teammate pasted an AWS secret into Slack by mistake, what is the fastest containment checklist? "
            "Don't remember this question—I don't want it in session notes."
        )
        o, e, t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o, {})
        self.assertIn("ephemeral", t)
        self.assertTrue(any("ephemeral intent" in x.lower() for x in e))

    def test_ephemeral_no_false_positive_remember_to(self) -> None:
        msg = "Please remind me to buy milk after the deploy window closes tonight."
        o, e, t = analyze_embedded_prompt_signals(msg)
        self.assertNotIn("ephemeral", t)

    def test_accessibility_screen_reader_friendly(self) -> None:
        msg = (
            "We need to publish an internal FAQ about our refund window and chargebacks for support staff. "
            "Please make the answer screen reader friendly with clear headings; some agents use NVDA on Windows."
        )
        o, e, t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o, {})
        self.assertIn("a11y", t)
        self.assertTrue(any("screen-reader" in x.lower() or "accessibility" in x.lower() for x in e))

    def test_accessibility_no_false_positive_what_is_wcag(self) -> None:
        msg = "In one sentence, what is WCAG?"
        o, e, t = analyze_embedded_prompt_signals(msg)
        self.assertNotIn("a11y", t)
        self.assertFalse(any("screen-reader" in x.lower() for x in e))

    def test_embedded_eli5_sets_audience_simple(self) -> None:
        msg = (
            "Our PTA asked me to explain to other parents why TLS matters for school websites. "
            "What is TLS in practice, eli5, but still directionally correct for HTTPS?"
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("audience"), "simple")

    def test_embedded_beginner_respects_expert_intent(self) -> None:
        msg = (
            "Assume I'm technical and want a deep dive, but also give one eli5 sentence at the end for the abstract. "
            "How does CRDT conflict resolution differ from OT for collaborative text?"
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertIsNone(o.get("audience"))

    def test_embedded_technical_audience_sets_technical(self) -> None:
        msg = (
            "Our platform team is debugging cross-region Postgres failover lag during cutovers. "
            "Assume I'm technical and explain the internals-focused replication path—skip the basics on WAL shipping."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("audience"), "technical")

    def test_embedded_technical_respects_beginner_intent(self) -> None:
        msg = (
            "I'm a total beginner to Kubernetes networking. Also assume I'm technical and give a deep technical "
            "walkthrough of CNI plugins—pick one audience level only."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertIsNone(o.get("audience"))

    def test_embedded_register_formal_board_ready(self) -> None:
        msg = (
            "Our startup is preparing the Q2 board deck. Draft a board-ready paragraph explaining why we chose "
            "multi-region Postgres over a managed document store for our audit trail requirements."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("register_tone"), "formal")

    def test_embedded_register_casual_slack(self) -> None:
        msg = (
            "The deploy finished late last night and metrics look fine. Help me write a short Slack message to the team "
            "celebrating the win—keep it casual and friendly, no corporate buzzwords."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("register_tone"), "casual")

    def test_embedded_register_ambiguous_skips(self) -> None:
        msg = (
            "Draft a client-facing email that still sounds like a casual Slack message to engineers; "
            "we want both tones at once which is confusing."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertIsNone(o.get("register_tone"))

    def test_embedded_json_output_in_prose(self) -> None:
        msg = (
            "We need a tiny status blob for CI: return json with keys ok, message, and retry_after_seconds "
            "summarizing whether the deploy gate passed. Keep keys stable for parsers."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("output_format"), "json")

    def test_embedded_json_respects_plain_text_opt_out(self) -> None:
        msg = (
            "The API can return json but for this ticket please explain in plain text only what fields mean; "
            "no json block in the answer."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertIsNone(o.get("output_format"))

    def test_embedded_output_format_plain(self) -> None:
        msg = (
            "We're drafting customer-facing release notes for the mobile app v4.2 security patch. "
            "Explain what changed in plain text only—no JSON or structured output blocks in your reply."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("output_format"), "plain")

    def test_embedded_verbosity_brief(self) -> None:
        msg = (
            "I'm pasting this into a Slack thread during an incident. "
            "Be brief and keep your answer short—just the essentials on what likely caused the 502 spike."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("verbosity"), "brief")

    def test_embedded_verbosity_detailed(self) -> None:
        msg = (
            "Our platform team is evaluating service mesh options for mTLS between internal microservices. "
            "Go deeper and explain thoroughly how Istio compares to Linkerd for our Kubernetes footprint."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("verbosity"), "detailed")

    def test_embedded_verbosity_conflict_skips(self) -> None:
        msg = (
            "Summarize the outage postmortem for executives. Be brief and keep it short, "
            "but also go deeper with a comprehensive explanation—pick one verbosity level."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertIsNone(o.get("verbosity"))

    def test_embedded_speculation_strict_in_prose(self) -> None:
        msg = (
            "We're writing an incident report for leadership about yesterday's partial outage. "
            "Stick to facts we can support from logs; if you are not sure about root cause, say so clearly—no guessing."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("speculation"), "strict")

    def test_embedded_speculation_skips_when_brainstorm_requested(self) -> None:
        msg = (
            "Brainstorm freely about future product directions, but also don't guess current revenue numbers—"
            "only cite public figures."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertIsNone(o.get("speculation"))

    def test_embedded_speculation_creative(self) -> None:
        msg = (
            "We're kicking off a product workshop on improving first-week activation for new users. "
            "Brainstorm freely about onboarding UX improvements—wild ideas are welcome if you label assumptions."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("speculation"), "creative")

    def test_embedded_answer_lead_tldr_bluf(self) -> None:
        msg = (
            "We need to brief the CFO in two minutes on why our cloud egress bill spiked last month. "
            "Please use BLUF: bottom line up front, then the supporting factors and what we already mitigated."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("answer_lead"), "tldr_first")

    def test_embedded_answer_lead_direct(self) -> None:
        msg = (
            "Explain how object storage lifecycle policies interact with versioning. Answer directly without a tldr; "
            "I need continuous prose for a design doc footnote."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("answer_lead"), "direct")

    def test_embedded_answer_lead_conflict_skips(self) -> None:
        msg = (
            "Brief the team on the outage timeline. Use BLUF and summary first, but also answer directly "
            "and skip the summary—pick one opening style only."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertIsNone(o.get("answer_lead"))

    def test_embedded_actionability_commands_kubectl(self) -> None:
        msg = (
            "Our staging cluster is on EKS 1.29. I need to verify whether the metrics-server addon is installed. "
            "Include kubectl commands I can copy-paste into my terminal to list addons and describe the deployment."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("actionability"), "commands")

    def test_embedded_actionability_conceptual_only(self) -> None:
        msg = (
            "Compare blue-green vs canary deploy strategies for API rollouts. Conceptual only—no shell commands—"
            "I want tradeoffs for an architecture review slide."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("actionability"), "conceptual")

    def test_embedded_actionability_conflict_skips(self) -> None:
        msg = (
            "Help me debug our Redis failover. Include kubectl commands I can paste into the terminal, "
            "but also conceptual only with no commands—pick one actionability style."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertIsNone(o.get("actionability"))

    def test_embedded_reply_format_bullets(self) -> None:
        msg = (
            "Summarize the main risks of adopting serverless Postgres for our fintech control plane. "
            "Use bullet points and format the answer as bullets so I can paste into a slide."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("reply_format"), "bullets")

    def test_embedded_reply_format_prose(self) -> None:
        msg = (
            "Explain how our webhook retry policy should behave during partial outages for the partner API. "
            "No bullets—plain paragraphs only for a legal review memo footnote."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("reply_format"), "prose")

    def test_embedded_reply_format_conflict_skips(self) -> None:
        msg = (
            "Outline our incident communication plan for customers. Use bullet points for the timeline, "
            "but also prose only with no bullets—pick one reply format."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertIsNone(o.get("reply_format"))

    def test_embedded_assumptions_limitations_sets_transparent_confidence(self) -> None:
        msg = (
            "We're drafting an internal memo on moving our batch jobs from cron to a managed scheduler. "
            "Please state your assumptions and limitations clearly—what breaks if our jobs are not idempotent?"
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("confidence_tone"), "transparent")

    def test_embedded_assumptions_respects_decisive_opt_out(self) -> None:
        msg = (
            "We need a vendor pick for log aggregation. Be decisive and sound confident in the recommendation, "
            "but also list the main assumptions behind the choice in one short paragraph."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertIsNone(o.get("confidence_tone"))

    def test_embedded_assumptions_respects_skip_assumptions(self) -> None:
        msg = (
            "Summarize why we might shard Postgres by tenant for our SaaS control plane. "
            "Skip the assumptions section—just give the operational tradeoffs in prose."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertIsNone(o.get("confidence_tone"))

    def test_embedded_confidence_tone_assertive(self) -> None:
        msg = (
            "We need a vendor pick for log aggregation by Friday for the ops review. "
            "Be decisive, don't hedge, and give firm answers—pick one option and justify it briefly."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("confidence_tone"), "assertive")

    def test_embedded_step_style_numbered(self) -> None:
        msg = (
            "I'm onboarding a new SRE who has never used our Helm chart before. "
            "Walk me through how to install the observability stack step by step on a fresh EKS cluster."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("step_style"), "numbered")

    def test_embedded_step_style_continuous(self) -> None:
        msg = (
            "Explain how our canary deployment controller decides when to promote a release, "
            "but use continuous prose only—no numbered steps—for an architecture blog draft."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("step_style"), "continuous")

    def test_embedded_step_style_conflict_skips(self) -> None:
        msg = (
            "How do I migrate our Postgres from RDS to Aurora? Show me how step by step, "
            "but also prose without steps and no numbered steps—pick one step style."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertIsNone(o.get("step_style"))

    def test_embedded_example_density_rich_worked_example(self) -> None:
        msg = (
            "Our junior engineers confuse eventual consistency with read-your-writes in replicated databases. "
            "Explain the difference and walk me through a toy example with two replicas so they can picture failure modes."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("example_density"), "rich")

    def test_embedded_example_density_sparse_theory_only(self) -> None:
        msg = (
            "I need a crisp architecture overview of CQRS versus plain CRUD for an internal wiki. "
            "Keep it abstract and theory only—skip examples; I just need definitions and tradeoffs."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("example_density"), "sparse")

    def test_embedded_example_density_ambiguous_skips(self) -> None:
        msg = (
            "For onboarding docs: explain idempotency keys for payment retries. "
            "Skip examples in the prose, but also walk me through a toy example—pick one style only."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertIsNone(o.get("example_density"))

    def test_embedded_exposition_definitions_first(self) -> None:
        msg = (
            "I'm writing lecture notes on PAC learning for CS undergrads who know probability but not ML notation. "
            "Please define terms first—hypothesis class, sample complexity, probably approximately correct—before "
            "you walk through any theorems."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("exposition_order"), "definitions_first")

    def test_embedded_exposition_intuition_first(self) -> None:
        msg = (
            "Our product team keeps confusing eventual consistency with linearizability when we talk to customers. "
            "Give intuition before the formal definitions so the tradeoff story lands before the mathy bits."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("exposition_order"), "intuition_first")

    def test_embedded_exposition_conflict_skips(self) -> None:
        msg = (
            "Explain how gradient checkpointing saves memory in transformer training. "
            "I want definitions first for the notation, but also big picture first so the team stays motivated—"
            "please pick one ordering only."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertIsNone(o.get("exposition_order"))

    def test_embedded_followup_close_minimal(self) -> None:
        msg = (
            "I need a tight internal memo on why we are postponing the monolith split. "
            "Please finish crisply—no questions at the end—this will be pasted into Confluence as-is."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("followup_close"), "minimal")

    def test_embedded_followup_close_suggest(self) -> None:
        msg = (
            "We finished the security review for the public API and have findings scattered across three docs. "
            "Summarize the top risks and end with actionable next steps our team should schedule next sprint."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("followup_close"), "suggest")

    def test_embedded_followup_close_conflict_skips(self) -> None:
        msg = (
            "Draft a blameless postmortem outline for the checkout outage. "
            "Suggest next steps at the end for leadership, but also don't ask if I need anything else—"
            "I'm pasting into email and want one consistent closing style."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertIsNone(o.get("followup_close"))

    def test_embedded_clarify_first_on(self) -> None:
        msg = (
            "We're picking between two observability vendors for a hybrid cloud footprint and the pricing pages "
            "are ambiguous about per-host vs per-metric billing. If anything is unclear ask me first about our "
            "cardinality and retention needs before you recommend a shortlist."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("clarify_first"), "on")

    def test_embedded_clarify_first_off(self) -> None:
        msg = (
            "I need a one-page explainer on why we chose gRPC for internal east-west traffic for an exec readout. "
            "No clarifying questions please—answer immediately even if the spec is incomplete; I'll edit tone later."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("clarify_first"), "off")

    def test_embedded_clarify_first_conflict_skips(self) -> None:
        msg = (
            "Help me draft acceptance criteria for the new SSO rollout. "
            "Ask clarifying questions before you answer about our IdP, but also don't interrogate me first—"
            "I need one consistent interaction style in this thread."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertIsNone(o.get("clarify_first"))

    def test_embedded_section_headings_prefer(self) -> None:
        msg = (
            "We're publishing an internal runbook for the on-call rotation after the last database failover drill. "
            "Please structure the answer with clear headings so each escalation tier is easy to skim in the wiki."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("section_headings"), "prefer")

    def test_embedded_section_headings_avoid(self) -> None:
        msg = (
            "I need to paste your reply into a vendor email thread where markdown renders badly. "
            "Give a flat answer with no section headings—continuous prose only—and keep it under one screen."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("section_headings"), "avoid")

    def test_embedded_section_headings_conflict_skips(self) -> None:
        msg = (
            "Summarize our API rate-limiting policy for the compliance workshop. "
            "Use markdown headings for each audience, but also avoid markdown headings because some attendees "
            "read from plain-text slides—pick one format only."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertIsNone(o.get("section_headings"))

    def test_embedded_analogy_use_prefer(self) -> None:
        msg = (
            "Our interns struggle with why write-ahead logs make crash recovery safer than plain btree flushes. "
            "Please use a helpful analogy from everyday life before you get into the filesystem jargon."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("analogy_use"), "prefer")

    def test_embedded_analogy_use_avoid(self) -> None:
        msg = (
            "I'm briefing compliance reviewers who dislike informal language. Explain differential privacy "
            "with literal explanations only—no analogies or metaphors—and cite standard definitions."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("analogy_use"), "avoid")

    def test_embedded_analogy_use_conflict_skips(self) -> None:
        msg = (
            "Help the sales engineers understand why our multi-tenant cache isolates noisy neighbors. "
            "Map it to an everyday example for intuition, but also stick to literal technical description only—"
            "pick one style for this answer."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertIsNone(o.get("analogy_use"))

    def test_embedded_term_emphasis_highlight(self) -> None:
        msg = (
            "We're sending this incident summary to directors who skim on mobile. "
            "Please bold the key terms and highlight important phrases so the timeline is easy to scan."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("term_emphasis"), "highlight")

    def test_embedded_term_emphasis_minimal(self) -> None:
        msg = (
            "I need a neutral postmortem paragraph for our public status page. "
            "Keep bold to a minimum and don't overuse bold—plain professional prose only."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("term_emphasis"), "minimal")

    def test_embedded_term_emphasis_conflict_skips(self) -> None:
        msg = (
            "Draft release notes for v2.4. Bold the key terms for scanning, but also avoid excessive bold "
            "because legal wants one consistent style—pick one emphasis level only."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertIsNone(o.get("term_emphasis"))

    def test_embedded_acronym_style_spell_out(self) -> None:
        msg = (
            "Our compliance team will read this SOC2 control mapping. "
            "Please spell out acronyms on first use and define acronyms when you introduce PCI, SSO, and KMS terms."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("acronym_style"), "spell_out")

    def test_embedded_acronym_style_terse(self) -> None:
        msg = (
            "This is an internal architecture review for senior SREs who already know our stack. "
            "Assume we know acronyms—keep acronyms as-is and skip acronym expansion in the write-up."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("acronym_style"), "terse")

    def test_embedded_acronym_style_conflict_skips(self) -> None:
        msg = (
            "Prepare a briefing for mixed audiences. Spell out acronyms for newcomers, but also "
            "don't expand acronyms because the appendix is for staff engineers only—use one style."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertIsNone(o.get("acronym_style"))

    def test_embedded_risk_posture_conservative(self) -> None:
        msg = (
            "We're planning a blue-green cutover for the payments API this weekend. "
            "Please err on the side of safety and prefer low-risk options that minimize blast radius if we rollback."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("risk_posture"), "conservative")

    def test_embedded_risk_posture_pragmatic(self) -> None:
        msg = (
            "Our startup needs to unblock a broken nightly deploy before Monday's demo. "
            "Be pragmatic about the fix—optimize for speed and avoid over-engineering a permanent platform."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("risk_posture"), "pragmatic")

    def test_embedded_risk_posture_conflict_skips(self) -> None:
        msg = (
            "Recommend how we should patch the auth service. Err on the side of safety for production, "
            "but also ship fast and optimize for speed this week—pick one risk posture only."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertIsNone(o.get("risk_posture"))

    def test_embedded_quote_style_quote(self) -> None:
        msg = (
            "Using the FAQ excerpts you retrieve about data retention, please quote the FAQ excerpts "
            "with direct quotes from the policy before you explain what it means for EU customers."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("quote_style"), "quote")

    def test_embedded_quote_style_paraphrase(self) -> None:
        msg = (
            "I need a support answer grounded in our knowledge base article on refunds. "
            "Paraphrase the FAQ in your own words and do not quote the excerpt verbatim for the customer email."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("quote_style"), "paraphrase")

    def test_embedded_quote_style_conflict_skips(self) -> None:
        msg = (
            "Review the policy documentation excerpt about SSO. Quote the FAQ excerpts with verbatim passages, "
            "but also paraphrase only and summarize the policy in your own words—pick one style."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertIsNone(o.get("quote_style"))

    def test_embedded_emoji_style_include(self) -> None:
        msg = (
            "I'm drafting a friendly onboarding checklist for new hires in Slack. "
            "Use a few tasteful emoji in your reply when they help scanning, but keep the steps clear."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("emoji_style"), "include")

    def test_embedded_emoji_style_avoid(self) -> None:
        msg = (
            "This needs to go into our formal investor update email template. "
            "No emoji in your reply—keep it professional and emoji-free tone throughout."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("emoji_style"), "avoid")

    def test_embedded_emoji_style_conflict_skips(self) -> None:
        msg = (
            "Write a short morale note for the team channel. Use emoji when helpful, "
            "but also avoid emoji and keep the reply emoji-free—pick one style only."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertIsNone(o.get("emoji_style"))

    def test_embedded_faq_grounding_strict(self) -> None:
        msg = (
            "I'm replying to a billing dispute using the support FAQ retrieval you inject. "
            "Only use the FAQ excerpts you were given and stick to the FAQ—if a detail is not in the FAQ say so."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("faq_grounding"), "strict")

    def test_embedded_faq_grounding_relaxed(self) -> None:
        msg = (
            "Summarize our knowledge base FAQ excerpts about SSO timeouts for the customer, "
            "but FAQ plus general knowledge is ok for a short background paragraph if you label it clearly."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("faq_grounding"), "relaxed")

    def test_embedded_faq_grounding_conflict_skips(self) -> None:
        msg = (
            "Answer from the policy documentation excerpt only: stick to the FAQ and use FAQ-only facts, "
            "but also mix the FAQ with general knowledge freely—pick one grounding mode."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertIsNone(o.get("faq_grounding"))

    def test_embedded_math_detail_show_work(self) -> None:
        msg = (
            "For my calculus homework on definite integrals, show your work and walk through the derivation "
            "when you integrate x^2 e^{-x} from zero to infinity."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("math_detail"), "show_work")

    def test_embedded_math_detail_final_only(self) -> None:
        msg = (
            "I'm checking a statistics problem set before class. For this Bayes theorem exercise, "
            "give me the final answer only and skip the steps—I just need the posterior probability."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("math_detail"), "final_only")

    def test_embedded_math_detail_conflict_skips(self) -> None:
        msg = (
            "Solve the quadratic equation for the exam review. Show your work with intermediate steps, "
            "but also final answer only with no derivation—pick one math detail style."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertIsNone(o.get("math_detail"))

    def test_embedded_code_block_style_fenced(self) -> None:
        msg = (
            "I'm documenting a kubectl rollout for our platform team. "
            "Put the bash commands in fenced code blocks with markdown code fences so I can paste into the runbook."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("code_block_style"), "fenced")

    def test_embedded_code_block_style_inline(self) -> None:
        msg = (
            "For this short Python API snippet in chat, use inline code only—no triple backticks and "
            "keep the one-liner commands inline in the sentence."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertEqual(o.get("code_block_style"), "inline")

    def test_embedded_code_block_style_conflict_skips(self) -> None:
        msg = (
            "Share a docker compose example for local dev. Use fenced code blocks for the yaml, "
            "but also inline code only with no fenced code blocks—pick one code layout."
        )
        o, _e, _t = analyze_embedded_prompt_signals(msg)
        self.assertIsNone(o.get("code_block_style"))


if __name__ == "__main__":
    unittest.main()
