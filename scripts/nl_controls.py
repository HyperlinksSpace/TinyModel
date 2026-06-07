"""Natural-language control phrases for Universal Brain chat.

This is a lightweight, deterministic pre-router for actions that should not depend on
LLM JSON routing (and should work without requiring users to remember slash commands).

It is intentionally conservative: it only triggers on fairly explicit phrasing.
"""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class ControlAction:
    name: str
    value: str | None = None


_WS = re.compile(r"\s+")


def _norm(s: str) -> str:
    return _WS.sub(" ", (s or "").strip().lower())


def parse_control_action(message: str) -> ControlAction | None:
    """Return a ControlAction if the message is a natural-language control request."""
    m = _norm(message)
    if not m:
        return None

    # "What mode is this? What session/scope am I in?"
    if re.search(r"\b(what|show)\b.*\b(my )?(session|scope|settings|mode|status)\b", m) or re.search(
        r"\bwhich\b.*\b(scope|session)\b", m
    ):
        return ControlAction("show_session")

    # Start a fresh private session (new scope key).
    if re.search(r"\b(new|fresh)\b.*\b(private )?(session|scope)\b", m) or re.search(
        r"\b(start|begin)\b.*\b(private )?(session|scope)\b", m
    ):
        return ControlAction("new_private_session")

    # Switch to a named scope in chat, e.g. "use scope abc-123" / "switch to session foo".
    m2 = re.search(r"\b(use|switch to|set)\b.*\b(scope|session)\b\s*[:=]?\s*([a-z0-9][a-z0-9_.:-]{1,63})\b", m)
    if m2:
        return ControlAction("set_scope", m2.group(3))

    # Memory controls (order matters: list/show before export/download)
    if re.search(
        r"\b(show|list)\b.*\b(my )?(data|memory|memories|notes)\b",
        m,
    ):
        return ControlAction("list_memories")
    if re.search(
        r"\b(export|download)\b.*\b(my )?(data|memory|memories|notes)\b",
        m,
    ):
        return ControlAction("export_memory")
    if re.search(r"\b(clear|wipe|delete|forget)\b.*\b(session)\b.*\b(memory|memories|notes)?\b", m):
        return ControlAction("clear_session")
    if re.search(r"\b(forget|delete|erase|wipe)\b.*\b(all|everything)\b.*\b(memory|memories|notes|data)\b", m) or re.search(
        r"\b(delete|erase)\b.*\b(my )?(data|account data|data for this chat)\b", m
    ):
        return ControlAction("forget_scope")

    # Session toggles (chat UX) — short lines only so long questions are not hijacked
    # (e.g. "Show the brain trace. … outline a stakeholder map …" must stay normal chat).
    if len(m) <= 120:
        if re.search(r"\b(turn on|enable|show)\b.*\b(trace|brain trace|debug)\b", m):
            return ControlAction("set_trace", "on")
        if re.search(r"\b(turn off|disable|hide)\b.*\b(trace|brain trace|debug)\b", m):
            return ControlAction("set_trace", "off")

        if re.search(r"\b(turn on|enable)\b.*\b(smart routing|auto routing|router)\b", m):
            return ControlAction("set_smart_route", "on")
        if re.search(r"\b(turn off|disable)\b.*\b(smart routing|auto routing|router)\b", m):
            return ControlAction("set_smart_route", "off")

        if re.search(r"\b(turn on|enable)\b.*\b(faq|rag|retrieval)\b", m):
            return ControlAction("set_rag", "on")
        if re.search(r"\b(turn off|disable)\b.*\b(faq|rag|retrieval)\b", m):
            return ControlAction("set_rag", "off")

    # Reply style for the generative model (short lines only to avoid hijacking real questions).
    # Require "reply"/"answer" before style|format|length so phrases like "default quote style" / "reset tables"
    # are handled by narrower matchers below.
    if len(m) <= 140 and (
        re.search(r"\breset\b.*\b(reply|answer)\s+(style|format|length)\b", m)
        or re.search(r"\b(default|normal)\b.*\b(reply|answer)\s+(style|format|length)\b", m)
    ):
        return ControlAction("reset_reply_style")

    if len(m) <= 96 and re.search(
        r"\b(be brief|stay brief|keep it short|short answers|answer briefly|concise replies)\b",
        m,
    ):
        return ControlAction("set_verbosity", "brief")

    if len(m) <= 120 and re.search(
        r"\b(more detail|go deeper|in greater detail|explain thoroughly|longer answers|detailed answers)\b",
        m,
    ):
        return ControlAction("set_verbosity", "detailed")

    if len(m) <= 100 and re.search(
        r"\b(normal (answer )?length|default length|balanced length)\b",
        m,
    ):
        return ControlAction("set_verbosity", "normal")

    if len(m) <= 110 and re.search(r"\b(use|prefer)\b", m) and re.search(
        r"\b(bullet points?|numbered lists?)\b",
        m,
    ):
        return ControlAction("set_reply_format", "bullets")

    if len(m) <= 100 and re.search(
        r"\b(no bullets|plain paragraphs?|prose only|stop using lists)\b",
        m,
    ):
        return ControlAction("set_reply_format", "prose")

    # FAQ / RAG grounding hints for the assistant (short control lines).
    if len(m) <= 100 and re.search(
        r"\b(strict faq|faq only|stick to (the )?faq|only use (the )?faq|only trust (the )?faq)\b",
        m,
    ):
        return ControlAction("set_faq_grounding", "strict")

    if len(m) <= 115 and re.search(
        r"\b(balanced faq|normal faq|default faq(\s+grounding)?|default faq mode)\b",
        m,
    ):
        return ControlAction("set_faq_grounding", "normal")

    if len(m) <= 130 and re.search(
        r"\b(relaxed faq|faq plus general knowledge|general knowledge(\s+is)?\s+ok|mix faq and general knowledge)\b",
        m,
    ):
        return ControlAction("set_faq_grounding", "relaxed")

    # Explanation depth (who the answer is for) — short control lines only.
    if (
        (len(m) <= 40 and re.match(r"^(please\s+)?explain simply[\s.!?]*$", m))
        or re.match(r"^(please\s+)?eli5\b[\s.!?]*$", m)
        or (len(m) <= 56 and re.search(r"\b(i'?m\s+a\s+beginner|beginner\s+here)\b", m))
        or re.match(r"^(please\s+)?assume i'?m\s+new\b[\s.!?]*$", m)
        or (len(m) <= 56 and re.search(r"\bi\s+need\s+(the\s+)?basics\b", m))
    ):
        return ControlAction("set_audience", "simple")

    if len(m) <= 72 and (
        re.match(r"^(please\s+)?assume i'?m\s+technical[\s.!?]*$", m)
        or re.match(r"^expert\s+mode[\s.!?]*$", m)
        or re.match(r"^(please\s+)?use jargon freely[\s.!?]*$", m)
        or re.match(r"^technical audience[\s.!?]*$", m)
        or re.match(r"^for experts[\s.!?]*$", m)
    ):
        return ControlAction("set_audience", "technical")

    if len(m) <= 78 and (
        re.match(r"^(please\s+)?(default explanation level|normal explanation level|general audience)[\s.!?]*$", m)
        or re.match(r"^(please\s+)?(reset|default)\s+audience[\s.!?]*$", m)
    ):
        return ControlAction("set_audience", "normal")

    # Answer lead — whether to front-load a TL;DR line (orthogonal to verbosity).
    if len(m) <= 88 and (
        re.match(r"^(please\s+)?(tl;|tl)dr\s+first\b[\s.!?]*$", m)
        or re.match(r"^(please\s+)?(lead|start)\s+with\s+(a\s+)?(short\s+)?summary\b[\s.!?]*$", m)
        or re.match(r"^(please\s+)?summary\s+first\b[\s.!?]*$", m)
    ):
        return ControlAction("set_answer_lead", "tldr_first")

    if len(m) <= 92 and (
        re.match(r"^(please\s+)?no\s+tl;?dr\b[\s.!?]*$", m)
        or re.match(r"^(please\s+)?skip (the\s+)?summary\b[\s.!?]*$", m)
        or re.match(r"^(please\s+)?answer directly\b[\s.!?]*$", m)
        or re.match(r"^(please\s+)?direct answer\s+only\b[\s.!?]*$", m)
        or re.match(r"^(please\s+)?without\s+a\s+tldr\b[\s.!?]*$", m)
    ):
        return ControlAction("set_answer_lead", "direct")

    if len(m) <= 64 and (
        re.match(r"^(please\s+)?(default answer structure|normal answer opening|usual\s+opening)[\s.!?]*$", m)
        or re.match(r"^(please\s+)?reset\s+(answer\s+)?opening[\s.!?]*$", m)
    ):
        return ControlAction("set_answer_lead", "normal")

    # Procedures: numbered steps vs continuous prose (orthogonal to bullets).
    if len(m) <= 88 and (
        re.match(r"^(please\s+)?(step by step|step-by-step)[\s.!?]*$", m)
        or re.match(r"^(please\s+)?use numbered steps[\s.!?]*$", m)
        or re.match(r"^(please\s+)?numbered steps\b[\s.!?]*$", m)
        or re.match(r"^(please\s+)?walk me through( the)? steps\b[\s.!?]*$", m)
        or re.match(r"^(please\s+)?break it into steps[\s.!?]*$", m)
    ):
        return ControlAction("set_step_style", "numbered")

    if len(m) <= 92 and (
        re.match(r"^(please\s+)?(no numbered steps|don'?t number steps|skip step numbers)[\s.!?]*$", m)
        or re.match(r"^(please\s+)?(continuous prose|prose without steps)[\s.!?]*$", m)
    ):
        return ControlAction("set_step_style", "continuous")

    if len(m) <= 64 and re.match(r"^(please\s+)?(default step style|normal steps|reset steps)[\s.!?]*$", m):
        return ControlAction("set_step_style", "normal")

    # How hard to hedge / flag limits (orthogonal to FAQ strictness).
    if len(m) <= 94 and (
        re.match(r"^(please\s+)?flag your assumptions[\s.!?]*$", m)
        or re.match(r"^(please\s+)?be explicit about uncertainty[\s.!?]*$", m)
        or re.match(r"^(please\s+)?say if you don'?t know[\s.!?]*$", m)
        or re.match(r"^(please\s+)?tell me when you(?:'?re|\s+are)\s+unsure[\s.!?]*$", m)
        or re.match(r"^(please\s+)?say when you(?:'?re|\s+are)\s+unsure[\s.!?]*$", m)
    ):
        return ControlAction("set_confidence_tone", "transparent")

    if len(m) <= 72 and (
        re.match(r"^(please\s+)?be decisive[\s.!?]*$", m)
        or re.match(r"^(please\s+)?don'?t hedge[\s.!?]*$", m)
        or re.match(r"^(please\s+)?give firm answers[\s.!?]*$", m)
    ):
        return ControlAction("set_confidence_tone", "assertive")

    if len(m) <= 80 and re.match(
        r"^(please\s+)?(default confidence tone|normal confidence|reset uncertainty)[\s.!?]*$",
        m,
    ):
        return ControlAction("set_confidence_tone", "normal")

    # Whether to offer follow-ups / next steps at the end of answers.
    if len(m) <= 96 and (
        re.match(r"^(please\s+)?suggest next steps[\s.!?]*$", m)
        or re.match(r"^(please\s+)?offer follow[- ]up questions[\s.!?]*$", m)
        or re.match(r"^(please\s+)?end with (optional )?next steps[\s.!?]*$", m)
    ):
        return ControlAction("set_followup_close", "suggest")

    if len(m) <= 100 and (
        re.match(r"^(please\s+)?no follow[- ]up questions[\s.!?]*$", m)
        or re.match(r"^(please\s+)?don'?t ask follow[- ]up questions[\s.!?]*$", m)
        or re.match(r"^(please\s+)?no questions at the end[\s.!?]*$", m)
    ):
        return ControlAction("set_followup_close", "minimal")

    if len(m) <= 78 and (
        re.match(r"^(please\s+)?(default follow[- ]ups?|reset follow[- ]ups?|normal follow[- ]ups?)[\s.!?]*$", m)
    ):
        return ControlAction("set_followup_close", "normal")

    # Teach order: define terms vs motivate first (orthogonal to TL;DR / steps).
    if len(m) <= 80 and (
        re.match(r"^(please\s+)?definitions first[\s.!?]*$", m)
        or re.match(r"^(please\s+)?start with definitions[\s.!?]*$", m)
        or re.match(r"^(please\s+)?define terms first[\s.!?]*$", m)
    ):
        return ControlAction("set_exposition_order", "definitions_first")

    if len(m) <= 96 and (
        re.match(r"^(please\s+)?intuition first[\s.!?]*$", m)
        or re.match(r"^(please\s+)?big picture first[\s.!?]*$", m)
        or re.match(r"^(please\s+)?start with the big picture[\s.!?]*$", m)
    ):
        return ControlAction("set_exposition_order", "intuition_first")

    if len(m) <= 88 and re.match(
        r"^(please\s+)?(default explanation order|reset explanation order|normal explanation order)[\s.!?]*$",
        m,
    ):
        return ControlAction("set_exposition_order", "normal")

    # Examples vs terse explanations when comparing or teaching.
    if len(m) <= 76 and (
        re.match(r"^(please\s+)?include examples[\s.!?]*$", m)
        or re.match(r"^(please\s+)?use concrete examples[\s.!?]*$", m)
        or re.match(r"^(please\s+)?illustrate with examples[\s.!?]*$", m)
    ):
        return ControlAction("set_example_density", "rich")

    if len(m) <= 92 and (
        re.match(r"^(please\s+)?skip examples[\s.!?]*$", m)
        or re.match(r"^(please\s+)?don'?t add examples[\s.!?]*$", m)
        or re.match(r"^(please\s+)?no examples unless i ask[\s.!?]*$", m)
    ):
        return ControlAction("set_example_density", "sparse")

    if len(m) <= 68 and re.match(
        r"^(please\s+)?(default examples|normal examples|reset examples)[\s.!?]*$",
        m,
    ):
        return ControlAction("set_example_density", "normal")

    # Compare/contrast presentation.
    if len(m) <= 96 and (
        re.match(r"^(please\s+)?use pros and cons[\s.!?]*$", m)
        or re.match(r"^(please\s+)?pros and cons sections[\s.!?]*$", m)
        or re.match(r"^(please\s+)?compare with pros and cons[\s.!?]*$", m)
    ):
        return ControlAction("set_comparison_frame", "pros_cons")

    if len(m) <= 100 and (
        re.match(r"^(please\s+)?compare in flowing prose[\s.!?]*$", m)
        or re.match(r"^(please\s+)?prose comparison only[\s.!?]*$", m)
        or re.match(r"^(please\s+)?no pros and cons sections[\s.!?]*$", m)
    ):
        return ControlAction("set_comparison_frame", "narrative")

    if len(m) <= 82 and re.match(
        r"^(please\s+)?(default comparison style|normal comparison|reset comparison)[\s.!?]*$",
        m,
    ):
        return ControlAction("set_comparison_frame", "normal")

    # Professional vs conversational wording (orthogonal to verbosity).
    if len(m) <= 92 and (
        re.match(r"^(please\s+)?formal tone[\s.!?]*$", m)
        or re.match(r"^(please\s+)?professional register[\s.!?]*$", m)
        or re.match(r"^(please\s+)?business writing style[\s.!?]*$", m)
    ):
        return ControlAction("set_register_tone", "formal")

    if len(m) <= 96 and (
        re.match(r"^(please\s+)?casual tone[\s.!?]*$", m)
        or re.match(r"^(please\s+)?friendly casual style[\s.!?]*$", m)
        or re.match(r"^(please\s+)?speak casually[\s.!?]*$", m)
    ):
        return ControlAction("set_register_tone", "casual")

    if len(m) <= 76 and re.match(
        r"^(please\s+)?(default tone|neutral tone|reset tone)[\s.!?]*$",
        m,
    ):
        return ControlAction("set_register_tone", "normal")

    # Markdown code snippet layout.
    if len(m) <= 100 and (
        re.match(r"^(please\s+)?use code fences[\s.!?]*$", m)
        or re.match(r"^(please\s+)?fenced code blocks[\s.!?]*$", m)
        or re.match(r"^(please\s+)?markdown code fences[\s.!?]*$", m)
    ):
        return ControlAction("set_code_block_style", "fenced")

    if len(m) <= 104 and (
        re.match(r"^(please\s+)?inline code only[\s.!?]*$", m)
        or re.match(r"^(please\s+)?no triple backticks[\s.!?]*$", m)
        or re.match(r"^(please\s+)?no fenced code blocks[\s.!?]*$", m)
    ):
        return ControlAction("set_code_block_style", "inline")

    if len(m) <= 96 and re.match(
        r"^(please\s+)?(default code formatting|reset code style|normal code blocks)[\s.!?]*$",
        m,
    ):
        return ControlAction("set_code_block_style", "normal")

    # Analogies / metaphors vs literal explanations only.
    if len(m) <= 92 and (
        re.match(r"^(please\s+)?use analogies[\s.!?]*$", m)
        or re.match(r"^(please\s+)?analogies when helpful[\s.!?]*$", m)
        or re.match(r"^(please\s+)?metaphors are ok[\s.!?]*$", m)
    ):
        return ControlAction("set_analogy_use", "prefer")

    if len(m) <= 100 and (
        re.match(r"^(please\s+)?no analogies[\s.!?]*$", m)
        or re.match(r"^(please\s+)?skip metaphors[\s.!?]*$", m)
        or re.match(r"^(please\s+)?literal explanations only[\s.!?]*$", m)
    ):
        return ControlAction("set_analogy_use", "avoid")

    if len(m) <= 82 and re.match(
        r"^(please\s+)?(default analogy style|reset analogies|normal analogies)[\s.!?]*$",
        m,
    ):
        return ControlAction("set_analogy_use", "normal")

    # Expand vs terse acronym handling on first introduce.
    if len(m) <= 112 and (
        re.match(r"^(please\s+)?spell out acronyms[\s.!?]*$", m)
        or re.match(r"^(please\s+)?expand acronyms on first use[\s.!?]*$", m)
        or re.match(r"^(please\s+)?define acronyms when you use them[\s.!?]*$", m)
    ):
        return ControlAction("set_acronym_style", "spell_out")

    if len(m) <= 112 and (
        re.match(r"^(please\s+)?assume i know acronyms[\s.!?]*$", m)
        or re.match(r"^(please\s+)?don'?t expand acronyms[\s.!?]*$", m)
        or re.match(r"^(please\s+)?keep acronyms as is[\s.!?]*$", m)
    ):
        return ControlAction("set_acronym_style", "terse")

    if len(m) <= 92 and re.match(
        r"^(please\s+)?(default acronym style|reset acronyms|normal acronyms)[\s.!?]*$",
        m,
    ):
        return ControlAction("set_acronym_style", "normal")

    # Clarify-first: ask brief questions before answering if key info is missing.
    if len(m) <= 110 and (
        re.match(r"^(please\s+)?ask clarifying questions first[\s.!?]*$", m)
        or re.match(r"^(please\s+)?clarify first[\s.!?]*$", m)
        or re.match(r"^(please\s+)?ask me questions before answering[\s.!?]*$", m)
    ):
        return ControlAction("set_clarify_first", "on")

    if len(m) <= 110 and (
        re.match(r"^(please\s+)?no clarifying questions[\s.!?]*$", m)
        or re.match(r"^(please\s+)?just answer without questions[\s.!?]*$", m)
        or re.match(r"^(please\s+)?answer without asking questions[\s.!?]*$", m)
    ):
        return ControlAction("set_clarify_first", "off")

    if len(m) <= 96 and re.match(
        r"^(please\s+)?(default clarify mode|reset clarify mode|normal clarify mode)[\s.!?]*$",
        m,
    ):
        return ControlAction("set_clarify_first", "normal")

    # Speculation level: strict factual vs brainstorming.
    if len(m) <= 110 and (
        re.match(r"^(please\s+)?no speculation[\s.!?]*$", m)
        or re.match(r"^(please\s+)?stick to high confidence only[\s.!?]*$", m)
        or re.match(r"^(please\s+)?avoid guessing[\s.!?]*$", m)
    ):
        return ControlAction("set_speculation", "strict")

    if len(m) <= 110 and (
        re.match(r"^(please\s+)?brainstorm freely[\s.!?]*$", m)
        or re.match(r"^(please\s+)?speculate freely[\s.!?]*$", m)
        or re.match(r"^(please\s+)?wild ideas ok[\s.!?]*$", m)
    ):
        return ControlAction("set_speculation", "creative")

    if len(m) <= 100 and re.match(
        r"^(please\s+)?(default speculation|normal speculation|reset speculation)[\s.!?]*$",
        m,
    ):
        return ControlAction("set_speculation", "normal")

    # Math/explanations: show work vs final-only.
    if len(m) <= 110 and (
        re.match(r"^(please\s+)?show your work[\s.!?]*$", m)
        or re.match(r"^(please\s+)?show the derivation[\s.!?]*$", m)
        or re.match(r"^(please\s+)?include steps in math[\s.!?]*$", m)
    ):
        return ControlAction("set_math_detail", "show_work")

    if len(m) <= 110 and (
        re.match(r"^(please\s+)?final answer only[\s.!?]*$", m)
        or re.match(r"^(please\s+)?no derivation[\s.!?]*$", m)
        or re.match(r"^(please\s+)?skip the steps[\s.!?]*$", m)
    ):
        return ControlAction("set_math_detail", "final_only")

    if len(m) <= 110 and re.match(
        r"^(please\s+)?(default math detail|normal math detail|reset math detail)[\s.!?]*$",
        m,
    ):
        return ControlAction("set_math_detail", "normal")

    # Output structure: JSON-shaped vs normal prose.
    if len(m) <= 110 and (
        re.match(r"^(please\s+)?answer in json[\s.!?]*$", m)
        or re.match(r"^(please\s+)?json output[\s.!?]*$", m)
        or re.match(r"^(please\s+)?structured json[\s.!?]*$", m)
    ):
        return ControlAction("set_output_format", "json")

    if len(m) <= 110 and (
        re.match(r"^(please\s+)?plain text only[\s.!?]*$", m)
        or re.match(r"^(please\s+)?no json[\s.!?]*$", m)
        or re.match(r"^(please\s+)?no structured output[\s.!?]*$", m)
    ):
        return ControlAction("set_output_format", "plain")

    if len(m) <= 110 and re.match(
        r"^(please\s+)?(default output format|normal output format|reset output format)[\s.!?]*$",
        m,
    ):
        return ControlAction("set_output_format", "normal")

    # Safety/risk posture for recommendations.
    if len(m) <= 110 and (
        re.match(r"^(please\s+)?be risk averse[\s.!?]*$", m)
        or re.match(r"^(please\s+)?be conservative[\s.!?]*$", m)
        or re.match(r"^(please\s+)?err on the side of safety[\s.!?]*$", m)
    ):
        return ControlAction("set_risk_posture", "conservative")

    if len(m) <= 110 and (
        re.match(r"^(please\s+)?be pragmatic[\s.!?]*$", m)
        or re.match(r"^(please\s+)?optimize for speed[\s.!?]*$", m)
        or re.match(r"^(please\s+)?good enough is fine[\s.!?]*$", m)
    ):
        return ControlAction("set_risk_posture", "pragmatic")

    if len(m) <= 110 and re.match(
        r"^(please\s+)?(default risk posture|normal risk posture|reset risk posture)[\s.!?]*$",
        m,
    ):
        return ControlAction("set_risk_posture", "normal")

    # Actionability: runnable steps vs conceptual explanation.
    if len(m) <= 110 and (
        re.match(r"^(please\s+)?give me runnable commands[\s.!?]*$", m)
        or re.match(r"^(please\s+)?include commands[\s.!?]*$", m)
        or re.match(r"^(please\s+)?make it actionable[\s.!?]*$", m)
    ):
        return ControlAction("set_actionability", "commands")

    if len(m) <= 110 and (
        re.match(r"^(please\s+)?no commands[\s.!?]*$", m)
        or re.match(r"^(please\s+)?conceptual only[\s.!?]*$", m)
        or re.match(r"^(please\s+)?high level only[\s.!?]*$", m)
    ):
        return ControlAction("set_actionability", "conceptual")

    if len(m) <= 110 and re.match(
        r"^(please\s+)?(default actionability|normal actionability|reset actionability)[\s.!?]*$",
        m,
    ):
        return ControlAction("set_actionability", "normal")

    # Quote/citation preference when using supplied excerpts.
    if len(m) <= 110 and (
        re.match(r"^(please\s+)?quote the faq excerpts[\s.!?]*$", m)
        or re.match(r"^(please\s+)?use direct quotes[\s.!?]*$", m)
        or re.match(r"^(please\s+)?cite with quotes[\s.!?]*$", m)
    ):
        return ControlAction("set_quote_style", "quote")

    if len(m) <= 110 and (
        re.match(r"^(please\s+)?no quotes[\s.!?]*$", m)
        or re.match(r"^(please\s+)?don'?t quote excerpts[\s.!?]*$", m)
        or re.match(r"^(please\s+)?paraphrase only[\s.!?]*$", m)
    ):
        return ControlAction("set_quote_style", "paraphrase")

    if len(m) <= 110 and re.match(
        r"^(please\s+)?(default quote style|normal quote style|reset quote style)[\s.!?]*$",
        m,
    ):
        return ControlAction("set_quote_style", "normal")

    # Tables: prefer markdown tables vs avoid.
    if len(m) <= 110 and (
        re.match(r"^(please\s+)?use tables[\s.!?]*$", m)
        or re.match(r"^(please\s+)?markdown tables[\s.!?]*$", m)
        or re.match(r"^(please\s+)?tabular format[\s.!?]*$", m)
    ):
        return ControlAction("set_table_style", "prefer")

    if len(m) <= 110 and (
        re.match(r"^(please\s+)?no tables[\s.!?]*$", m)
        or re.match(r"^(please\s+)?avoid tables[\s.!?]*$", m)
        or re.match(r"^(please\s+)?no markdown tables[\s.!?]*$", m)
    ):
        return ControlAction("set_table_style", "avoid")

    if len(m) <= 110 and re.match(
        r"^(please\s+)?(default table style|normal tables|reset tables)[\s.!?]*$",
        m,
    ):
        return ControlAction("set_table_style", "normal")

    # Emoji in assistant replies (short lines; conservative wording).
    if len(m) <= 110 and (
        re.match(r"^(please\s+)?(use emoji|emoji ok|emoji welcome|include emoji)[\s.!?]*$", m)
        or re.match(r"^(please\s+)?add (a few )?emoji[\s.!?]*$", m)
    ):
        return ControlAction("set_emoji_style", "include")

    if len(m) <= 110 and (
        re.match(r"^(please\s+)?no emojis?[\s.!?]*$", m)
        or re.match(r"^(please\s+)?avoid emoji[\s.!?]*$", m)
        or re.match(r"^(please\s+)?don'?t use emoji[\s.!?]*$", m)
    ):
        return ControlAction("set_emoji_style", "avoid")

    if len(m) <= 110 and re.match(
        r"^(please\s+)?(default emoji style|normal emoji|reset emoji)[\s.!?]*$",
        m,
    ):
        return ControlAction("set_emoji_style", "normal")

    # Markdown section headings (## / ###) vs flat prose.
    if len(m) <= 110 and (
        re.match(r"^(please\s+)?use section headings[\s.!?]*$", m)
        or re.match(r"^(please\s+)?organize with headings[\s.!?]*$", m)
        or re.match(r"^(please\s+)?use markdown headings[\s.!?]*$", m)
    ):
        return ControlAction("set_section_headings", "prefer")

    if len(m) <= 110 and (
        re.match(r"^(please\s+)?no section headings[\s.!?]*$", m)
        or re.match(r"^(please\s+)?avoid markdown headings[\s.!?]*$", m)
        or re.match(r"^(please\s+)?flat (answer|prose)( please)?[\s.!?]*$", m)
    ):
        return ControlAction("set_section_headings", "avoid")

    if len(m) <= 110 and re.match(
        r"^(please\s+)?(default section headings|normal headings|reset headings)[\s.!?]*$",
        m,
    ):
        return ControlAction("set_section_headings", "normal")

    # Inline emphasis: bold a few key terms vs keep markdown minimal.
    if len(m) <= 110 and (
        re.match(r"^(please\s+)?bold key terms[\s.!?]*$", m)
        or re.match(r"^(please\s+)?highlight important terms[\s.!?]*$", m)
        or re.match(r"^(please\s+)?emphasize keywords[\s.!?]*$", m)
    ):
        return ControlAction("set_term_emphasis", "highlight")

    if len(m) <= 110 and (
        re.match(r"^(please\s+)?minimal bold[\s.!?]*$", m)
        or re.match(r"^(please\s+)?don'?t overuse bold[\s.!?]*$", m)
        or re.match(r"^(please\s+)?avoid excessive bold[\s.!?]*$", m)
    ):
        return ControlAction("set_term_emphasis", "minimal")

    if len(m) <= 110 and re.match(
        r"^(please\s+)?(default emphasis|normal bold|reset emphasis)[\s.!?]*$",
        m,
    ):
        return ControlAction("set_term_emphasis", "normal")

    # Counterpoint tone: supportive vs challenge assumptions (short lines).
    if len(m) <= 110 and (
        re.match(r"^(please\s+)?challenge my assumptions[\s.!?]*$", m)
        or re.match(r"^(please\s+)?play devils advocate[\s.!?]*$", m)
        or re.match(r"^(please\s+)?push back on weak points[\s.!?]*$", m)
    ):
        return ControlAction("set_counterpoint_tone", "challenge")

    if len(m) <= 110 and (
        re.match(r"^(please\s+)?be supportive[\s.!?]*$", m)
        or re.match(r"^(please\s+)?assume good intent[\s.!?]*$", m)
        or re.match(r"^(please\s+)?encourage my ideas[\s.!?]*$", m)
    ):
        return ControlAction("set_counterpoint_tone", "supportive")

    if len(m) <= 110 and re.match(
        r"^(please\s+)?(default counterpoints|normal pushback|reset counterpoints)[\s.!?]*$",
        m,
    ):
        return ControlAction("set_counterpoint_tone", "normal")

    return None


