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

    # Session toggles (chat UX)
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
        ``cite_sources``, ``cite_minimal``, ``ranked_options``, ``checklist``, ``no_checklist``). Session-style overrides
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

    cl = _embedded_checklist_reply(m)
    if cl:
        extras.append(cl[0])
        trace_tags.append(cl[1])

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