# Tokens for "write the reply in …" detection (allowlist avoids "in Python" / "in 24 hours").
_REPLY_LANG_TOKENS: dict[str, str] = {
    "arabic": "Arabic",
    "chinese": "Chinese (Simplified)",
    "czech": "Czech",
    "danish": "Danish",
    "dutch": "Dutch",
    "english": "English",
    "finnish": "Finnish",
    "french": "French",
    "german": "German",
    "greek": "Greek",
    "hebrew": "Hebrew",
    "hindi": "Hindi",
    "hungarian": "Hungarian",
    "indonesian": "Indonesian",
    "italian": "Italian",
    "japanese": "Japanese",
    "korean": "Korean",
    "norwegian": "Norwegian",
    "polish": "Polish",
    "portuguese": "Portuguese",
    "romanian": "Romanian",
    "russian": "Russian",
    "spanish": "Spanish",
    "swedish": "Swedish",
    "thai": "Thai",
    "turkish": "Turkish",
    "ukrainian": "Ukrainian",
    "vietnamese": "Vietnamese",
}


_LEN_CAP_UNIT_MAX: dict[str, int] = {
    "word": 2500,
    "words": 2500,
    "sentence": 80,
    "sentences": 80,
    "paragraph": 30,
    "paragraphs": 30,
    "line": 120,
    "lines": 120,
}


def _length_cap_instruction(m: str) -> tuple[str, str] | None:
    """If the user asked for a max length, return (system instruction, compact trace token)."""
    if len(m) < 24:
        return None
    patterns = [
        re.compile(
            r"\b(?:in under|at most|no more than|under|within|no longer than)\s+(\d{1,4})\s+"
            r"(words?|sentences?|paragraphs?|lines?)\b"
        ),
        re.compile(r"\b(?:max|maximum)\s+(\d{1,4})\s+(words?|sentences?|paragraphs?|lines?)\b"),
        re.compile(r"\b(\d{1,4})\s+words?\s+(?:max|maximum|only|at most|or less)\b"),
    ]
    for rx in patterns:
        mo = rx.search(m)
        if not mo:
            continue
        n_raw, unit = mo.group(1), mo.group(2).lower()
        try:
            n = int(n_raw)
        except ValueError:
            continue
        cap = _LEN_CAP_UNIT_MAX.get(unit)
        if cap is None or n < 1 or n > cap:
            continue
        if unit.startswith("word"):
            plural, short = "words", "w"
        elif unit.startswith("sentence"):
            plural, short = "sentences", "s"
        elif unit.startswith("paragraph"):
            plural, short = "paragraphs", "p"
        else:
            plural, short = "lines", "ln"
        trace_tok = f"len_cap={n}{short}"
        instr = (
            f"The user requested a **tight length cap** of about **{n} {plural}** for the full assistant answer "
            f"(including lists or headings). Stay at or under this cap; if it is impossible, say so in one short sentence "
            "then give the closest fit."
        )
        return instr, trace_tok
    return None


def _code_only_instruction(m: str) -> str | None:
    """Detect requests for code-heavy output with almost no prose."""
    if len(m) < 18:
        return None
    if re.search(
        r"\b(just the code|(?<!not )(?<!no )code only|only code|no prose,?\s*just code|"
        r"no explanation,?\s*just (?:the )?code|"
        r"skip (?:the )?explanation|omit (?:the )?explanation|(?:give|send|return)\s+me\s+only\s+the\s+code|"
        r"output\s+only\s+(?:the\s+)?code)\b",
        m,
    ):
        return (
            "The user asked for **code-first output**: put the working solution in **one fenced markdown code block** "
            "when the answer is code; keep any non-code text to **at most one short sentence** or omit it if the code "
            "is self-explanatory."
        )
    return None


def _embedded_code_commentary(m: str) -> tuple[str, str] | None:
    """``code_explained`` — snippet plus walkthrough (complement to ``code_only`` trace tag)."""
    if len(m) < 32:
        return None
    if not re.search(
        r"\b(code|script|function|snippet|program|implementation|bash|python|sql|regex|api|curl|"
        r"typescript|rust|java|module|class|method|algorithm)\b",
        m,
    ):
        return None
    explained = bool(
        re.search(
            r"\b(code (?:with|plus|and) (?:an? )?explanation|explain (?:the|what) (?:the )?code(?: does)?|"
            r"walk me through the (?:code|snippet)|comment(?:ed)? code|annotate (?:the )?(?:code|snippet)|"
            r"code (?:with|plus) (?:inline )?comments|don'?t (?:just )?give code without explaining|"
            r"not (?:just )?code only|no code[- ]only|"
            r"with (?:a )?line[- ]by[- ]line (?:walkthrough|explanation)|"
            r"explain (?:each|every) (?:line|part|step)|teach (?:me )?(?:through|with) the code|"
            r"show (?:me )?(?:the )?code (?:and|then) explain|"
            r"include (?:brief )?comments (?:in|on) the code)\b",
            m,
        )
    )
    if not explained:
        return None
    instr = (
        "The user asked for **code with explanation**: include a **fenced code block** (or clearly separated snippet) "
        "**and** a concise walkthrough—what it does, non-obvious lines, and how to run or adapt it. "
        "Do **not** return code alone without prose."
    )
    return instr, "code_explained"


def _embedded_guided_discovery(m: str) -> tuple[str, str] | None:
    """``guided`` (hints-first) vs ``full_solution`` for problem-solving (not one-line controls)."""
    if len(m) < 36:
        return None
    if not re.search(
        r"\b(why|how|explain|prove|derive|solve|puzzle|homework|problem|exercise|bug|code|implement|"
        r"design|compare|understand|learn|teach|practice|algorithm|proof|debug|refactor)\b",
        m,
    ):
        return None
    guided = bool(
        re.search(
            r"\b(don'?t (give|spell|hand) (me )?(the )?full (answer|solution)|don'?t spoil the solution|"
            r"hints? only|only hints|guide me with (hints|questions)|nudge me (in the right direction|toward)|"
            r"i want to (figure|work) it out myself|socratic(\s+method)?|"
            r"lead me to (the )?answer|questions first instead of answering|"
            r"without (giving|spelling) (out )?(the )?(whole )?solution)\b",
            m,
        )
        and not re.search(r"\bdon'?t do hints only\b", m)
    )
    full = bool(
        re.search(
            r"\b(give me the (?:full|complete) (?:worked )?(?:answer|solution)|"
            r"(?:show|spell out) (?:me )?(?:the )?(?:full|entire|complete) (?:worked )?solution|"
            r"complete solution now|don'?t do hints only|no hints only|skip the socratic|"
            r"not hints only|"
            r"just (?:give|tell) me the answer|"
            r"finish the (?:proof|solution) for me|"
            r"i'?m stuck.{0,40}(?:full|complete) solution)\b",
            m,
        )
    )
    if guided and full:
        return None
    if guided:
        instr = (
            "The user asked for **guided discovery** (Socratic / hint-first): prefer short **questions**, "
            "**nudges**, and **partial hints** over a complete solution in this turn. "
            "If one concrete step is essential, show **at most one** move, then check whether they want to continue. "
            "Offer the full worked answer if they say they are stuck or ask you to finish."
        )
        return instr, "guided"
    if full:
        instr = (
            "The user asked for a **complete solution** in this turn: provide the full worked answer with "
            "clear steps or reasoning—do **not** stay in hint-only or Socratic question mode unless a safety "
            "check is required."
        )
        return instr, "full_solution"
    return None


def _ephemeral_privacy_instruction(m: str) -> tuple[str, str] | None:
    """User asked not to treat this turn as content to persist (memory / logging)."""
    if len(m) < 22:
        return None
    if re.search(
        r"\b(off the record|no memory for this|nothing persisted|ephemeral question|ephemeral chat|"
        r"don'?t log this|don'?t persist this|"
        r"don'?t (?:remember|store) (?:this|that|it|anything)|"
        r"do not (?:remember|store) (?:this|that|it)|"
        r"please don'?t (?:remember|store) (?:this|that|it)|"
        r"forget this after|don'?t save (?:this|that)\s+to\s+memory)\b",
        m,
    ):
        instr = (
            "The user signaled **ephemeral intent** for this reply: do **not** invite `/remember`, `/session`, or "
            "long-term note-taking for this content; avoid urging them to store secrets, API keys, or passwords. "
            "Still answer helpfully within normal safety and deployment limits."
        )
        return instr, "ephemeral"

    return None


def _accessibility_sr_instruction(m: str) -> tuple[str, str] | None:
    """User wants screen-reader / WCAG-minded answer structure (linear, semantic headings)."""
    if len(m) < 44:
        return None
    if not re.search(
        r"\b(screen[- ]?reader|screenreader|nvda|jaws|voiceover|talkback|orca|"
        r"wcag(?:\s+[0-9]{1,2}(?:\.[0-9])?)?|\ba11y\b|accessibility|accessible to|"
        r"blind users?|low vision|visually impaired)\b",
        m,
    ):
        return None
    audience = re.search(
        r"\bfor\s+(?:blind|low-vision|screen[- ]?reader|a11y)\s+(?:users?|readers?|audiences?|visitors?)?\b",
        m,
    )
    format_rq = re.search(
        r"\b(friendly|friendlier|structure|structured|layout|linear|heading|headings|semantic|"
        r"readable|reformat|format this|annotate|describe (?:the\s+)?(?:chart|diagram|figure|image)|"
        r"please (?:reply|answer|write|help|summarize|reformat|structure)|"
        r"how (?:should|can) i (?:write|format|publish))\b",
        m,
    )
    if not audience and not format_rq:
        return None
    instr = (
        "The user asked for **screen-reader–friendly / accessibility-aware** formatting: prefer a **clear linear reading order**; "
        "use real markdown heading lines for sections when the answer is long; do **not** rely on a table as the **only** "
        "place critical facts appear—repeat key facts in prose if you use a table; briefly describe any chart or diagram "
        "in words; keep emoji sparse and never the sole carrier of meaning."
    )
    return instr, "a11y"


def _embedded_source_citations(m: str) -> tuple[str, str] | None:
    """``cite_sources`` vs ``cite_minimal`` — inline attribution for FAQ/web/supplied context."""
    if len(m) < 44:
        return None
    if not re.search(
        r"\b(faq|policy|article|paper|report|study|news|web|search|source|reference|claim|fact|"
        r"research|documentation|docs|excerpt|snippet|evidence|retrieved|grounded)\b",
        m,
    ):
        return None
    sources = bool(
        re.search(
            r"\b(cite (?:your )?sources|include (?:source )?links|link to (?:your )?sources|"
            r"(?:give|provide) (?:inline )?citations|attribute (?:each )?(?:claim|point)|"
            r"reference(?:s)? for (?:each|every)|where (?:did|does) (?:this|that) come from|"
            r"back (?:each )?(?:claim|point) with (?:a )?(?:link|source)|"
            r"include (?:the )?urls|show (?:me )?(?:the )?sources you used|"
            r"audit[- ]ready (?:citations|references)|source attribution)\b",
            m,
        )
    )
    minimal = bool(
        re.search(
            r"\b(no (?:source )?links|don'?t cite(?: sources)?|skip (?:the )?links|"
            r"without links or citations|no bibliography|don'?t include urls|"
            r"no footnotes|answer without citing)\b",
            m,
        )
    )
    if sources and minimal:
        return None
    if sources:
        instr = (
            "The user asked for **explicit source attribution**: when using FAQ excerpts, web snippets, "
            "or supplied context, **cite them inline** (e.g. `[FAQ excerpt 2]`, `[Web 1]`) and prefer "
            "**short links or clear source labels** for factual claims; say when something is general knowledge "
            "without a provided source."
        )
        return instr, "cite_sources"
    if minimal:
        instr = (
            "The user asked to **avoid heavy citation formatting**: answer in clear prose **without** "
            "a bibliography, long URL lists, or footnote blocks unless a single inline cite is essential "
            "for policy or safety."
        )
        return instr, "cite_minimal"
    return None


def _embedded_ranked_options(m: str) -> tuple[str, str] | None:
    """``ranked_options`` — user wants choices ordered by priority/merit, not flat peer lists."""
    if len(m) < 48:
        return None
    if not re.search(
        r"\b(option|choice|alternative|approach|vendor|tool|framework|candidate|stack|"
        r"path|strategy|pick|recommend|solution|provider|platform|library|database|"
        r"architecture|design|method|technique|product)\b",
        m,
    ):
        return None
    ranked = bool(
        re.search(
            r"\b(rank (?:them|these|the|your)|ranked (?:list|recommendations?)|"
            r"in order of (?:priority|importance|preference|merit|likelihood)|"
            r"top \d+ (?:options?|choices?|picks?|recommendations?)|"
            r"ordered (?:from|by)|prioriti[sz]e (?:these|the|your)|"
            r"best to worst|strongest to weakest|from most to least|"
            r"highest to lowest(?: priority)?|"
            r"which (?:one|option) (?:first|should we pick first)|"
            r"order (?:them|these) by)\b",
            m,
        )
    )
    flat = bool(
        re.search(
            r"\b(no ranking|don'?t rank|order doesn'?t matter|unordered (?:list|options?)|"
            r"don'?t priorit[iy]ze|all options are equal|no priority order)\b",
            m,
        )
    )
    if ranked and flat:
        return None
    if ranked:
        instr = (
            "The user asked for a **ranked recommendation**: present options in a **clear priority order** "
            "(best-first or explicitly numbered 1., 2., 3.) with a short rationale for the ordering; "
            "do not present every alternative as equally good when they asked for ranking."
        )
        return instr, "ranked_options"
    return None


def _embedded_checklist_reply(m: str) -> tuple[str, str] | None:
    """``checklist`` vs ``no_checklist`` — markdown ``- [ ]`` task layout (not bullet-only lists)."""
    if len(m) < 44:
        return None
    if not re.search(
        r"\b(rollout|deploy|launch|onboard|audit|review|procedure|task|step|plan|"
        r"migrate|implement|runbook|playbook|incident|release|checklist|todo|action item)\b",
        m,
    ):
        return None
    prefer = bool(
        re.search(
            r"\b((?:give|provide|format|return|list|use|write).{0,24}checklist|"
            r"as a checklist|checklist (?:format|style)|action[- ]items? checklist|"
            r"task checklist|tick[- ]box(?:es)?|checkbox(?:es)? (?:list|format)|"
            r"markdown checkbox|to[- ]do list format)\b",
            m,
        )
    )
    avoid = bool(
        re.search(
            r"\b(no checklist|not a checklist|don'?t use checkboxes|avoid checklist|"
            r"without checkboxes|not tick[- ]boxes)\b",
            m,
        )
    )
    if prefer and avoid:
        return None
    if prefer:
        instr = (
            "The user asked for a **markdown checklist**: use **`- [ ]` task lines** (or `- [x]` if noting done) "
            "for actionable items; keep each item one short line; optional brief intro, then the checklist."
        )
        return instr, "checklist"
    if avoid:
        instr = (
            "The user asked **not** to format the answer as a markdown checkbox checklist; use prose, bullets, "
            "or numbered steps instead of `- [ ]` task lines."
        )
        return instr, "no_checklist"
    return None


def _embedded_pseudocode(m: str) -> tuple[str, str] | None:
    """``pseudocode`` vs ``runnable_code`` — abstract algorithm vs executable snippet."""
    if len(m) < 36:
        return None
    if not re.search(
        r"\b(code|algorithm|function|script|program|logic|implementation|sort|search|"
        r"loop|recursion|data structure|complexity)\b",
        m,
    ):
        return None
    pseudo = bool(
        re.search(
            r"\b(pseudo[- ]code only|pseudocode only|pseudo code only|"
            r"language[- ]agnostic(?: algorithm)?|"
            r"don'?t need (?:real |working |runnable )?code|"
            r"abstract algorithm|plain[- ]english algorithm|"
            r"no syntax(?:-specific)? (?:code|details)|not runnable|non[- ]runnable)\b",
            m,
        )
    )
    runnable = bool(
        re.search(
            r"\b((?<!not )runnable|(?<!not )executable|working code|production[- ]ready code|"
            r"copy[- ]paste(?:able)? code|(?<!not )real code|(?<!not )actual code|"
            r"(?<!not )runnable (?:python|javascript|bash|typescript|snippet))\b",
            m,
        )
    )
    if pseudo and runnable:
        return None
    if pseudo:
        instr = (
            "The user asked for **pseudocode**: use clear indented pseudocode or plain-language "
            "algorithm steps—not a language-specific runnable program; omit imports, compiler flags, "
            "and deployment detail unless essential."
        )
        return instr, "pseudocode"
    if runnable:
        instr = (
            "The user asked for **runnable, language-specific code**: prefer a concrete snippet they "
            "can copy-paste or execute, not abstract pseudocode alone."
        )
        return instr, "runnable_code"
    return None


_OPTION_COUNT_WORDS: dict[str, int] = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}

_OPTION_COUNT_PATTERNS = (
    re.compile(
        r"\b(?:(?:give|provide|list|offer|suggest|propose|present|limit(?:\s+to)?|need)\s+(?:me\s+)?)?"
        r"(?:exactly|just|only|at most|no more than)\s+"
        r"(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+"
        r"(?:distinct|different|separate)?\s*"
        r"(?:options?|choices?|alternatives?|approaches?|ideas?|recommendations?|picks?|paths?|solutions?)\b"
    ),
    re.compile(
        r"\btop\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+"
        r"(?:options?|choices?|alternatives?|picks?|recommendations?)\b"
    ),
)


def _parse_option_count_token(tok: str) -> int | None:
    if tok.isdigit():
        n = int(tok)
        return n if 1 <= n <= 10 else None
    return _OPTION_COUNT_WORDS.get(tok)


def _embedded_fixed_option_count(m: str) -> tuple[str, str] | None:
    """``options_n=N`` — user wants exactly N distinct alternatives (not an open-ended list)."""
    if len(m) < 44:
        return None
    if not re.search(
        r"\b(options?|choices?|alternatives?|approaches?|ideas?|recommendations?|picks?|"
        r"paths?|solutions?|vendors?|tools?|frameworks?|strategies?|candidates?)\b",
        m,
    ):
        return None
    found: set[int] = set()
    for pat in _OPTION_COUNT_PATTERNS:
        for mo in pat.finditer(m):
            n = _parse_option_count_token(mo.group(1))
            if n is not None:
                found.add(n)
    if len(found) != 1:
        return None
    n = next(iter(found))
    instr = (
        f"The user asked for **exactly {n} distinct options**: present **{n}** clearly labeled alternatives "
        f"(e.g. **Option 1** … **Option {n}**); do not pad with extras or collapse into fewer unless "
        f"{n} is infeasible—in that case say why in one short sentence."
    )
    return instr, f"options_n={n}"


def _embedded_diagram_visual(m: str) -> tuple[str, str] | None:
    """``diagram`` vs ``no_diagram`` — Mermaid/flowchart/ASCII visual vs text-only."""
    if len(m) < 44:
        return None
    if not re.search(
        r"\b(architecture|system|flow|pipeline|process|workflow|diagram|chart|topology|"
        r"sequence|component|service|deploy|design|how|explain|model|map|overview|"
        r"interaction|request|data)\b",
        m,
    ):
        return None
    prefer = bool(
        re.search(
            r"\b(sequence diagram|architecture diagram|component diagram|system diagram|"
            r"flowchart|flow chart|"
            r"mermaid.{0,20}diagram|"
            r"(?:include|add|draw|show|provide|use|give me).{0,28}diagram|"
            r"(?:ascii|text[- ]based) diagram|"
            r"visual(?:ize| diagram)|"
            r"as a (?:mermaid )?flowchart)\b",
            m,
        )
    )
    avoid = bool(
        re.search(
            r"\b(no diagrams?|without diagrams?|don'?t (?:use|include) (?:a )?diagrams?|"
            r"avoid (?:mermaid|flowcharts?|diagrams?)|"
            r"text[- ]only (?:please|answer)|no (?:mermaid|flowcharts?)|"
            r"skip (?:the )?diagrams?|prose only no (?:charts?|diagrams?))\b",
            m,
        )
    )
    if prefer and avoid:
        return None
    if prefer:
        instr = (
            "The user asked for a **visual diagram** in the reply: include **one** concise "
            "**Mermaid** diagram (preferred) or a short **ASCII** diagram when Mermaid is awkward; "
            "add brief prose before/after; keep node labels short."
        )
        return instr, "diagram"
    if avoid:
        instr = (
            "The user asked for **no diagrams**: answer in prose, bullets, numbered steps, or tables "
            "only—do **not** include Mermaid blocks, flowcharts, or ASCII art diagrams."
        )
        return instr, "no_diagram"
    return None


def _embedded_risks_benefits_order(m: str) -> tuple[str, str] | None:
    """``risks_first`` vs ``benefits_first`` — section order for trade-offs (not ``risk_posture``)."""
    if len(m) < 48:
        return None
    if not re.search(
        r"\b(plan|proposal|rollout|launch|migrate|design|strategy|decision|invest|build|ship|"
        r"product|feature|architecture|change|initiative|roadmap|pitch|trade[- ]?off)\b",
        m,
    ):
        return None
    risks = bool(
        re.search(
            r"\b(risks? first|downsides? first|cons first|what could go wrong first|"
            r"start with (?:the )?risks?|lead with (?:the )?risks?|"
            r"pitfalls? first|negative(?:s)? before positives?|"
            r"caveats? (?:before|then) benefits?|worst[- ]case first)\b",
            m,
        )
    )
    benefits = bool(
        re.search(
            r"\b(benefits? first|upsides? first|pros first|"
            r"start with (?:the )?benefits?|lead with (?:the )?upsides?|"
            r"positives? before negatives?|sell (?:me on )?the upside first|"
            r"good news first)\b",
            m,
        )
    )
    if risks and benefits:
        return None
    if risks:
        instr = (
            "The user asked for **risks / downsides first**: open with key **risks, caveats, and failure modes** "
            "before benefits or recommendations; keep the ordering explicit even if you later add upsides."
        )
        return instr, "risks_first"
    if benefits:
        instr = (
            "The user asked for **benefits / upsides first**: open with **advantages and positive outcomes** "
            "before risks or caveats; keep the ordering explicit even if you note downsides later."
        )
        return instr, "benefits_first"
    return None


def _embedded_risks_mitigations(m: str) -> tuple[str, str] | None:
    """``risks_mitigations`` — paired risk + mitigation layout (not ``risks_first`` section order)."""
    if len(m) < 48:
        return None
    no_rm = bool(
        re.search(
            r"\b(no mitigations?|without mitigations?|skip (?:the\s+)?mitigation(?:s| plan)?|"
            r"don'?t (?:include|list) mitigations?|risks? only|"
            r"no (?:paired\s+)?mitigation section|avoid (?:a\s+)?mitigation section|"
            r"not a risk register|skip (?:the\s+)?risk register)\b",
            m,
        )
    )
    if no_rm:
        return None
    want = bool(
        re.search(
            r"\b(risks? and mitigations?|risks? with mitigations?|"
            r"mitigation(?:s| plan) for each risk|risk register|"
            r"list (?:the\s+)?(?:key\s+)?risks? (?:and|with) (?:corresponding\s+)?mitigations?|"
            r"each risk (?:with|and) (?:a\s+)?mitigation|"
            r"paired risk[- ]mitigation|mitigation steps? for (?:each|every) risk|"
            r"include mitigations? (?:for|against) (?:each|the) risks?)\b",
            m,
        )
    )
    if not want:
        return None
    if not re.search(
        r"\b(plan|proposal|rollout|launch|migrate|design|strategy|security|"
        r"compliance|initiative|project|deployment|change|review|assess|write|describe|outline|report)\b",
        m,
    ):
        return None
    instr = (
        "The user wants a **risks + mitigations** layout: include a **Risks and mitigations** section "
        "where each key risk is paired with a **concrete mitigation** (bullets or a small table with "
        "Risk / Mitigation columns)—do not list risks without actionable mitigations."
    )
    return instr, "risks_mitigations"


def _embedded_revise_draft(m: str) -> tuple[str, str] | None:
    """``revise_draft`` — rewrite/polish user-supplied copy (not a greenfield explain-only ask)."""
    if len(m) < 48:
        return None
    revise = bool(
        re.search(
            r"\b(improve (?:my |this |the )?draft|polish (?:my |this |the )?(?:draft|email|memo)?|"
            r"rewrite (?:it|this|the (?:text|email|message))|"
            r"rewrite (?:my |this |the )?(?:draft|email|paragraph|message|memo|post|letter)|"
            r"edit (?:my |this )?(?:draft|text|copy)|proofread (?:my |this )?|"
            r"tighten (?:my |this )?(?:draft|writing|wording)|"
            r"make (?:this |it |the text )(?:clearer|more professional|more concise|shorter)|"
            r"copy[- ]?edit|wordsmithe)\b",
            m,
        )
    )
    no_revise = bool(
        re.search(
            r"\b(don'?t rewrite|do not rewrite|no rewrite|keep (?:my |the )?wording (?:as[- ]is|unchanged)|"
            r"don'?t edit (?:my |the )?text)\b",
            m,
        )
    )
    if not revise or no_revise:
        return None
    has_artifact = bool(
        re.search(
            r"\b(?:my|this|the)\s+draft\b|draft\s+(?:email|message|memo|slack|paragraph|letter|post)\b|"
            r"(?:text|email|memo)\s+below|following\s+(?:text|email|draft|memo)|"
            r"draft:\s|here(?:'s| is)\s+(?:my|the)\s+draft\b",
            m,
        )
    )
    if not has_artifact and len(m) < 100:
        return None
    instr = (
        "The user wants a **revision of supplied text**: treat their message as source copy to "
        "**rewrite or polish in place**—preserve intent and facts; return the improved version prominently "
        "(add brief bullets on what changed only if helpful); do **not** answer as if no draft was provided."
    )
    return instr, "revise_draft"


def _embedded_revise_diff(m: str) -> tuple[str, str] | None:
    """``revise_diff`` — when revising supplied copy, show before/after or track-changes layout."""
    if len(m) < 48:
        return None
    want_diff = bool(
        re.search(
            r"\b(before and after|before[- ]?after|side[- ]by[- ]side|"
            r"show (?:me )?(?:what|the) changed|show (?:the )?changes|track changes?|"
            r"redline(?:d)?(?:\s+version)?|diff format|as a diff|"
            r"strikethrough (?:for|on) (?:removed|deletions)|"
            r"highlight (?:what|the) changed|compare (?:the )?original (?:to|with|and))\b",
            m,
        )
    )
    no_diff = bool(
        re.search(
            r"\b(no before and after|don'?t show (?:a )?diff|without (?:a )?diff|"
            r"no track changes?|inline revision only|revision only no diff|"
            r"don'?t (?:show|include) (?:before|after)|skip (?:the )?diff)\b",
            m,
        )
    )
    if not want_diff or no_diff:
        return None
    revise = bool(
        re.search(
            r"\b(improve (?:my |this |the )?draft|polish|rewrite|edit (?:my |this )?|"
            r"proofread|copy[- ]?edit|revise (?:my |this |the )?|tighten (?:my )?)\b",
            m,
        )
    )
    has_artifact = bool(
        re.search(
            r"\b(?:my|this|the)\s+draft\b|draft\s+(?:email|message|memo|slack|paragraph|letter|post)\b|"
            r"(?:text|email|memo)\s+below|following\s+(?:text|email|draft|memo)|"
            r"draft:\s|here(?:'s| is)\s+(?:my|the)\s+draft\b",
            m,
        )
    )
    if not revise and not has_artifact:
        return None
    if not has_artifact and len(m) < 96:
        return None
    instr = (
        "The user wants a **before/after or track-changes style revision**: label sections **Before** "
        "and **After** (or use a concise unified diff / `~~removed~~` / **added** markup for changed spans). "
        "Keep the polished **After** copy complete; do not answer as if no source draft was provided."
    )
    return instr, "revise_diff"


def _embedded_email_format(m: str) -> tuple[str, str] | None:
    """``email_format`` — Subject / Greeting / Body / Sign-off layout (greenfield compose, not polish)."""
    if len(m) < 48:
        return None
    no_ef = bool(
        re.search(
            r"\b(no email format|without (?:an?\s+)?email format|not an email format|"
            r"skip (?:the\s+)?email format|don'?t use email format|"
            r"avoid email format|not as an email|no subject line block)\b",
            m,
        )
    )
    if no_ef:
        return None
    revise_only = bool(
        re.search(
            r"\b(rewrite (?:my |this |the )?(?:draft )?|polish (?:my |this )?(?:draft )?|"
            r"proofread (?:my |this )?|improve (?:my |this |the )?draft|copy[- ]?edit)\b",
            m,
        )
    )
    has_draft_artifact = bool(
        re.search(
            r"\b(?:my|this|the)\s+draft\b|draft:\s|here(?:'s| is)\s+(?:my|the)\s+draft\b",
            m,
        )
    )
    if revise_only and has_draft_artifact:
        return None
    want = bool(
        re.search(
            r"\b((?:write|draft|compose|prepare) (?:an?\s+)?email|"
            r"email (?:to|for) (?:the |my |our |a )?|"
            r"email format|as an email|in email format|"
            r"follow[- ]up email|outreach email|"
            r"reply (?:by|as|in) email|email (?:message|template))\b",
            m,
        )
    )
    if not want:
        return None
    if not re.search(
        r"\b(write|draft|compose|prepare|notify|inform|send|follow[- ]?up|"
        r"apolog|request|update|client|customer|colleague|manager|team|"
        r"recipient|message|explain|describe)\b",
        m,
    ):
        return None
    instr = (
        "The user wants a **formatted email**: use labels **Subject:** (one line), "
        "a **Greeting** (Hi/Dear …), concise body paragraphs, and a **Sign-off** "
        "(Thanks/Best regards + optional name/role)—ready to paste into an email client; "
        "do not answer as a generic essay about how to write emails."
    )
    return instr, "email_format"


def _embedded_meeting_agenda(m: str) -> tuple[str, str] | None:
    """``meeting_agenda`` — timeboxed meeting run-of-show (distinct from ``action_plan`` owner tables)."""
    if len(m) < 48:
        return None
    no_ma = bool(
        re.search(
            r"\b(no meeting agenda|without (?:a\s+)?meeting agenda|not a meeting agenda|"
            r"skip (?:the\s+)?meeting agenda|don'?t use meeting agenda|"
            r"avoid meeting agenda (?:format|section)|"
            r"no agenda format|skip (?:the\s+)?agenda format)\b",
            m,
        )
    )
    if no_ma:
        return None
    want = bool(
        re.search(
            r"\b(meeting agenda(?:\s+format)?|agenda format|"
            r"prepare (?:an?\s+)?agenda|draft (?:an?\s+)?agenda|"
            r"run[- ]of[- ]show|meeting run[- ]of[- ]show|"
            r"timeboxed agenda|agenda with time(?:\s+)?boxes?|"
            r"agenda for (?:the |our |a )?(?:meeting|sync|workshop|kickoff|review))\b",
            m,
        )
    )
    if not want:
        return None
    if not re.search(
        r"\b(meeting|sync|workshop|kickoff|review|standup|retro|planning|"
        r"session|facilitate|host|schedule|attendees|discuss|outline|write|prepare)\b",
        m,
    ):
        return None
    instr = (
        "The user wants a **meeting agenda**: use markdown headings **Meeting title**, "
        "**Objective** (1–2 lines), optional **Attendees**, **Agenda** as timeboxed items "
        "(e.g. `5 min — Topic`), **Pre-reads / prep** if relevant, and **Decisions needed**—"
        "keep it scannable for a live facilitator; not a checkbox checklist or owner/due-date table."
    )
    return instr, "meeting_agenda"


def _embedded_topic_guard(m: str) -> tuple[str, str] | None:
    """``topic_guard`` — user asked to omit specific subjects from the reply."""
    if len(m) < 44:
        return None
    avoid = bool(
        re.search(
            r"\b(don'?t mention|do not mention|avoid (?:mentioning|discussing|talking about)|"
            r"skip (?:mentioning|discussing)|leave out|no discussion of|"
            r"do not discuss|steer clear of|without mentioning|"
            r"don'?t bring up|do not bring up|exclude (?:any )?discussion of)\b",
            m,
        )
    )
    must_cover = bool(
        re.search(
            r"\b(make sure to mention|be sure to (?:mention|cover)|must (?:mention|cover|discuss)|"
            r"you must (?:mention|cover)|focus (?:only )?on|only discuss|"
            r"include (?:a )?section on)\b",
            m,
        )
    )
    if not avoid or must_cover:
        return None
    if not re.search(
        r"\b(explain|describe|what|how|why|help|write|draft|answer|summarize|compare|"
        r"faq|policy|guide|customer|user|team|product)\b",
        m,
    ):
        return None
    instr = (
        "The user set **topic guardrails**: do **not** mention or elaborate on subjects they flagged to "
        "avoid in this message (for example pricing, competitors, politics, or internal tools)—even if "
        "tangentially relevant; you may note briefly that you are omitting a flagged topic."
    )
    return instr, "topic_guard"


def _embedded_topic_must(m: str) -> tuple[str, str] | None:
    """``topic_must`` — user required specific subjects or sections in the reply."""
    if len(m) < 44:
        return None
    must_cover = bool(
        re.search(
            r"\b(make sure to mention|be sure to (?:mention|cover)|must (?:mention|cover|discuss|include)|"
            r"you must (?:mention|cover)|need (?:you )?to (?:mention|cover)|"
            r"include (?:a )?(?:section|subsection) (?:on|about|for)|"
            r"dedicated section (?:on|about|for)|don'?t skip (?:mentioning|discussing)|"
            r"address (?:the )?(?:topic|question) of|cover (?:the )?topic of)\b",
            m,
        )
    )
    avoid = bool(
        re.search(
            r"\b(don'?t mention|do not mention|avoid (?:mentioning|discussing|talking about)|"
            r"skip (?:mentioning|discussing)|leave out|no discussion of|"
            r"do not discuss|steer clear of|without mentioning|"
            r"don'?t bring up|do not bring up|exclude (?:any )?discussion of)\b",
            m,
        )
    )
    if not must_cover or avoid:
        return None
    if not re.search(
        r"\b(explain|describe|what|how|why|help|write|draft|answer|summarize|compare|"
        r"faq|policy|guide|customer|user|team|product|outline|prepare)\b",
        m,
    ):
        return None
    instr = (
        "The user set **required topics**: explicitly **cover** each subject or section they asked "
        "you to mention (use clear headings or bullets per required item); do not omit flagged "
        "must-cover topics even if they seem tangential."
    )
    return instr, "topic_must"


def _embedded_answer_frame(m: str) -> tuple[str, str] | None:
    """``frame_star`` / ``frame_prep`` / ``frame_irac`` — named professional answer scaffolds."""
    if len(m) < 48:
        return None
    if not re.search(
        r"\b(answer|write|explain|describe|respond|interview|behavioral|prompt|story|"
        r"example|scenario|case|memo|report|outline)\b",
        m,
    ):
        return None
    candidates: list[tuple[str, str]] = []
    if re.search(
        r"\b(star format|star method|situation[- ]task[- ]action[- ]result|"
        r"\bstar\b.{0,30}(?:situation|task|action|result))\b",
        m,
    ):
        candidates.append(
            (
                "Structure the answer using **STAR** with markdown headings **Situation**, **Task**, "
                "**Action**, and **Result** (one short paragraph each unless a length cap applies).",
                "frame_star",
            )
        )
    if re.search(r"\b(prep format|prep method|point[- ]reason[- ]example[- ]point)\b", m):
        candidates.append(
            (
                "Structure the answer using **PREP**: **Point**, **Reason**, **Example**, then restate the **Point**.",
                "frame_prep",
            )
        )
    if re.search(r"\b(irac format|irac method|issue[- ]rule[- ]analysis[- ]conclusion)\b", m):
        candidates.append(
            (
                "Structure the answer using **IRAC**: **Issue**, **Rule**, **Analysis**, **Conclusion**.",
                "frame_irac",
            )
        )
    if len(candidates) != 1:
        return None
    return candidates[0]


def _embedded_simple_audience(m: str) -> bool:
    """True if a longer prompt asks for child-level / lay explanations (ELI5-style) in prose."""
    if len(m) < 40:
        return False
    if re.search(
        r"\b(expert mode|technical audience|assume i'?m technical|phd level|for experts|deep technical)\b",
        m,
    ):
        return False
    if not re.search(
        r"\b(eli5|explain like i'?m(?:\s+a)? five|like i'?m(?:\s+a)? five\b|"
        r"for (?:my )?kids to understand|total beginner|i'?m\s+a\s+beginner\b|beginner\s+here\b|"
        r"non-technical (?:parent|reader|manager|audience)|"
        r"lay audience|no technical background|zero prior knowledge)\b",
        m,
    ):
        return False
    return bool(
        re.search(
            r"\b(why|how|what|when|where|explain|describe|tell me|help me (?:to )?understand|walk me through|"
            r"learn about|new to)\b",
            m,
        )
    )


def _embedded_technical_audience(m: str) -> bool:
    """True if a longer prompt asks for expert-depth explanations (not short *Expert mode* controls)."""
    if len(m) < 40:
        return False
    if re.search(
        r"\b(eli5|explain like i'?m(?:\s+a)? five|total beginner|i'?m\s+a\s+beginner\b|beginner\s+here\b|"
        r"lay audience|no technical background|zero prior knowledge|explain simply)\b",
        m,
    ):
        return False
    if not re.search(
        r"\b(expert mode|technical audience|assume i'?m technical|phd level|for experts|deep technical|"
        r"staff engineer audience|senior (?:sre|eng|engineer) audience|"
        r"use jargon freely|skip the basics|don'?t dumb (?:it )?down|"
        r"peer[- ]level technical|internals[- ]focused|implementation[- ]heavy)\b",
        m,
    ):
        return False
    return bool(
        re.search(
            r"\b(why|how|what|when|where|explain|describe|tell me|walk me through|"
            r"compare|design|architect|debug|troubleshoot|analyze|review|implement)\b",
            m,
        )
    )


def _embedded_register_tone(m: str) -> str | None:
    """One-shot formal vs casual register when prose names an audience (not the short *Formal tone* control)."""
    if len(m) < 48:
        return None
    formal = re.search(
        r"\b(board-ready|for regulators|regulatory filing|formal memo|audit[- ]friendly|"
        r"client-facing|for (?:the\s+)?board(?:\s+of\s+directors)?\b|for leadership review|"
        r"executive summary for|c[- ]suite|for executives|board presentation|investor[- ]ready|"
        r"sec filing tone)\b",
        m,
    )
    casual = re.search(
        r"\b(slack message|teams message to the team|keep it casual|casual tone|friendly teammate|"
        r"like you(?:'re|\s+are)\s+my coworker|water cooler|informal note|keep it light|"
        r"pub chat|chatty tone)\b",
        m,
    )
    if formal and not casual:
        return "formal"
    if casual and not formal:
        return "casual"
    return None


def _embedded_verbosity(m: str) -> str | None:
    """``brief`` vs ``detailed`` reply length (not short *Be brief* controls; distinct from ``len_cap``)."""
    if len(m) < 44:
        return None
    detailed = bool(
        re.search(
            r"\b(more detail|go deeper|in greater detail|explain thoroughly|longer answers?|"
            r"detailed answers?|comprehensive explanation|deep dive|"
            r"don'?t skimp on detail|fuller explanation|elaborate (?:on|please)|"
            r"walk me through (?:it )?in depth)\b",
            m,
        )
    )
    brief = bool(
        re.search(
            r"\b(be brief|stay brief|keep it short|short answers?|answer briefly|concise replies?|"
            r"keep (?:your )?answer short|just the essentials|high[- ]level summary only|"
            r"don'?t ramble|brevity (?:please|is key))\b",
            m,
        )
    )
    if brief and detailed:
        return None
    if brief:
        return "brief"
    if detailed:
        return "detailed"
    return None


def _embedded_output_format(m: str) -> str | None:
    """``json`` vs ``plain`` output shape (not short *Answer in JSON* / *Plain text only* controls)."""
    if len(m) < 40:
        return None
    plain = bool(
        re.search(
            r"\b(plain text only|no json(?:\s+block)?|not json|avoid json|skip json|"
            r"no structured output|don'?t use json|without json|"
            r"normal (?:plain )?text(?:\s+only)?|prose only.{0,30}no json|"
            r"don'?t (?:return|emit|output) json)\b",
            m,
        )
    )
    json_fmt = bool(
        re.search(
            r"\b(valid json|return json|reply in json|answer in json|json output|structured json|"
            r"json object|json array|as json\b|as a json|machine[- ]readable json|emit json|"
            r"serialize (?:to|as) json|output as json|respond with json)\b",
            m,
        )
    )
    if plain and json_fmt:
        return None
    if plain:
        return "plain"
    if json_fmt:
        return "json"
    return None


def _embedded_speculation(m: str) -> str | None:
    """``strict`` vs ``creative`` speculation level (not short *No speculation* / *Brainstorm freely* controls)."""
    if len(m) < 44:
        return None
    creative = bool(
        re.search(
            r"\b(brainstorm freely|speculate freely|wild ideas(?:\s+ok)?|creative speculation|"
            r"go ahead and guess|reasonable guesses welcome|speculate a bit|"
            r"blue[- ]sky (?:thinking|ideas)|throw out (?:some )?possibilities|"
            r"explore hypotheticals|what[- ]if scenarios (?:are )?welcome|"
            r"ideation (?:mode|session)|open[- ]ended brainstorming)\b",
            m,
        )
    )
    strict = bool(
        re.search(
            r"\b(don'?t guess|no guessing|avoid guessing|only high confidence|stick to (?:the\s+)?facts|"
            r"avoid halluc|no hallucinations|don'?t hallucinate|if you don'?t know say|"
            r"if unsure say|say when you(?:'re|\s+are)\s+unsure|no speculation|avoid speculation|"
            r"don'?t speculate|fact[- ]checked|grounded only|evidence[- ]based only|"
            r"only if (?:you(?:'re|\s+are)\s+)?(?:certain|sure)|do not invent (?:facts|numbers))\b",
            m,
        )
    )
    if creative and strict:
        return None
    if strict:
        return "strict"
    if creative:
        return "creative"
    return None


def _embedded_answer_lead(m: str) -> str | None:
    """``tldr_first`` vs ``direct`` answer opening (not short *TLDR first* / *Answer directly* controls)."""
    if len(m) < 44:
        return None
    direct = bool(
        re.search(
            r"\b(no tldr|skip (?:the )?summary|answer directly|without a (?:summary|tldr)|"
            r"no executive summary|don'?t (?:add|give) a tldr|direct answer only|"
            r"jump straight to the answer|no summary (?:upfront|at the top)|"
            r"get straight to the (?:answer|point)|omit (?:the )?(?:opening )?summary)\b",
            m,
        )
    )
    tldr = bool(
        re.search(
            r"\b(tl;?dr first|tldr first|lead with (?:a\s+)?(?:one[- ]line\s+)?summary|summary first|"
            r"executive summary first|bottom line up front|bluf|"
            r"start with (?:a\s+)?(?:short\s+)?summary|headline first|"
            r"give me the (?:key\s+)?takeaway first)\b",
            m,
        )
    )
    if direct and tldr:
        return None
    if direct:
        return "direct"
    if tldr:
        return "tldr_first"
    return None


def _embedded_recommendation_first(m: str) -> tuple[str, str] | None:
    """``recommendation_first`` — open with an explicit recommendation before rationale (not generic BLUF)."""
    if len(m) < 44:
        return None
    no_rec = bool(
        re.search(
            r"\b(no recommendation (?:upfront|first|at the top)|"
            r"don'?t (?:lead with|start with|give) (?:your\s+)?recommendation|"
            r"skip (?:the\s+)?(?:upfront\s+)?recommendation|"
            r"without (?:an?\s+)?(?:upfront\s+)?recommendation|"
            r"recommendation (?:only\s+)?at the end|"
            r"conclude with (?:your\s+)?recommendation|"
            r"end with (?:your\s+)?recommendation|"
            r"hold (?:your\s+)?recommendation until (?:the\s+)?end)\b",
            m,
        )
    )
    if no_rec:
        return None
    want = bool(
        re.search(
            r"\b(lead with (?:your\s+)?recommendation|recommendation first|"
            r"state your recommendation (?:upfront|first|at the top)|"
            r"start with (?:your\s+)?(?:clear\s+)?recommendation|"
            r"give (?:your\s+)?recommendation (?:upfront|first|at the top)|"
            r"upfront recommendation (?:then|before)|"
            r"recommendation before (?:the\s+)?(?:analysis|rationale|details)|"
            r"open with (?:your\s+)?recommendation|"
            r"lead with what you recommend)\b",
            m,
        )
    )
    if not want:
        return None
    if not re.search(
        r"\b(recommend|choose|pick|select|decide|advise|should we|which (?:option|approach|tool|vendor)|"
        r"go with|prefer|adoption|migrate|switch|buy|build vs buy)\b",
        m,
    ):
        return None
    instr = (
        "The user wants **recommendation-first** structure: open with a short **Recommendation** line "
        "that states clearly what you advise (one concrete choice or go/no-go), **then** provide "
        "supporting rationale—do not bury the recommendation after long background."
    )
    return instr, "recommendation_first"


def _embedded_go_no_go(m: str) -> tuple[str, str] | None:
    """``go_no_go`` — explicit Go / No-go / Conditional gate verdict for approval reviews."""
    if len(m) < 48:
        return None
    no_gng = bool(
        re.search(
            r"\b(no go[- ]?/?no[- ]?go|without (?:a\s+)?go[- ]?/?no[- ]?go|"
            r"skip (?:the\s+)?go[- ]?/?no[- ]?go|not a go[- ]?/?no[- ]?go|"
            r"don'?t (?:include|use) go[- ]?/?no[- ]?go|"
            r"avoid go[- ]?/?no[- ]?go (?:format|section|verdict)|"
            r"no proceed[- ]or[- ]halt section)\b",
            m,
        )
    )
    if no_gng:
        return None
    want = bool(
        re.search(
            r"\b(go[- ]?/?no[- ]?go (?:decision|recommendation|verdict|call|assessment)|"
            r"go or no[- ]go|no[- ]go or go|"
            r"proceed or (?:halt|pause|stop)|halt or proceed|"
            r"should we proceed (?:or|vs\.?) (?:pause|halt|stop|wait)|"
            r"gate review (?:decision|memo|recommendation)|"
            r"approval gate (?:decision|review)|"
            r"launch gate (?:decision|review)|"
            r"explicit (?:go|no[- ]go) (?:verdict|recommendation))\b",
            m,
        )
    )
    if not want:
        return None
    if not re.search(
        r"\b(rollout|launch|release|migrate|deploy|production|project|initiative|"
        r"approve|approval|steering|committee|board|gate|proceed|write|memo|report|assess|decide)\b",
        m,
    ):
        return None
    instr = (
        "The user wants a **go/no-go gate** verdict: open with a bold **Go**, **No-go**, or "
        "**Conditional go** line (pick one), then brief **Criteria met**, **Risks / blockers**, and "
        "**Conditions** (if conditional)—keep it decision-ready for an approval meeting."
    )
    return instr, "go_no_go"


def _embedded_actionability(m: str) -> str | None:
    """``commands`` vs ``conceptual`` actionability (not short *Make it actionable* / *Conceptual only* controls)."""
    if len(m) < 44:
        return None
    conceptual = bool(
        re.search(
            r"\b(conceptual only|high level only|no commands|without commands|no shell commands|"
            r"avoid command dumps|don'?t include (?:bash|shell|terminal) commands|"
            r"focus on concepts(?:\s+and\s+rationale)?|strategic discussion only|"
            r"architecture overview only|no runnable snippets|theory and tradeoffs only)\b",
            m,
        )
    )
    commands = bool(
        re.search(
            r"\b(include (?:a\s+)?(?:bash|sh|zsh|powershell) snippet|run(?:nable)? commands?|"
            r"copy[- ]paste (?:into )?(?:the\s+)?(?:terminal|shell)|"
            r"curl (?:one[- ]?liner|example)|one[- ]liner (?:for|to)|"
            r"bash one[- ]liner|powershell command|terminal commands?|"
            r"give me (?:the\s+)?(?:exact\s+)?commands?|include kubectl|"
            r"docker (?:run|compose) (?:example|snippet)|(?:pip|npm|pnpm|yarn) install (?:line|command)|"
            r"ready[- ]to[- ]run (?:script|snippet)|paste(?:able)? commands?)\b",
            m,
        )
    )
    if conceptual and commands:
        return None
    if conceptual:
        return "conceptual"
    if commands:
        return "commands"
    return None


def _embedded_confidence_tone(m: str) -> str | None:
    """``transparent`` vs ``assertive`` confidence (not short *Flag assumptions* / *Be decisive* controls)."""
    if len(m) < 44:
        return None
    skip_transparent = bool(
        re.search(
            r"\b(no assumptions? section|skip (?:the\s+)?assumptions?|don'?t list assumptions|"
            r"without caveats|no caveats|omit limitations)\b",
            m,
        )
    )
    transparent = (
        not skip_transparent
        and (
            bool(
                re.search(
                    r"\b(state|list|spell out|call out|identify|enumerate|label)\s+"
                    r"(?:your\s+|the\s+|our\s+|key\s+|main\s+)?(?:key\s+|main\s+)?assumptions?\b",
                    m,
                )
            )
            or bool(
                re.search(
                    r"\b(assumptions?\s+and\s+limitations?|limitations?\s+and\s+caveats?|"
                    r"limitations?\s+section|caveats?\s+(?:first|upfront|at\s+the\s+top)|"
                    r"upfront\s+caveats?|scope\s+and\s+assumptions?|boundary\s+conditions?|"
                    r"what\s+(?:we\s+)?(?:are\s+)?assuming\b|"
                    r"explicit(?:ly)?\s+about\s+(?:limitations?|uncertainty|what\s+we\s+don'?t\s+know)|"
                    r"where\s+this\s+(?:breaks?\s+down|stops?\s+working|doesn'?t\s+apply))\b",
                    m,
                )
            )
            or bool(
                re.search(
                    r"\b(flag|surface|highlight)\s+(?:key\s+)?(?:uncertainties|unknowns|gaps|risk\s+factors)\b",
                    m,
                )
            )
        )
    )
    assertive = bool(
        re.search(
            r"\b(be decisive|don'?t hedge|give firm answers?|minimal hedging|"
            r"sound\s+confident|avoid disclaimers|confident (?:recommendation|tone)|"
            r"take a clear stance|no throat[- ]clearing|decisive recommendation)\b",
            m,
        )
    )
    if transparent and assertive:
        return None
    if transparent:
        return "transparent"
    if assertive:
        return "assertive"
    return None


def _embedded_example_density(m: str) -> str | None:
    """``rich`` or ``sparse`` from prose (not the short *Include examples* / *Skip examples* control lines)."""
    if len(m) < 44:
        return None
    sparse = bool(
        re.search(
            r"\b(skip examples?|don'?t add examples?|don'?t include examples?|"
            r"without examples?|keep (?:it\s+)?abstract|theory[- ]only|abstract only|"
            r"example[- ]free|no examples? (?:please|in your (?:answer|reply))|"
            r"avoid illustrative examples?)\b",
            m,
        )
    )
    rich = bool(
        re.search(
            r"\b(include (?:at\s+least\s+)?(?:one|two|a few)\s+concrete examples?|"
            r"at least one (?:short\s+)?concrete example|"
            r"illustrate (?:this|that|it)\s+with (?:a\s+)?(?:concrete\s+|real[- ]world\s+)?example|"
            r"worked example|walk(?:\s+me)? through (?:a\s+)?(?:small|tiny|toy|minimal)\s+example|"
            r"\b(?:a\s+)?toy example\b|miniature scenario|"
            r"ground (?:this|it|your answer) in (?:a\s+)?(?:concrete\s+)?example|"
            r"give (?:me\s+)?a (?:concrete\s+)?example|"
            r"show (?:me\s+)?(?:this\s+)?with (?:a\s+)?(?:concrete\s+)?example)\b",
            m,
        )
    )
    if sparse and rich:
        return None
    if sparse:
        return "sparse"
    if rich:
        return "rich"
    return None


def _embedded_exposition_order(m: str) -> str | None:
    """``definitions_first`` vs ``intuition_first`` from prose (not short *Definitions first* controls)."""
    if len(m) < 48:
        return None
    if re.search(
        r"\b(skip definitions first|don'?t start with definitions|"
        r"no formal definitions upfront)\b",
        m,
    ):
        return None
    if re.search(
        r"\b(skip the intuition|cut the warm[- ]?up|no hand[- ]?wavy intro)\b",
        m,
    ):
        return None
    defn = bool(
        re.search(
            r"\b(define (?:the\s+)?(?:key\s+)?terms? (?:first|before|upfront)|"
            r"definitions?\s+(?:first|before|upfront)|"
            r"start with (?:a\s+)?(?:brief\s+)?definition|"
            r"formal definitions? (?:first|before)|"
            r"precise definitions? before|"
            r"terminology (?:first|upfront)|"
            r"establish definitions before|"
            r"glossary[- ]style (?:intro|opening)|"
            r"define jargon before)\b",
            m,
        )
    )
    intu = bool(
        re.search(
            r"\b(intuition (?:first|before (?:the\s+)?(?:math|formal|proof|details?))|"
            r"big[- ]picture (?:first|before|then)|"
            r"high[- ]level intuition (?:first|before)|"
            r"motivation before (?:the\s+)?(?:formal|proof|math)|"
            r"informal (?:picture|overview) before|"
            r"start with (?:the\s+)?(?:big\s+picture|intuition|high[- ]level sketch)|"
            r"warm(?:\s+up)? with (?:an?\s+)?intuitive)\b",
            m,
        )
    )
    if defn and intu:
        return None
    if defn:
        return "definitions_first"
    if intu:
        return "intuition_first"
    return None


def _embedded_glossary_section(m: str) -> tuple[str, str] | None:
    """``glossary`` — include a short glossary / key-terms definitions section."""
    if len(m) < 48:
        return None
    no_glossary = bool(
        re.search(
            r"\b(no glossary|without glossary|skip glossary|avoid glossary|don'?t (?:include|add) glossary)\b",
            m,
        )
    )
    if no_glossary:
        return None

    no_headings = bool(
        re.search(
            r"\b(flat answer|no section headings|avoid markdown headings|continuous prose only|prose without headings)\b",
            m,
        )
    )

    want = bool(
        re.search(
            r"\b(glossary(?:[- ]style)?|provide (?:a )?glossary|include (?:a )?glossary|"
            r"terms and definitions|define (?:the )?(?:key )?terms)\b",
            m,
        )
    )
    if not want or no_headings:
        return None

    instr = (
        "The user requested a **Glossary**: include a short **Glossary** section defining 3–8 "
        "key terms mentioned in the prompt (especially jargon). Provide each definition as a "
        "single concise sentence."
    )
    return instr, "glossary"


def _embedded_spelling_locale(m: str) -> tuple[str, str] | None:
    """``spelling_uk`` / ``spelling_us`` — British vs American English spelling in the reply."""
    if len(m) < 44:
        return None
    uk = bool(
        re.search(
            r"\b(british english|uk english|uk spelling|british spelling|"
            r"use british spellings?|spell(?:ing)? (?:in )?british english|"
            r"en[- ]?gb (?:spelling|english)|"
            r"colour not color|favour not favor|organise not organize)\b",
            m,
        )
    )
    us = bool(
        re.search(
            r"\b(american english|us english|us spelling|american spelling|"
            r"use american spellings?|spell(?:ing)? (?:in )?american english|"
            r"en[- ]?us (?:spelling|english)|"
            r"color not colour|favor not favour|organize not organise)\b",
            m,
        )
    )
    if uk and us:
        return None
    if uk:
        instr = (
            "The user asked for **British English (UK) spelling** throughout the reply "
            "(e.g. colour, organise, centre, licence)—not US forms unless quoting source text verbatim."
        )
        return instr, "spelling_uk"
    if us:
        instr = (
            "The user asked for **American English (US) spelling** throughout the reply "
            "(e.g. color, organize, center, license)—not UK forms unless quoting source text verbatim."
        )
        return instr, "spelling_us"
    return None


def _embedded_timeline_order(m: str) -> tuple[str, str] | None:
    """``timeline_chron`` / ``timeline_reverse`` — chronological vs reverse-chronological event layout."""
    if len(m) < 48:
        return None
    if re.search(
        r"\b(no timeline|not a timeline|without a timeline|skip (?:the )?timeline|"
        r"don'?t use a timeline)\b",
        m,
    ):
        return None
    reverse = bool(
        re.search(
            r"\b(reverse chronological|anti[- ]chronological|newest first|most recent first|"
            r"latest first|work backwards|backward in time|from latest to earliest|"
            r"most recent event first)\b",
            m,
        )
    )
    chron = bool(
        re.search(
            r"\b(?:in chronological order|(?<!reverse )chronological order|time order|"
            r"timeline format|as a timeline|event timeline|what happened when|"
            r"from earliest to latest|oldest first|earliest first|"
            r"history in order)\b",
            m,
        )
    )
    if reverse and chron:
        return None
    if not re.search(
        r"\b(explain|describe|summarize|outline|what happened|history|incident|outage|"
        r"rollout|migration|deployment|release|postmortem|timeline|events|sequence|"
        r"when did|how did .{0,40} unfold)\b",
        m,
    ):
        return None
    if reverse:
        instr = (
            "The user wants a **reverse-chronological timeline**: list events **newest → oldest** "
            "with short date/time or phase labels (e.g. **Now**, **T+2h**, **Day 0**); one line or "
            "bullet per milestone."
        )
        return instr, "timeline_reverse"
    if chron:
        instr = (
            "The user wants a **chronological timeline**: list events **earliest → latest** "
            "with short date/time or phase labels (e.g. **09:00 UTC**, **Phase 1**, **Day 2**); "
            "one line or bullet per milestone."
        )
        return instr, "timeline_chron"
    return None


def _embedded_writing_voice(m: str) -> tuple[str, str] | None:
    """``voice_second`` / ``voice_third`` — address reader as *you* vs impersonal third person."""
    if len(m) < 48:
        return None
    third = bool(
        re.search(
            r"\b(third person|3rd person|impersonal tone|impersonal voice|"
            r"don'?t address (?:the )?reader as you|avoid second person|"
            r"no second person|don'?t use (?:you|your) (?:throughout|in the reply)|"
            r"refer to (?:the )?user(?:s)? not you|neutral documentation voice|"
            r"formal documentation style.{0,30}not you)\b",
            m,
        )
    )
    second = bool(
        re.search(
            r"\b(?:(?<!avoid )(?<!no )second person|2nd person|"
            r"speak directly to (?:the )?reader|talk to me as the user|"
            r"use you and your throughout|write to me using you|"
            r"directly address me as you|use second[- ]person (?:you|voice))\b",
            m,
        )
    )
    if not second and re.search(r"\baddress (?:the )?reader as you\b", m):
        if not re.search(r"\b(don'?t|do not) address (?:the )?reader as you\b", m):
            second = True
    if second and third:
        return None
    if not re.search(
        r"\b(explain|describe|write|draft|guide|help|walk|tell|outline|"
        r"document|instructions|how (?:do|can|should) i|tutorial|onboarding)\b",
        m,
    ):
        return None
    if second:
        instr = (
            "The user wants **second-person voice**: address the reader as **you/your** "
            "(tutorial or coaching tone)—not impersonal third-person phrasing like "
            "*the user should* unless quoting policy verbatim."
        )
        return instr, "voice_second"
    if third:
        instr = (
            "The user wants **third-person / impersonal voice**: avoid addressing the reader "
            "as **you**; prefer neutral phrasing (*the administrator*, *one*, *the team*) "
            "suited to formal docs or policy text."
        )
        return instr, "voice_third"
    return None


def _embedded_faq_qa_format(m: str) -> tuple[str, str] | None:
    """``faq_qa`` — reply as explicit question-and-answer pairs (``Q:`` / ``A:`` layout)."""
    if len(m) < 48:
        return None
    no_qa = bool(
        re.search(
            r"\b(no q&a format|not q&a format|without q&a|skip q&a format|"
            r"don'?t use q&a|prose not q&a|not in q&a format|"
            r"no question[- ]and[- ]answer pairs?|avoid q&a layout)\b",
            m,
        )
    )
    if no_qa:
        return None
    want = bool(
        re.search(
            r"\b(q&a format|question[- ]and[- ]answer format|questions? and answers? format|"
            r"format as q&a|faq[- ]style q&a|faq q&a layout|"
            r"each question (?:with|followed by) (?:an )?answer|"
            r"question answer pairs?|q:\s*/\s*a: layout|"
            r"use q:\s*and a:\s*headings|pair each question with an answer)\b",
            m,
        )
    )
    if not want:
        return None
    if not re.search(
        r"\b(explain|describe|write|draft|document|outline|prepare|"
        r"faq|support|customer|policy|helpdesk|knowledge base|kb)\b",
        m,
    ):
        return None
    instr = (
        "The user wants a **FAQ Q&A layout**: structure the reply as clear **question → answer** "
        "pairs using markdown labels **Q:** and **A:** (or **Question** / **Answer** headings); "
        "keep each answer concise under its question—not one undifferentiated essay."
    )
    return instr, "faq_qa"


def _embedded_summary_last(m: str) -> tuple[str, str] | None:
    """``summary_last`` — close the reply with a brief recap (complement to ``answer_lead=tldr_first``)."""
    if len(m) < 44:
        return None
    no_end = bool(
        re.search(
            r"\b(no summary at the end|skip (?:the )?(?:closing|final) summary|"
            r"don'?t (?:add|end with) a (?:tldr|summary) at the end|"
            r"without a closing summary|no recap at the end)\b",
            m,
        )
    )
    if no_end:
        return None
    tldr_first = bool(
        re.search(
            r"\b(tl;?dr first|tldr first|summary first|executive summary first|"
            r"bottom line up front|\bbluf\b|lead with (?:a\s+)?(?:one[- ]line\s+)?summary|"
            r"(?:key\s+)?takeaway first|headline first)\b",
            m,
        )
    )
    end_sum = bool(
        re.search(
            r"\b(summary at the end|tldr at the (?:bottom|end)|executive summary at the end|"
            r"wrap up with (?:a\s+)?(?:brief\s+)?summary|close with (?:a\s+)?(?:one[- ]line\s+)?summary|"
            r"end with (?:a\s+)?(?:brief\s+)?(?:summary|tldr|recap|key takeaway)|"
            r"recap at the (?:bottom|end)|closing summary|final summary (?:line|paragraph))\b",
            m,
        )
    )
    if not end_sum or tldr_first:
        return None
    if not re.search(
        r"\b(explain|describe|write|draft|summarize|report|outline|brief|memo|answer|"
        r"analysis|review|compare|recommend)\b",
        m,
    ):
        return None
    instr = (
        "The user wants a **closing summary**: after the main answer, end with a short "
        "**Summary** or **TL;DR** line (1–3 sentences) that recaps the key takeaway—"
        "do **not** open with that recap (unless they also asked for BLUF elsewhere)."
    )
    return instr, "summary_last"


def _embedded_decision_matrix(m: str) -> tuple[str, str] | None:
    """``decision_matrix`` — criteria × options markdown table for side-by-side evaluation."""
    if len(m) < 48:
        return None
    no_matrix = bool(
        re.search(
            r"\b(no decision matrix|without a (?:decision|comparison|feature) matrix|"
            r"not a (?:decision|comparison|feature) matrix|skip the matrix|"
            r"don'?t use a (?:decision|comparison|feature) matrix|"
            r"avoid a (?:decision|comparison|feature) matrix|"
            r"no matrix (?:format|table))\b",
            m,
        )
    )
    if no_matrix:
        return None
    want = bool(
        re.search(
            r"\b(decision matrix|comparison matrix|feature matrix|"
            r"evaluation matrix|criteria matrix|"
            r"score each option (?:on|against|across)|"
            r"matrix (?:comparing|of) (?:the )?(?:options|vendors|tools|alternatives|platforms)|"
            r"options (?:as|in) columns?(?: and criteria as rows?)?|"
            r"criteria (?:as|in) rows?(?: and options as columns?)?|"
            r"side[- ]by[- ]side matrix|"
            r"rate each option (?:on|against) (?:each|the) criteri(?:a|on))\b",
            m,
        )
    )
    if not want:
        return None
    if not re.search(
        r"\b(compare|choose|pick|select|evaluate|decide|recommend|rank|"
        r"vendor|tool|option|alternative|approach|platform|solution)\b",
        m,
    ):
        return None
    instr = (
        "The user wants a **decision matrix**: include a markdown **table** with **options/alternatives "
        "as columns** and **evaluation criteria as rows** (cells: short scores, ratings, or ✓/✗). "
        "Add a one-line legend if you use symbols; keep supporting prose outside the table."
    )
    return instr, "decision_matrix"


def _embedded_build_vs_buy(m: str) -> tuple[str, str] | None:
    """``build_vs_buy`` — structured Build (in-house) vs Buy (vendor/SaaS) decision layout."""
    if len(m) < 48:
        return None
    no_bvb = bool(
        re.search(
            r"\b(no build[- ]vs[- ]buy|without (?:a\s+)?build[- ]vs[- ]buy|"
            r"skip (?:the\s+)?build[- ]vs[- ]buy|not a build[- ]vs[- ]buy|"
            r"don'?t use build[- ]vs[- ]buy|avoid build[- ]vs[- ]buy (?:analysis|section)|"
            r"no make[- ]vs[- ]buy section)\b",
            m,
        )
    )
    if no_bvb:
        return None
    want = bool(
        re.search(
            r"\b(build[- ]vs[- ]buy|build[- ]versus[- ]buy|make[- ]vs[- ]buy|make[- ]versus[- ]buy|"
            r"build or buy|make or buy|"
            r"in[- ]house vs (?:vendor|outsource|saas|third[- ]party)|"
            r"build in[- ]house (?:vs\.?|versus|or) (?:buy|purchase|vendor)|"
            r"custom build vs (?:commercial|off[- ]the[- ]shelf|saas|vendor)|"
            r"diy vs (?:buy|purchase|vendor solution))\b",
            m,
        )
    )
    if not want:
        return None
    if not re.search(
        r"\b(build|buy|vendor|outsource|saas|platform|tool|service|solution|"
        r"decide|evaluate|recommend|assess|choose|write|describe|outline|report|memo)\b",
        m,
    ):
        return None
    instr = (
        "The user wants a **build vs buy** analysis: structure the answer with markdown headings "
        "**Build (in-house)** and **Buy (vendor/SaaS)** (bullets under each on cost, time, risk, "
        "and fit), then a brief **Recommendation** line—do not bury the choice after long background."
    )
    return instr, "build_vs_buy"


def _embedded_one_pager(m: str) -> tuple[str, str] | None:
    """``one_pager`` — single-page executive brief with fixed scannable sections."""
    if len(m) < 48:
        return None
    no_op = bool(
        re.search(
            r"\b(no one[- ]pager|without (?:a\s+)?one[- ]pager|not a one[- ]pager|"
            r"skip (?:the\s+)?one[- ]pager|don'?t use one[- ]pager|"
            r"avoid one[- ]pager (?:format|section|layout)|"
            r"no single[- ]page (?:brief|memo format))\b",
            m,
        )
    )
    if no_op:
        return None
    bluf_first = bool(
        re.search(
            r"\b(tl;?dr first|tldr first|summary first|executive summary first|"
            r"bottom line up front|\bbluf\b|lead with (?:a\s+)?(?:one[- ]line\s+)?summary)\b",
            m,
        )
    )
    end_sum = bool(
        re.search(
            r"\b(summary at the end|tldr at the (?:bottom|end)|executive summary at the end|"
            r"wrap up with (?:a\s+)?(?:brief\s+)?summary|close with (?:a\s+)?(?:one[- ]line\s+)?summary)\b",
            m,
        )
    )
    if bluf_first or end_sum:
        return None
    want = bool(
        re.search(
            r"\b(one[- ]pager(?:\s+format|\s+memo|\s+brief|\s+summary)?|"
            r"one page (?:memo|brief|summary|write[- ]up|document)|"
            r"single[- ]page (?:brief|memo|summary|executive brief)|"
            r"executive one[- ]pager|"
            r"fit(?:s|ting)? on (?:a\s+)?single page|"
            r"one[- ]page (?:executive\s+)?(?:brief|memo|summary))\b",
            m,
        )
    )
    if not want:
        return None
    if not re.search(
        r"\b(write|draft|prepare|outline|describe|brief|memo|report|"
        r"leadership|executive|steering|board|stakeholder|committee|"
        r"initiative|program|proposal|decision|update)\b",
        m,
    ):
        return None
    instr = (
        "The user wants a **one-pager** executive brief: use compact markdown headings "
        "**Title / Purpose**, **Context**, **Problem / Opportunity**, **Recommendation** "
        "(1–2 sentences), **Key points** (3–5 bullets), **Next steps**, and brief "
        "**Risks / dependencies**—keep it scannable on one screen; avoid long background prose."
    )
    return instr, "one_pager"


def _embedded_action_plan(m: str) -> tuple[str, str] | None:
    """``action_plan`` — actionable items with owners and due dates (not ``- [ ]`` checklists)."""
    if len(m) < 48:
        return None
    no_ap = bool(
        re.search(
            r"\b(no action plan|without (?:an\s+)?action plan|not an action plan|"
            r"skip (?:the\s+)?action plan|don'?t use action plan|"
            r"avoid action plan (?:format|section|table)|"
            r"no implementation plan (?:table|format))\b",
            m,
        )
    )
    if no_ap:
        return None
    checklist_only = bool(
        re.search(
            r"\b((?:as a|use a|markdown) checklist|checklist (?:format|style)|"
            r"tick[- ]box(?:es)?|checkbox(?:es)? (?:list|format))\b",
            m,
        )
    )
    if checklist_only:
        return None
    want = bool(
        re.search(
            r"\b(action plan(?:\s+format)?|implementation plan(?:\s+with)?(?:\s+)?owners|"
            r"who does what(?:\s+by when)?|owners? and (?:due dates?|deadlines?|timelines?)|"
            r"assign owners?(?:\s+and)?(?:\s+)?(?:due dates?|deadlines?)|"
            r"delivery plan with owners|work plan with (?:owners|assignees)|"
            r"table of actions? (?:with|and) (?:owners?|due dates?))\b",
            m,
        )
    )
    if not want:
        return None
    if not re.search(
        r"\b(rollout|deploy|launch|migrate|implement|project|program|initiative|"
        r"sprint|workstream|deliverable|plan|outline|write|describe|track|execute)\b",
        m,
    ):
        return None
    instr = (
        "The user wants an **action plan**: list actionable items in a markdown **table** "
        "(or clearly labeled rows) with **Action**, **Owner** (role/team), **Due / target date** "
        "(or phase), and brief **Notes** if needed—group by phase when useful; "
        "use **not** `- [ ]` checkbox checklists unless they also asked for tick-boxes."
    )
    return instr, "action_plan"


def _embedded_raci_matrix(m: str) -> tuple[str, str] | None:
    """``raci`` — Responsible / Accountable / Consulted / Informed role assignment table."""
    if len(m) < 48:
        return None
    no_raci = bool(
        re.search(
            r"\b(no raci|without (?:a\s+)?raci|not a raci|skip (?:the\s+)?raci|"
            r"don'?t use raci|avoid raci (?:matrix|chart|table)|"
            r"no raci (?:matrix|chart|table|section))\b",
            m,
        )
    )
    if no_raci:
        return None
    want = bool(
        re.search(
            r"\b(raci matrix|raci chart|raci table|raci format|"
            r"responsible[, ]+accountable[, ]+consulted[, ]+(?:and )?informed|"
            r"\braci\b.{0,40}(?:responsible|accountable|consulted|informed)|"
            r"r\s*\/\s*a\s*\/\s*c\s*\/\s*i (?:matrix|roles|chart)|"
            r"who is (?:responsible|accountable) (?:vs\.?|and|versus) (?:consulted|informed)|"
            r"assign (?:raci|r\s*\/\s*a\s*\/\s*c\s*\/\s*i) roles)\b",
            m,
        )
    )
    if not want:
        return None
    if not re.search(
        r"\b(project|rollout|migration|initiative|workstream|deliverable|team|"
        r"launch|deployment|program|plan|outline|write|describe|assign|ownership)\b",
        m,
    ):
        return None
    instr = (
        "The user wants a **RACI matrix**: include a markdown **table** with rows for key "
        "tasks/workstreams and columns **R** (Responsible), **A** (Accountable), **C** (Consulted), "
        "**I** (Informed)—use role names or teams in cells; add a one-line legend if needed."
    )
    return instr, "raci"


def _embedded_stakeholder_map(m: str) -> tuple[str, str] | None:
    """``stakeholder_map`` — influence/interest stakeholder table (distinct from ``raci`` task roles)."""
    if len(m) < 48:
        return None
    no_sm = bool(
        re.search(
            r"\b(no stakeholder map|without (?:a\s+)?stakeholder map|not a stakeholder map|"
            r"skip (?:the\s+)?stakeholder map|don'?t use stakeholder map|"
            r"avoid stakeholder (?:map|matrix|analysis)|"
            r"no stakeholder (?:map|matrix|analysis format))\b",
            m,
        )
    )
    if no_sm:
        return None
    raci_only = bool(
        re.search(
            r"\b(raci matrix|raci chart|raci table|"
            r"responsible[, ]+accountable[, ]+consulted[, ]+(?:and )?informed|"
            r"r\s*\/\s*a\s*\/\s*c\s*\/\s*i (?:matrix|roles|chart))\b",
            m,
        )
    )
    if raci_only:
        return None
    want = bool(
        re.search(
            r"\b(stakeholder map(?:\s+format)?|stakeholder matrix|stakeholder analysis|"
            r"map (?:the\s+)?stakeholders?|stakeholder mapping|"
            r"influence[- ](?:interest|impact) (?:matrix|grid|map)|"
            r"power[- ]interest (?:matrix|grid|map)|"
            r"interest[- ]influence (?:matrix|grid)|"
            r"who (?:are|is) (?:the\s+)?stakeholders? (?:and|with) (?:their\s+)?(?:influence|interests))\b",
            m,
        )
    )
    if not want:
        return None
    if not re.search(
        r"\b(project|rollout|migration|initiative|program|change|launch|"
        r"communicate|engage|adopt|implement|outline|write|describe|plan|announce)\b",
        m,
    ):
        return None
    instr = (
        "The user wants a **stakeholder map**: include a markdown **table** with columns "
        "**Stakeholder / group**, **Interest**, **Influence** (High/Med/Low), **Key concerns**, "
        "and **Engagement approach**—optionally add a one-line **Power–Interest** quadrant note; "
        "this is **not** a RACI task-assignment matrix."
    )
    return instr, "stakeholder_map"


def _embedded_swot_analysis(m: str) -> tuple[str, str] | None:
    """``swot`` — Strengths / Weaknesses / Opportunities / Threats strategic layout."""
    if len(m) < 48:
        return None
    no_swot = bool(
        re.search(
            r"\b(no swot|without (?:a\s+)?swot|not a swot|skip (?:the\s+)?swot|"
            r"don'?t use swot|avoid swot|no swot (?:format|section|framework))\b",
            m,
        )
    )
    if no_swot:
        return None
    want = bool(
        re.search(
            r"\b(swot analysis|swot format|swot framework|swot breakdown|"
            r"strengths[, ]+weaknesses[, ]+opportunities[, ]+(?:and )?threats|"
            r"strengths weaknesses opportunities threats|"
            r"s\.w\.o\.t\.|"
            r"\bswot\b.{0,40}(?:strengths|weaknesses|opportunities|threats))\b",
            m,
        )
    )
    if not want:
        return None
    if not re.search(
        r"\b(analy(?:s|z)e|analysis|assess|evaluate|review|plan|strategy|launch|"
        r"product|initiative|market|competitive|position|expansion|rollout|"
        r"describe|write|outline|report|memo)\b",
        m,
    ):
        return None
    instr = (
        "The user wants a **SWOT analysis**: structure the answer with markdown headings "
        "**Strengths**, **Weaknesses**, **Opportunities**, and **Threats** (bullets under each). "
        "Focus on one subject (product, team, initiative, or market position)—not a generic essay."
    )
    return instr, "swot"


def _embedded_pestle_analysis(m: str) -> tuple[str, str] | None:
    """``pestle`` — Political / Economic / Social / Technological / Legal / Environmental macro scan."""
    if len(m) < 48:
        return None
    no_pestle = bool(
        re.search(
            r"\b(no pestle|without (?:a\s+)?pestle|not a pestle|skip (?:the\s+)?pestle|"
            r"don'?t use pestle|avoid pestle|no pestle (?:format|section|framework))\b",
            m,
        )
    )
    if no_pestle:
        return None
    want = bool(
        re.search(
            r"\b(pestle analysis|pestle format|pestle framework|pestle breakdown|"
            r"political[, ]+economic[, ]+social[, ]+technological[, ]+legal[, ]+(?:and )?environmental|"
            r"political economic social technological legal environmental|"
            r"p\.e\.s\.t\.l\.e\.|"
            r"\bpestle\b.{0,40}(?:political|economic|social|technological|legal|environmental))\b",
            m,
        )
    )
    if not want:
        return None
    if not re.search(
        r"\b(analy(?:s|z)e|analysis|assess|evaluate|review|plan|strategy|market|"
        r"expansion|entry|regulatory|policy|macro|environment|industry|"
        r"describe|write|outline|report|memo|initiative)\b",
        m,
    ):
        return None
    instr = (
        "The user wants a **PESTLE analysis**: structure the answer with markdown headings "
        "**Political**, **Economic**, **Social**, **Technological**, **Legal**, and **Environmental** "
        "(bullets under each). Focus on external macro factors affecting one market or initiative."
    )
    return instr, "pestle"


def _embedded_cost_benefit(m: str) -> tuple[str, str] | None:
    """``cost_benefit`` — structured costs vs benefits analysis for business cases."""
    if len(m) < 48:
        return None
    no_cb = bool(
        re.search(
            r"\b(no cost[- ]benefit|without (?:a\s+)?cost[- ]benefit|"
            r"skip (?:the\s+)?cost[- ]benefit|not a cost[- ]benefit|"
            r"don'?t use cost[- ]benefit|avoid cost[- ]benefit (?:format|section)|"
            r"no cba section|skip (?:the\s+)?cba)\b",
            m,
        )
    )
    if no_cb:
        return None
    want = bool(
        re.search(
            r"\b(cost[- ]benefit analysis|cost benefit analysis|"
            r"costs? and benefits? (?:analysis|breakdown|section)|"
            r"benefits? (?:and|vs\.?) costs? (?:analysis|breakdown)|"
            r"\bcba\b (?:format|analysis|section)|"
            r"weigh (?:the\s+)?costs? against (?:the\s+)?benefits?|"
            r"weigh benefits? against costs?|"
            r"costs? versus benefits? (?:analysis|comparison))\b",
            m,
        )
    )
    if not want:
        return None
    if not re.search(
        r"\b(project|proposal|invest|build|migrate|rollout|initiative|business case|"
        r"strategy|plan|evaluate|assess|decide|recommend|write|describe|outline|report|memo)\b",
        m,
    ):
        return None
    instr = (
        "The user wants a **cost-benefit analysis**: structure the answer with markdown headings "
        "**Costs** and **Benefits** (bullets under each), then a brief **Net assessment** line "
        "comparing them—keep dollar/time estimates qualitative unless the user supplied numbers."
    )
    return instr, "cost_benefit"


def _embedded_open_questions(m: str) -> tuple[str, str] | None:
    """``open_questions`` — end section listing unresolved unknowns / TBD items (not user-facing closers)."""
    if len(m) < 48:
        return None
    no_oq = bool(
        re.search(
            r"\b(no open questions?|without (?:an?\s+)?open questions? section|"
            r"skip (?:the\s+)?open questions?|don'?t (?:include|list) open questions?|"
            r"not an open questions? section|avoid (?:an?\s+)?open questions? section|"
            r"no tbd section|skip (?:the\s+)?(?:tbd|unknowns?) section)\b",
            m,
        )
    )
    if no_oq:
        return None
    want = bool(
        re.search(
            r"\b(open questions? section|include (?:an?\s+)?open questions?|"
            r"list (?:the\s+)?open questions?|outstanding questions?|unresolved questions?|"
            r"questions? (?:we )?still need (?:to )?(?:answer|resolve)|"
            r"what(?:'s| is) still (?:unknown|tbd|unclear)|"
            r"(?:information|info) gaps?(?: to (?:flag|note))?|"
            r"unknowns? (?:to|we still need to) (?:flag|resolve|clarify)|"
            r"tbd items?(?: at the end)?|"
            r"end with (?:an?\s+)?open questions? section)\b",
            m,
        )
    )
    if not want:
        return None
    if not re.search(
        r"\b(plan|proposal|memo|report|outline|draft|review|analysis|initiative|"
        r"rollout|strategy|design|recommend|assess|evaluate|write|describe|explain)\b",
        m,
    ):
        return None
    instr = (
        "The user wants an **Open questions** section: after the main answer, add a heading "
        "**Open questions** with 3–6 bullet points listing **unresolved unknowns**, missing data, "
        "or decisions still TBD—do **not** use this section to ask the user rhetorical follow-ups "
        "or stock closers like “let me know if you need more.”"
    )
    return instr, "open_questions"


def _embedded_scenario_cases(m: str) -> tuple[str, str] | None:
    """``scenario_cases`` — Best / base / worst case (or similar) multi-scenario breakdown."""
    if len(m) < 48:
        return None
    no_sc = bool(
        re.search(
            r"\b(no scenarios?|without (?:a\s+)?scenario analysis|skip (?:the\s+)?scenario(?:s)?|"
            r"don'?t use scenarios?|avoid scenario analysis|not a scenario analysis|"
            r"single scenario only|one scenario only|no best[- ]case section)\b",
            m,
        )
    )
    if no_sc:
        return None
    want = bool(
        re.search(
            r"\b(best[- ]case(?:\s*[/,&]\s*(?:base|worst)[- ]case)?|"
            r"worst[- ]case(?:\s*[/,&]\s*(?:base|best)[- ]case)?|"
            r"base[- ]case(?:\s*[/,&]\s*(?:best|worst)[- ]case)?|"
            r"best,?\s+base,?\s+(?:and\s+)?worst[- ]case|"
            r"optimistic,?\s+(?:realistic|base)[, ]+(?:and\s+)?pessimistic|"
            r"scenario analysis|three scenarios?|3 scenarios?|"
            r"multiple scenarios?|range of outcomes?|"
            r"upside[- ]downside[- ]base|bull[- ]base[- ]bear case)\b",
            m,
        )
    )
    if not want:
        return None
    if not re.search(
        r"\b(plan|forecast|budget|revenue|growth|launch|initiative|rollout|strategy|"
        r"project|invest|risk|outlook|memo|report|analysis|assess|evaluate|describe|write|explain)\b",
        m,
    ):
        return None
    instr = (
        "The user wants a **scenario analysis**: structure the answer with markdown headings "
        "**Best case**, **Base case**, and **Worst case** (or clearly labeled optimistic / "
        "realistic / pessimistic scenarios). Under each, give 2–4 bullet points on outcomes, "
        "assumptions, and key triggers—keep it focused on one decision or initiative."
    )
    return instr, "scenario_cases"


def _embedded_postmortem_format(m: str) -> tuple[str, str] | None:
    """``postmortem`` — blameless incident postmortem scaffold (SRE-style sections)."""
    if len(m) < 48:
        return None
    no_pm = bool(
        re.search(
            r"\b(no postmortem|without (?:a\s+)?postmortem|not a postmortem|"
            r"skip (?:the\s+)?postmortem|don'?t use postmortem format|"
            r"avoid postmortem (?:format|sections|template)|"
            r"no post[- ]mortem (?:format|template|sections))\b",
            m,
        )
    )
    if no_pm:
        return None
    want = bool(
        re.search(
            r"\b(postmortem format|post[- ]mortem format|blameless postmortem|"
            r"blameless post[- ]mortem|incident postmortem|postmortem template|"
            r"post[- ]mortem template|postmortem outline|structure (?:as|in) a postmortem|"
            r"write (?:it\s+)?(?:as|in) postmortem format|"
            r"postmortem.{0,50}(?:lessons learned|root cause|action items))\b",
            m,
        )
    )
    if not want:
        return None
    if not re.search(
        r"\b(incident|outage|failure|on[- ]call|sre|deploy|rollback|downtime|"
        r"sev[0-9]|production|service|system|write|draft|outline|describe|explain|report)\b",
        m,
    ):
        return None
    instr = (
        "The user wants a **blameless postmortem** layout: use markdown headings "
        "**Summary**, **Impact**, **Timeline**, **Root cause**, **Lessons learned**, and "
        "**Action items** (short bullets under each). Stay factual and avoid blaming individuals."
    )
    return instr, "postmortem"


def _embedded_sprint_retro(m: str) -> tuple[str, str] | None:
    """``sprint_retro`` — agile sprint retrospective layout (distinct from incident ``postmortem``)."""
    if len(m) < 48:
        return None
    no_sr = bool(
        re.search(
            r"\b(no sprint retro|without (?:a\s+)?sprint retro|not a sprint retro|"
            r"skip (?:the\s+)?sprint retro|don'?t use sprint retro|"
            r"avoid sprint retro(?:spective)? (?:format|sections)|"
            r"no (?:sprint\s+)?retrospective format|"
            r"skip (?:the\s+)?(?:sprint\s+)?retrospective format)\b",
            m,
        )
    )
    if no_sr:
        return None
    postmortem_only = bool(
        re.search(
            r"\b(postmortem format|blameless postmortem|incident postmortem|"
            r"post[- ]mortem format|postmortem outline)\b",
            m,
        )
    )
    if postmortem_only:
        return None
    want = bool(
        re.search(
            r"\b(sprint retro(?:spective)?(?:\s+format)?|"
            r"sprint retrospective(?:\s+format)?|"
            r"agile retro(?:spective)?|scrum retro(?:spective)?|"
            r"retro format|retrospective format|"
            r"run (?:a\s+)?(?:sprint\s+)?retro(?:spective)?|"
            r"facilitate (?:a\s+)?(?:sprint\s+)?retro(?:spective)?)\b",
            m,
        )
    )
    if not want:
        return None
    if not re.search(
        r"\b(sprint|iteration|scrum|agile|team|delivery|release|"
        r"reflect|review|improve|outline|write|describe|facilitate|discuss)\b",
        m,
    ):
        return None
    instr = (
        "The user wants a **sprint retrospective** layout: use markdown headings "
        "**Sprint / period** (one line), **What went well**, **What didn't go well**, "
        "**Ideas / experiments**, and **Action items** (concrete next-sprint improvements)—"
        "stay blameless and team-focused; this is **not** an incident postmortem."
    )
    return instr, "sprint_retro"


def _embedded_five_whys(m: str) -> tuple[str, str] | None:
    """``five_whys`` — iterative Why chain for root-cause analysis (distinct from full postmortem)."""
    if len(m) < 48:
        return None
    no_fw = bool(
        re.search(
            r"\b(no five whys|no 5 whys|without five whys|skip (?:the\s+)?(?:five|5) whys|"
            r"don'?t use (?:the\s+)?(?:five|5) whys|avoid five whys|"
            r"not a five whys|no why chain|skip (?:the\s+)?why chain)\b",
            m,
        )
    )
    if no_fw:
        return None
    want = bool(
        re.search(
            r"\b(five whys|5 whys|five[- ]whys analysis|5[- ]whys analysis|"
            r"five whys (?:method|technique|root cause)|"
            r"root cause (?:using|with|via) (?:the\s+)?(?:five|5) whys|"
            r"ask why (?:five|5) times|why chain analysis|"
            r"iterative whys?|successive whys?)\b",
            m,
        )
    )
    if not want:
        return None
    if not re.search(
        r"\b(incident|outage|failure|bug|defect|problem|issue|root cause|"
        r"debug|diagnose|explain|investigate|analyze|analysis|why did|what caused)\b",
        m,
    ):
        return None
    instr = (
        "The user wants a **5 Whys** root-cause analysis: start with a one-line **Problem statement**, "
        "then numbered **Why 1** … **Why 5** (each answer feeds the next why; stop early if the root "
        "is clear), and end with a **Root cause** summary line—stay blameless and factual."
    )
    return instr, "five_whys"


def _embedded_fishbone(m: str) -> tuple[str, str] | None:
    """``fishbone`` — Ishikawa cause-and-effect diagram by category (complements ``five_whys``)."""
    if len(m) < 48:
        return None
    no_fb = bool(
        re.search(
            r"\b(no fishbone|without (?:a\s+)?fishbone|not a fishbone|"
            r"skip (?:the\s+)?fishbone|don'?t use fishbone|"
            r"avoid fishbone (?:diagram|analysis|format)|"
            r"no ishikawa (?:diagram|analysis)|"
            r"no cause[- ]and[- ]effect diagram)\b",
            m,
        )
    )
    if no_fb:
        return None
    want = bool(
        re.search(
            r"\b(fishbone (?:diagram|analysis|chart|format)|"
            r"ishikawa (?:diagram|analysis|chart|format)|"
            r"cause[- ]and[- ]effect (?:diagram|analysis|chart)|"
            r"fishbone.{0,40}(?:root cause|categories|6m|6 m)|"
            r"6\s*m(?:s)? (?:fishbone|analysis|diagram)|"
            r"diagram the causes? (?:by|into) categories)\b",
            m,
        )
    )
    if not want:
        return None
    if not re.search(
        r"\b(incident|outage|failure|defect|bug|problem|issue|quality|"
        r"process|production|root cause|analyze|analysis|investigate|"
        r"explain|describe|outline|diagnose|why did|what caused)\b",
        m,
    ):
        return None
    instr = (
        "The user wants a **fishbone (Ishikawa)** cause-and-effect analysis: start with "
        "**Problem / Effect** (one line), then markdown headings for cause categories "
        "(e.g. **People**, **Process**, **Technology**, **Environment**, **Materials/Data**, "
        "**Management/Policy**) with 2–4 sub-cause bullets under each; end with a brief "
        "**Likely root cause** line—stay blameless; optional compact ASCII spine is fine."
    )
    return instr, "fishbone"


def _embedded_followup_close(m: str) -> str | None:
    """``minimal`` vs ``suggest`` from prose (not short *No follow-up questions* controls)."""
    if len(m) < 48:
        return None
    minimal = bool(
        re.search(
            r"\b(no questions? at the end|don'?t (?:ask|end) with (?:a\s+)?questions?|"
            r"don'?t ask if i need (?:anything|more) else|don'?t ask whether i need more|"
            r"skip (?:the\s+)?(?:stock\s+)?closer|no follow[- ]up questions (?:at\s+the\s+)?(?:end|please)?|"
            r"don'?t prompt for follow[- ]ups?|finish crisply|stop after the core answer|"
            r"avoid rhetorical closers?|no offers? to help further|"
            r"don'?t (?:close|end) with (?:an?\s+)?(?:offer|invitation) to continue)\b",
            m,
        )
    )
    suggest = bool(
        re.search(
            r"\b(suggest next steps|optional next steps at the end|"
            r"end with (?:brief\s+)?(?:actionable\s+)?next steps|"
            r"close with suggested next actions|what should we do next|"
            r"offer ways to go deeper|give me follow[- ]ups? i can take|"
            r"recommend what to do next|include (?:optional\s+)?next steps)\b",
            m,
        )
    )
    if minimal and suggest:
        return None
    if minimal:
        return "minimal"
    if suggest:
        return "suggest"
    return None


def _embedded_clarify_first(m: str) -> str | None:
    """``on`` vs ``off`` from prose (not short *Clarify first* / *No clarifying questions* controls)."""
    if len(m) < 48:
        return None
    off = bool(
        re.search(
            r"\b(no clarifying questions (?:first|please)?|don'?t ask clarifying questions|"
            r"skip clarifying questions|answer without asking questions first|"
            r"don'?t (?:pause to\s+)?ask questions first|"
            r"give (?:your\s+)?best answer without asking|"
            r"don'?t interrogate me first|skip the q&a preamble|"
            r"answer immediately (?:even\s+)?if (?:the\s+)?(?:spec|specs) (?:is|are) incomplete)\b",
            m,
        )
    )
    on = bool(
        re.search(
            r"\b(ask clarifying questions before (?:you\s+)?answer|"
            r"clarify (?:any\s+)?ambiguities before|"
            r"if anything is unclear ask me first|"
            r"before you (?:answer|dive in) ask (?:me\s+)?(?:what\s+you\s+need|any questions)|"
            r"pause and ask (?:me\s+)?(?:short\s+)?questions if|"
            r"confirm my (?:constraints|requirements) before|"
            r"ask what you need (?:to know )?first|"
            r"i may have left details out[-—]\s*ask|"
            r"feel free to ask (?:me\s+)?(?:1[-–]3\s+)?clarifying questions first)\b",
            m,
        )
    )
    if on and off:
        return None
    if off:
        return "off"
    if on:
        return "on"
    return None


def _embedded_section_headings(m: str) -> str | None:
    """``prefer`` vs ``avoid`` for markdown ##/### structure (not short *Use section headings* controls)."""
    if len(m) < 48:
        return None
    avoid = bool(
        re.search(
            r"\b(flat answer|no section headings|avoid markdown headings|"
            r"no (?:##|hash)\s*style headings|without (?:##|markdown) title lines|"
            r"continuous prose (?:only|without headings)|"
            r"don'?t use (?:leading\s+)?#+\s*headings?|"
            r"skip (?:the\s+)?##\s*headers?)\b",
            m,
        )
    )
    prefer = bool(
        re.search(
            r"\b(use (?:markdown\s+)?(?:section\s+)?headings|organize with (?:markdown\s+)?headings|"
            r"structure (?:the\s+)?answer with (?:clear\s+)?headings|"
            r"break (?:it|this|the answer) into (?:titled\s+)?sections|"
            r"(?:clear\s+)?markdown headings for each|"
            r"##\s*(?:or|/)\s*###\s*headings|"
            r"top[- ]level headings for each (?:major\s+)?(?:topic|section))\b",
            m,
        )
    )
    if avoid and prefer:
        return None
    if avoid:
        return "avoid"
    if prefer:
        return "prefer"
    return None


def _embedded_analogy_use(m: str) -> str | None:
    """``prefer`` vs ``avoid`` for analogies/metaphors (not short *Use analogies* / *No analogies* controls)."""
    if len(m) < 48:
        return None
    avoid = bool(
        re.search(
            r"\b(no analogies|skip metaphors|avoid metaphors|skip the analogies|"
            r"without analogies or metaphors|literal (?:explanations?|wording) only|"
            r"don'?t use analogies|don'?t use metaphors|no cute comparisons|"
            r"stick to literal (?:technical\s+)?(?:language|description|wording)|"
            r"keep (?:it\s+)?strictly literal)\b",
            m,
        )
    )
    prefer = bool(
        re.search(
            r"\b(use (?:a\s+)?(?:helpful\s+|tight\s+)?analogy|"
            r"explain (?:it\s+)?with (?:a\s+)?(?:simple\s+)?(?:real[- ]world\s+)?analogy|"
            r"include (?:a\s+)?(?:brief\s+)?(?:metaphor|analogy)|"
            r"liken (?:this|it) to (?:something|a\s+familiar)|"
            r"compare (?:this|it)\s+to (?:a\s+)?(?:real[- ]world|everyday)|"
            r"map (?:this|it) to an everyday example|"
            r"metaphor that helps|ground (?:the\s+)?idea in (?:an?\s+)?analogy)\b",
            m,
        )
    )
    if avoid and prefer:
        return None
    if avoid:
        return "avoid"
    if prefer:
        return "prefer"
    return None


def _embedded_term_emphasis(m: str) -> str | None:
    """``highlight`` vs ``minimal`` inline bold (not short *Bold key terms* controls)."""
    if len(m) < 48:
        return None
    minimal = bool(
        re.search(
            r"\b(minimal bold|don'?t overuse bold|avoid excessive bold|"
            r"sparse bold|keep bold (?:to a )?minimum|"
            r"no bold except (?:for )?code|plain text without bold|"
            r"don'?t bold every|avoid bolding (?:whole|entire) sentences)\b",
            m,
        )
    )
    highlight = bool(
        re.search(
            r"\b(bold (?:the\s+)?(?:key\s+)?terms|highlight (?:the\s+)?(?:key\s+)?(?:terms|phrases)|"
            r"emphasize (?:the\s+)?(?:key\s+)?(?:terms|keywords)|"
            r"make (?:the\s+)?key terms stand out|"
            r"use bold (?:on|for) (?:a\s+)?(?:few\s+)?(?:key\s+)?(?:terms|phrases|keywords)|"
            r"so (?:execs|leadership|managers) can scan.{0,50}bold)\b",
            m,
        )
    )
    if minimal and highlight:
        return None
    if minimal:
        return "minimal"
    if highlight:
        return "highlight"
    return None


def _embedded_acronym_style(m: str) -> str | None:
    """``spell_out`` vs ``terse`` acronym handling (not short *Spell out acronyms* controls)."""
    if len(m) < 48:
        return None
    terse = bool(
        re.search(
            r"\b(assume (?:i|we) know acronyms|don'?t expand acronyms|"
            r"keep acronyms as[- ]is|skip acronym expansion|"
            r"no need to spell out acronyms|acronym[- ]literate (?:audience|readers?)|"
            r"terse acronyms only)\b",
            m,
        )
    )
    spell = bool(
        re.search(
            r"\b(spell out acronyms|expand acronyms (?:on|at) first use|"
            r"define acronyms when you (?:use|introduce)|"
            r"write out acronyms (?:on|at) first mention|"
            r"full form (?:once|on first mention).{0,40}(?:acronym|initialism)|"
            r"expand (?:each\s+)?(?:api|sla|sso|gdpr|hipaa|pci)[- ]style (?:term|acronym)|"
            r"for (?:auditors|compliance|non-technical).{0,50}spell out)\b",
            m,
        )
    )
    if spell and terse:
        return None
    if terse:
        return "terse"
    if spell:
        return "spell_out"
    return None


def _embedded_risk_posture(m: str) -> str | None:
    """``conservative`` vs ``pragmatic`` recommendation tone (not short *Be risk averse* controls)."""
    if len(m) < 48:
        return None
    pragmatic = bool(
        re.search(
            r"\b(optimize for speed|good enough is fine|be pragmatic about|"
            r"avoid over[- ]engineering|ship (?:it )?fast|move fast (?:and|&)|"
            r"time[- ]efficient (?:fix|approach|recommendation)|"
            r"practical trade[- ]offs over perfection|"
            r"don'?t gold[- ]plate|bias toward shipping)\b",
            m,
        )
    )
    conservative = bool(
        re.search(
            r"\b(err on the side of safety|be risk[- ]averse|"
            r"risk[- ]averse (?:recommendation|approach)|"
            r"choose the (?:safest|lower[- ]risk) option|"
            r"minimize (?:downside|blast radius)|"
            r"prefer (?:safer|low[- ]risk) (?:options?|paths?)|"
            r"conservative (?:recommendation|rollout|approach)|"
            r"safety[- ]first (?:for|on) (?:this|the) (?:rollout|migration|change))\b",
            m,
        )
    )
    if conservative and pragmatic:
        return None
    if conservative:
        return "conservative"
    if pragmatic:
        return "pragmatic"
    return None


def _embedded_quote_style(m: str) -> str | None:
    """``quote`` vs ``paraphrase`` when relying on supplied FAQ excerpts (not short *Quote the FAQ* controls)."""
    if len(m) < 48:
        return None
    src = r"(?:faq|excerpt|policy|knowledge base|kb article|documentation|provided (?:text|docs))"
    paraphrase = bool(
        re.search(
            rf"\b(paraphrase (?:the )?{src}|paraphrase only|"
            rf"(?:don'?t|do not) quote (?:the )?{src}|no direct quotes? from (?:the )?{src}|"
            rf"summarize (?:the )?{src} in your own words|"
            rf"avoid quoting (?:the )?{src}|in your own words.{0,40}(?:faq|excerpt))\b",
            m,
        )
    )
    quote = bool(
        re.search(
            rf"\b((?<!not )(?<!don't )quote (?:the )?{src}|direct quotes? from (?:the )?{src}|"
            rf"cite with (?:direct )?quotes? when (?:you )?(?:use|reference) (?:the )?{src}|"
            rf"verbatim (?:quotes?|passages?) from (?:the )?{src}|"
            rf"include (?:a )?(?:short )?verbatim quote.{0,50}(?:faq|excerpt)|"
            rf"when you rely on (?:the )?{src}.{0,50}quote)\b",
            m,
        )
    )
    if quote and paraphrase:
        return None
    if quote:
        return "quote"
    if paraphrase:
        return "paraphrase"
    return None


def _embedded_emoji_style(m: str) -> str | None:
    """``include`` vs ``avoid`` emoji in replies (not short *Use emoji* / *No emoji* controls)."""
    if len(m) < 48:
        return None
    avoid = bool(
        re.search(
            r"\b(no emojis? in (?:your|the) reply|avoid emoji|emoji[- ]free (?:reply|tone)|"
            r"don'?t use emoji|do not use emoji|keep (?:it\s+)?(?:strictly\s+)?professional.{0,40}no emoji|"
            r"without emoji|skip (?:the\s+)?emoji|no cute emoji|"
            r"plain text only.{0,30}no emoji)\b",
            m,
        )
    )
    include = bool(
        re.search(
            r"\b(use (?:a few\s+)?(?:tasteful\s+)?emoji|include emoji|emoji (?:are|is) ok|"
            r"emoji welcome|feel free to use emoji|sprinkle (?:in\s+)?emoji|"
            r"a few emoji (?:are|is) fine|light emoji (?:are|is) ok|"
            r"you may use emoji|add (?:a few\s+)?emoji (?:if|when) (?:helpful|appropriate))\b",
            m,
        )
    )
    if avoid and include:
        return None
    if avoid:
        return "avoid"
    if include:
        return "include"
    return None


def _embedded_counterpoint_tone(m: str) -> str | None:
    """``challenge`` vs ``supportive`` pushback on plans (not short *Challenge my assumptions* controls)."""
    if len(m) < 52:
        return None
    ctx = (
        r"\b(plan|plans|design|approach|idea|ideas|architecture|proposal|strategy|"
        r"implementation|rollout|pitch|deck|draft|thesis|launch|release|migration|schema|"
        r"deployment|code|system)\b"
    )
    gentle = bool(
        re.search(r"\b(don'?t challenge|be gentle|go easy on me|no criticism|don'?t be harsh)\b", m)
    )
    challenge = bool(
        not gentle
        and re.search(
            r"\b(red team|red-team|stress[- ]?test|pick apart|tear down|what am i missing|sanity check|"
            r"challenge my|poke holes|find (?:weaknesses|gaps|flaws)|critique (?:my|this|our)|"
            r"devil'?s advocate)\b",
            m,
        )
        and re.search(ctx, m)
    )
    supportive = bool(
        re.search(
            r"\b(be supportive (?:of|about|with)|assume good intent|encourage my (?:idea|plan|proposal)|"
            r"constructive and supportive|help me build on (?:this|my) (?:idea|plan)|"
            r"coach me through (?:this|my) (?:idea|plan|pitch)|"
            r"gentle (?:feedback|pushback) on (?:my|this|our)|"
            r"avoid harsh criticism|frame improvements as next steps|"
            r"lean supportive and (?:specific|actionable))\b",
            m,
        )
        and re.search(ctx, m)
    )
    if challenge and supportive:
        return None
    if challenge:
        return "challenge"
    if supportive:
        return "supportive"
    return None


def _embedded_math_detail(m: str) -> str | None:
    """``show_work`` vs ``final_only`` for math-like answers (not short *Show your work* controls)."""
    if len(m) < 44:
        return None
    show = bool(
        re.search(
            r"\b(show your work|show (?:all )?(?:the )?steps|with (?:a )?derivation|prove (that|it)|rigorously|"
            r"walk through (?:the )?derivation|show intermediate steps|step[- ]by[- ]step derivation|"
            r"derive (?:it|the result) (?:step by step|explicitly))\b",
            m,
        )
    )
    final = bool(
        re.search(
            r"\b(final answer only|no derivation|skip (?:the )?steps|just (?:give )?(?:me )?the (?:final )?result|"
            r"don'?t show your work|do not show your work|answer without (?:showing )?steps|"
            r"no intermediate steps|closed[- ]form (?:answer|result) only|"
            r"(?:numerical |numeric )?answer only.{0,30}no steps)\b",
            m,
        )
    )
    if show and final:
        return None
    if show:
        return "show_work"
    if final and re.search(
        r"\b(math|equation|integral|derivative|probability|calculate|calculus|algebra|"
        r"proof|formula|theorem|matrix|solve|statistics|bayes|variance|expected value)\b",
        m,
    ):
        return "final_only"
    return None


def _embedded_faq_grounding(m: str) -> str | None:
    """``strict`` vs ``relaxed`` FAQ/RAG grounding (not short *Strict FAQ* / *Relaxed FAQ* controls)."""
    if len(m) < 48:
        return None
    src = r"(?:faq|excerpt|policy|knowledge base|kb article|documentation|provided excerpts|retrieved passages)"
    strict = bool(
        re.search(
            rf"\b(stick to (?:the )?{src}|only use (?:the )?{src}|"
            rf"only trust (?:the )?{src}|faq[- ]only (?:for|on) (?:this|the)|"
            rf"strict faq (?:grounding|only)|if (?:it(?:'s| is) )?not in (?:the )?{src}.{0,40}(?:say|admit)|"
            rf"don'?t go beyond (?:the )?{src}|must be supported by (?:the )?{src}|"
            rf"policy claims must come from (?:the )?{src}|"
            rf"grounded strictly in (?:the )?{src})\b",
            m,
        )
    )
    relaxed = bool(
        re.search(
            rf"\b(faq plus general knowledge|mix (?:the )?{src} with general knowledge|"
            rf"relaxed faq (?:grounding|mode)|"
            rf"general knowledge (?:is )?ok.{0,50}(?:faq|excerpt|policy|documentation)|"
            rf"(?:faq|excerpt|policy|documentation).{0,50}general knowledge (?:is )?ok|"
            rf"supplement (?:the )?{src} with (?:brief )?general[- ]knowledge|"
            rf"beyond (?:the )?{src} you may add (?:brief )?general context)\b",
            m,
        )
    )
    if strict and relaxed:
        return None
    if strict:
        return "strict"
    if relaxed:
        return "relaxed"
    return None


def _embedded_code_block_style(m: str) -> str | None:
    """``fenced`` vs ``inline`` code layout (not short *Use code fences* / *Inline code only* controls)."""
    if len(m) < 48:
        return None
    code_ctx = (
        r"\b(code|snippet|command|script|bash|shell|python|curl|kubectl|docker|sql|"
        r"regex|yaml|terraform|powershell|config|api call|terminal)\b"
    )
    fenced = bool(
        re.search(
            r"\b(use code fences|fenced code blocks?|markdown code fences?|"
            r"triple[- ]backtick fences?|put (?:the )?(?:code|commands?|script) in (?:a )?fenced block|"
            r"use markdown fenced code blocks?|wrap (?:the )?(?:code|snippet) in (?:triple )?backticks)\b",
            m,
        )
    )
    inline = bool(
        re.search(
            r"\b(inline code only|no triple backticks?|no fenced code blocks?|"
            r"avoid code fences|single backticks? only|don'?t use fenced blocks?|"
            r"keep (?:code|snippets?) inline|inline backticks? only)\b",
            m,
        )
    )
    if not fenced and not inline:
        return None
    if not re.search(code_ctx, m):
        return None
    if fenced and inline:
        return None
    if fenced:
        return "fenced"
    return "inline"


def _embedded_reply_format(m: str) -> str | None:
    """``bullets`` vs ``prose`` list layout (not short *Use bullet points* / *No bullets* controls)."""
    if len(m) < 48:
        return None
    prose = bool(
        re.search(
            r"\b(no bullets?|plain paragraphs?|prose only|stop using lists|"
            r"continuous prose only|avoid bullet lists?|write in paragraphs|"
            r"paragraph form only|don'?t use bullet points?|"
            r"keep (?:it\s+)?in (?:flowing )?prose|not as a bulleted list)\b",
            m,
        )
    )
    bullets = bool(
        re.search(
            r"\b(bullet points?|bulleted list|use bullets|format as bullets|"
            r"list (?:the\s+)?key points in bullets|markdown bullets?|"
            r"give me a bulleted list|bullet(?:ed)? format)\b",
            m,
        )
    )
    if prose and bullets:
        return None
    if prose:
        return "prose"
    if bullets:
        return "bullets"
    return None


def _embedded_comparison_frame(m: str) -> str | None:
    """``pros_cons`` vs ``narrative`` comparison layout (not short *Use pros and cons* controls)."""
    if len(m) < 48:
        return None
    if not re.search(r"\b(compare|comparing|comparison|contrasted?|contrast|trade-?offs?)\b", m):
        return None
    narrative = bool(
        re.search(
            r"\b(no pros|without pros|avoid pros|no pros\/cons|no pros and cons sections?)\b",
            m,
        )
        or re.search(
            r"\b(flowing prose|continuous prose|narrative comparison|prose comparison only|"
            r"compare in flowing prose)\b",
            m,
        )
    )
    pros = bool(
        re.search(
            r"\b(trade-?offs?|(?<!no )pros and cons|advantages and disadvantages)\b",
            m,
        )
        or re.search(r"\bdifference between\b.+\band\b", m)
        or re.search(r"\b(compare|comparing|comparison|contrasted?|contrast)\b.+\b(vs\.?|versus)\b", m)
        or (
            re.search(r"\b(compare|comparing|comparison)\b", m)
            and re.search(r"\b(and|with)\b", m)
            and len(m) >= 72
            and re.search(
                r"\b(versus|vs\.?|option|approach|tool|stack|framework|language|model|database|db|cloud)\b",
                m,
            )
        )
    )
    if narrative and pros:
        return None
    if narrative:
        return "narrative"
    if pros:
        return "pros_cons"
    return None


def _embedded_table_style(m: str) -> str | None:
    """``prefer`` vs ``avoid`` markdown tables (not short *Use tables* / *No tables* controls)."""
    if len(m) < 48:
        return None
    avoid = bool(
        re.search(
            r"\b(no tables?|without a table|avoid tables?|no markdown tables?|"
            r"don'?t use tables?|skip the table|table[- ]free (?:summary|answer)|"
            r"not in a table|avoid tabular format)\b",
            m,
        )
    )
    prefer = bool(
        re.search(
            r"\b(in a table|as a table|markdown table|(?<!avoid )tabular format|two-?column|rows and columns|"
            r"use a (?:markdown )?table|format as a table|put (?:it|this) in a table|"
            r"present (?:it|the comparison) in a table)\b",
            m,
        )
    )
    if avoid and prefer:
        return None
    if avoid:
        return "avoid"
    if prefer:
        return "prefer"
    return None


def _embedded_step_style(m: str) -> str | None:
    """``numbered`` vs ``continuous`` procedure layout (not short *Step by step* controls)."""
    if len(m) < 48:
        return None
    continuous = bool(
        re.search(
            r"\b(no numbered steps|don'?t number steps|skip step numbers|"
            r"prose without steps|avoid numbered step lists?|"
            r"continuous prose (?:only|instead)|not as numbered steps|"
            r"connected paragraphs?(?:\s+only)?|explain as (?:flowing )?prose)\b",
            m,
        )
    )
    numbered = bool(
        re.search(r"\b(step by step|step-by-step)\b", m)
        or re.search(r"\b(walk me through|show me how)\b", m)
        or re.search(r"\b(?<!no )(?:use )?numbered steps\b|break it into steps\b", m)
        or (
            re.search(r"\b(how do i|how can i|how should i|how to)\b", m)
            and re.search(
                r"\b(install|set up|setup|configure|enable|deploy|migrate|upgrade|fix|debug|troubleshoot)\b",
                m,
            )
        )
    )
    if continuous and numbered:
        return None
    if continuous:
        return "continuous"
    if numbered:
        return "numbered"
    return None


def _reply_lang_phrase(m: str) -> str | None:
    """Return display name (e.g. 'French') if the user asked for a reply in a known language."""
    for mo in re.finditer(
        r"\b(respond|answer|reply|write|explain)\s+(?:in|using)\s+([a-z]{3,20})\b(?:\s*[.?!]|$|,|\s+please|\s+thanks)?",
        m,
    ):
        tok = mo.group(2)
        if tok in _REPLY_LANG_TOKENS:
            return _REPLY_LANG_TOKENS[tok]
    mo = re.search(
        r"\b(translate|translating)\s+(?:this|that|it|your answer|the above|my text)\s+(?:to|into)\s+([a-z]{3,20})\b",
        m,
    )
    if mo and mo.group(2) in _REPLY_LANG_TOKENS:
        return _REPLY_LANG_TOKENS[mo.group(2)]
    mo = re.search(r"\b(entire reply|whole answer|full answer)\s+(?:in|using)\s+([a-z]{3,20})\b", m)
    if mo and mo.group(2) in _REPLY_LANG_TOKENS:
        return _REPLY_LANG_TOKENS[mo.group(2)]
    # Trailing clause: "... in french" / "... in spanish, please"
    tail = m[-100:] if len(m) > 100 else m
    mo = re.search(r"\b(in|into)\s+([a-z]{3,20})\s*(?:[,.]|please|thanks)?\s*$", tail)
    if mo and mo.group(2) in _REPLY_LANG_TOKENS:
        return _REPLY_LANG_TOKENS[mo.group(2)]
    return None


def analyze_embedded_prompt_signals(message: str) -> tuple[dict[str, str], list[str], list[str]]:
    """Infer reply-style preferences from wording inside longer questions (one-shot overlays).

    Used only when ``parse_control_action`` does not treat the line as a dedicated control
    command. Conservative patterns avoid hijacking short chit-chat.

    Returns:
        (field_overrides, extra_system_paragraphs, trace_tags) — overrides use the same keys/values as
        ``ub_session`` reply-style fields; extra paragraphs are appended as separate system sections;
        ``trace_tags`` are short tokens for the brain-trace ``prompt_signals:`` line (e.g. ``language``,
        ``code_only``, ``code_explained``, ``len_cap=80w``, ``guided``, ``ephemeral``, ``a11y``,
        ``cite_sources``, ``cite_minimal``, ``ranked_options``, ``checklist``, ``no_checklist``,
        ``pseudocode``, ``runnable_code``, ``options_n=N``, ``diagram``, ``no_diagram``,
        ``risks_first``, ``benefits_first``, ``revise_draft``, ``revise_diff``, ``email_format``, ``meeting_agenda``, ``topic_guard``,
        ``topic_must``, ``glossary``, ``spelling_uk``, ``spelling_us``, ``risks_mitigations``,
        ``timeline_chron``, ``timeline_reverse``, ``voice_second``, ``voice_third``, ``faq_qa``,
        ``summary_last``, ``decision_matrix``, ``build_vs_buy``, ``one_pager``, ``action_plan``, ``raci``, ``stakeholder_map``, ``swot``, ``pestle``, ``cost_benefit``, ``open_questions``, ``scenario_cases``,
        ``postmortem``, ``sprint_retro``, ``five_whys``, ``fishbone``,
        ``recommendation_first``,
        ``go_no_go``,
        ``frame_star``, ``frame_prep``, ``frame_irac``). Session-style overrides
        (e.g. ``confidence_tone=transparent``) appear as ``key=value`` tokens in the same line.
    """
    m = _norm(message)
    overrides: dict[str, str] = {}
    extras: list[str] = []
    trace_tags: list[str] = []

    if len(m) >= 24:
        lang = _reply_lang_phrase(m)
        if lang:
            trace_tags.append("language")
            extras.append(
                f"The user asked (via natural wording) for the assistant reply in **{lang}**. "
                f"Write the **entire** answer in {lang}, including headings and lists, unless a quoted passage must stay "
                "verbatim in another language."
            )

    co = _code_only_instruction(m)
    cex = _embedded_code_commentary(m)
    if co and cex:
        pass
    elif co:
        trace_tags.append("code_only")
        extras.append(co)
    elif cex:
        extras.append(cex[0])
        trace_tags.append(cex[1])

    pc = _embedded_pseudocode(m)
    if pc and not (co or cex):
        extras.append(pc[0])
        trace_tags.append(pc[1])

    lc = _length_cap_instruction(m)
    if lc:
        extras.append(lc[0])
        trace_tags.append(lc[1])

    gdd = _embedded_guided_discovery(m)
    if gdd:
        extras.append(gdd[0])
        trace_tags.append(gdd[1])

    ep = _ephemeral_privacy_instruction(m)
    if ep:
        extras.append(ep[0])
        trace_tags.append(ep[1])

    ax = _accessibility_sr_instruction(m)
    if ax:
        extras.append(ax[0])
        trace_tags.append(ax[1])

    sc = _embedded_source_citations(m)
    if sc:
        extras.append(sc[0])
        trace_tags.append(sc[1])

    ro = _embedded_ranked_options(m)
    if ro:
        extras.append(ro[0])
        trace_tags.append(ro[1])

    dmx = _embedded_decision_matrix(m)
    if dmx:
        extras.append(dmx[0])
        trace_tags.append(dmx[1])

    bvb = _embedded_build_vs_buy(m)
    if bvb:
        extras.append(bvb[0])
        trace_tags.append(bvb[1])

    opg = _embedded_one_pager(m)
    if opg:
        extras.append(opg[0])
        trace_tags.append(opg[1])

    apl = _embedded_action_plan(m)
    if apl:
        extras.append(apl[0])
        trace_tags.append(apl[1])

    rac = _embedded_raci_matrix(m)
    if rac:
        extras.append(rac[0])
        trace_tags.append(rac[1])

    stm = _embedded_stakeholder_map(m)
    if stm:
        extras.append(stm[0])
        trace_tags.append(stm[1])

    cl = _embedded_checklist_reply(m)
    if cl:
        extras.append(cl[0])
        trace_tags.append(cl[1])

    oc = _embedded_fixed_option_count(m)
    if oc:
        extras.append(oc[0])
        trace_tags.append(oc[1])

    dv = _embedded_diagram_visual(m)
    if dv:
        extras.append(dv[0])
        trace_tags.append(dv[1])

    rbo = _embedded_risks_benefits_order(m)
    if rbo:
        extras.append(rbo[0])
        trace_tags.append(rbo[1])

    rskm = _embedded_risks_mitigations(m)
    if rskm:
        extras.append(rskm[0])
        trace_tags.append(rskm[1])

    emf = _embedded_email_format(m)
    if emf:
        extras.append(emf[0])
        trace_tags.append(emf[1])

    mag = _embedded_meeting_agenda(m)
    if mag:
        extras.append(mag[0])
        trace_tags.append(mag[1])

    rd = _embedded_revise_draft(m)
    if rd:
        extras.append(rd[0])
        trace_tags.append(rd[1])

    rdiff = _embedded_revise_diff(m)
    if rdiff:
        extras.append(rdiff[0])
        trace_tags.append(rdiff[1])

    tg = _embedded_topic_guard(m)
    if tg:
        extras.append(tg[0])
        trace_tags.append(tg[1])

    tm = _embedded_topic_must(m)
    if tm:
        extras.append(tm[0])
        trace_tags.append(tm[1])

    af = _embedded_answer_frame(m)
    if af:
        extras.append(af[0])
        trace_tags.append(af[1])

    swot = _embedded_swot_analysis(m)
    if swot:
        extras.append(swot[0])
        trace_tags.append(swot[1])

    pest = _embedded_pestle_analysis(m)
    if pest:
        extras.append(pest[0])
        trace_tags.append(pest[1])

    cba = _embedded_cost_benefit(m)
    if cba:
        extras.append(cba[0])
        trace_tags.append(cba[1])

    oq = _embedded_open_questions(m)
    if oq:
        extras.append(oq[0])
        trace_tags.append(oq[1])

    scn = _embedded_scenario_cases(m)
    if scn:
        extras.append(scn[0])
        trace_tags.append(scn[1])

    pm = _embedded_postmortem_format(m)
    if pm:
        extras.append(pm[0])
        trace_tags.append(pm[1])

    srt = _embedded_sprint_retro(m)
    if srt:
        extras.append(srt[0])
        trace_tags.append(srt[1])

    fw = _embedded_five_whys(m)
    if fw:
        extras.append(fw[0])
        trace_tags.append(fw[1])

    fb = _embedded_fishbone(m)
    if fb:
        extras.append(fb[0])
        trace_tags.append(fb[1])

    gls = _embedded_glossary_section(m)
    if gls:
        extras.append(gls[0])
        trace_tags.append(gls[1])

    spl = _embedded_spelling_locale(m)
    if spl:
        extras.append(spl[0])
        trace_tags.append(spl[1])

    tlo = _embedded_timeline_order(m)
    if tlo:
        extras.append(tlo[0])
        trace_tags.append(tlo[1])

    wvc = _embedded_writing_voice(m)
    if wvc:
        extras.append(wvc[0])
        trace_tags.append(wvc[1])

    fqa = _embedded_faq_qa_format(m)
    if fqa:
        extras.append(fqa[0])
        trace_tags.append(fqa[1])

    sml = _embedded_summary_last(m)
    if sml:
        extras.append(sml[0])
        trace_tags.append(sml[1])

    if _embedded_simple_audience(m):
        overrides["audience"] = "simple"
    elif _embedded_technical_audience(m):
        overrides["audience"] = "technical"

    ert = _embedded_register_tone(m)
    if ert:
        overrides["register_tone"] = ert

    oft = _embedded_output_format(m)
    if oft:
        overrides["output_format"] = oft

    vrb = _embedded_verbosity(m)
    if vrb:
        overrides["verbosity"] = vrb

    spc = _embedded_speculation(m)
    if spc:
        overrides["speculation"] = spc

    ald = _embedded_answer_lead(m)
    if ald:
        overrides["answer_lead"] = ald

    rcf = _embedded_recommendation_first(m)
    if rcf:
        extras.append(rcf[0])
        trace_tags.append(rcf[1])

    gng = _embedded_go_no_go(m)
    if gng:
        extras.append(gng[0])
        trace_tags.append(gng[1])

    act = _embedded_actionability(m)
    if act:
        overrides["actionability"] = act

    cft = _embedded_confidence_tone(m)
    if cft:
        overrides["confidence_tone"] = cft

    exd = _embedded_example_density(m)
    if exd:
        overrides["example_density"] = exd

    if len(m) < 48:
        return overrides, extras, trace_tags

    cmf = _embedded_comparison_frame(m)
    if cmf:
        overrides["comparison_frame"] = cmf

    stl = _embedded_step_style(m)
    if stl:
        overrides["step_style"] = stl

    tbl = _embedded_table_style(m)
    if tbl:
        overrides["table_style"] = tbl

    rpf = _embedded_reply_format(m)
    if rpf:
        overrides["reply_format"] = rpf

    mth = _embedded_math_detail(m)
    if mth:
        overrides["math_detail"] = mth

    cpt = _embedded_counterpoint_tone(m)
    if cpt:
        overrides["counterpoint_tone"] = cpt

    eord = _embedded_exposition_order(m)
    if eord:
        overrides["exposition_order"] = eord

    fuc = _embedded_followup_close(m)
    if fuc:
        overrides["followup_close"] = fuc

    clf = _embedded_clarify_first(m)
    if clf:
        overrides["clarify_first"] = clf

    shd = _embedded_section_headings(m)
    if shd:
        overrides["section_headings"] = shd

    anu = _embedded_analogy_use(m)
    if anu:
        overrides["analogy_use"] = anu

    tem = _embedded_term_emphasis(m)
    if tem:
        overrides["term_emphasis"] = tem

    acs = _embedded_acronym_style(m)
    if acs:
        overrides["acronym_style"] = acs

    rsk = _embedded_risk_posture(m)
    if rsk:
        overrides["risk_posture"] = rsk

    qst = _embedded_quote_style(m)
    if qst:
        overrides["quote_style"] = qst

    emj = _embedded_emoji_style(m)
    if emj:
        overrides["emoji_style"] = emj

    fgr = _embedded_faq_grounding(m)
    if fgr:
        overrides["faq_grounding"] = fgr

    cbs = _embedded_code_block_style(m)
    if cbs:
        overrides["code_block_style"] = cbs

    return overrides, extras, trace_tags

