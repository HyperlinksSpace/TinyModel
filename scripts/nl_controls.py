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
        r"\b(just the code|code only|only code|no prose,?\s*just code|no explanation,?\s*just (?:the )?code|"
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


def _guided_discovery_instruction(m: str) -> tuple[str, str] | None:
    """User wants hints, nudges, or questions instead of a fully worked answer on the first reply."""
    if len(m) < 36:
        return None
    if not re.search(
        r"\b(don'?t (give|spell|hand) (me )?(the )?full (answer|solution)|don'?t spoil the solution|"
        r"hints? only|only hints|guide me with (hints|questions)|nudge me (in the right direction|toward)|"
        r"i want to (figure|work) it out myself|socratic(\s+method)?|"
        r"lead me to (the )?answer|questions first instead of answering|"
        r"without (giving|spelling) (out )?(the )?(whole )?solution)\b",
        m,
    ):
        return None
    # Require a problem-seeking cue so casual chat ("no spoilers for the movie") does not flip modes.
    if not re.search(
        r"\b(why|how|explain|prove|derive|solve|puzzle|homework|problem|exercise|bug|code|implement|"
        r"design|compare|understand|learn|teach|practice|algorithm|proof|debug|refactor)\b",
        m,
    ):
        return None
    instr = (
        "The user asked for **guided discovery** (Socratic / hint-first): prefer short **questions**, "
        "**nudges**, and **partial hints** over a complete solution in this turn. "
        "If one concrete step is essential, show **at most one** move, then check whether they want to continue. "
        "Offer the full worked answer if they say they are stuck or ask you to finish."
    )
    return instr, "guided"


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


def _embedded_json_output(m: str) -> bool:
    """True if a longer prompt asks for JSON-shaped output (not the short *Answer in JSON* control line)."""
    if len(m) < 40:
        return False
    if re.search(
        r"\b(no json|not json|avoid json|skip json|plain text only|no structured output|"
        r"don'?t use json|without json)\b",
        m,
    ):
        return False
    return bool(
        re.search(
            r"\b(valid json|return json|reply in json|answer in json|json output|structured json|"
            r"json object|json array|as json\b|as a json|machine[- ]readable json|emit json|"
            r"serialize (?:to|as) json|output as json|respond with json)\b",
            m,
        )
    )


def _embedded_speculation_strict(m: str) -> bool:
    """True if a longer prompt demands low-speculation / anti-guessing (not the short *No speculation* control)."""
    if len(m) < 44:
        return False
    if re.search(
        r"\b(brainstorm freely|speculate freely|wild ideas|creative speculation|"
        r"go ahead and guess|reasonable guesses welcome|speculate a bit)\b",
        m,
    ):
        return False
    return bool(
        re.search(
            r"\b(don'?t guess|no guessing|avoid guessing|only high confidence|stick to (?:the\s+)?facts|"
            r"avoid halluc|no hallucinations|don'?t hallucinate|if you don'?t know say|"
            r"if unsure say|say when you(?:'re|\s+are)\s+unsure|no speculation|avoid speculation|"
            r"don'?t speculate|fact[- ]checked|grounded only|evidence[- ]based only|"
            r"only if (?:you(?:'re|\s+are)\s+)?(?:certain|sure)|do not invent (?:facts|numbers))\b",
            m,
        )
    )


def _embedded_answer_lead_tldr(m: str) -> bool:
    """True if a longer prompt wants an upfront summary / BLUF (not the short *TLDR first* control line)."""
    if len(m) < 44:
        return False
    if re.search(
        r"\b(no tldr|skip (?:the )?summary|answer directly|without a (?:summary|tldr)|"
        r"no executive summary|don'?t (?:add|give) a tldr)\b",
        m,
    ):
        return False
    return bool(
        re.search(
            r"\b(tl;?dr first|tldr first|lead with (?:a\s+)?(?:one[- ]line\s+)?summary|summary first|"
            r"executive summary first|bottom line up front|bluf|"
            r"start with (?:a\s+)?(?:short\s+)?summary|headline first|"
            r"give me the (?:key\s+)?takeaway first)\b",
            m,
        )
    )


def _embedded_actionability_commands(m: str) -> bool:
    """True if a longer prompt asks for runnable shell/tooling snippets (not the short *Make it actionable* control)."""
    if len(m) < 44:
        return False
    if re.search(
        r"\b(no commands|conceptual only|high level only|without commands|no shell commands|"
        r"no code|no snippets|theory only)\b",
        m,
    ):
        return False
    return bool(
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


def _embedded_confidence_transparent(m: str) -> bool:
    """True if a longer prompt asks for explicit assumptions, limitations, or caveats (not the short control lines)."""
    if len(m) < 44:
        return False
    if re.search(
        r"\b(no assumptions? section|skip (?:the\s+)?assumptions?|don'?t list assumptions|"
        r"without caveats|no caveats|omit limitations)\b",
        m,
    ):
        return False
    if re.search(
        r"\b(no hedging|don'?t hedge|be decisive|firm answers?|minimal hedging|"
        r"sound\s+confident|avoid disclaimers)\b",
        m,
    ):
        return False
    return bool(
        re.search(
            r"\b(state|list|spell out|call out|identify|enumerate|label)\s+"
            r"(?:your\s+|the\s+|our\s+|key\s+|main\s+)?(?:key\s+|main\s+)?assumptions?\b",
            m,
        )
        or re.search(
            r"\b(assumptions?\s+and\s+limitations?|limitations?\s+and\s+caveats?|"
            r"limitations?\s+section|caveats?\s+(?:first|upfront|at\s+the\s+top)|"
            r"upfront\s+caveats?|scope\s+and\s+assumptions?|boundary\s+conditions?|"
            r"what\s+(?:we\s+)?(?:are\s+)?assuming\b|"
            r"explicit(?:ly)?\s+about\s+(?:limitations?|uncertainty|what\s+we\s+don'?t\s+know)|"
            r"where\s+this\s+(?:breaks?\s+down|stops?\s+working|doesn'?t\s+apply))\b",
            m,
        )
        or re.search(
            r"\b(flag|surface|highlight)\s+(?:key\s+)?(?:uncertainties|unknowns|gaps|risk\s+factors)\b",
            m,
        )
    )


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
        ``code_only``, ``len_cap=80w``, ``guided``, ``ephemeral``, ``a11y``). Session-style overrides
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
    if co:
        trace_tags.append("code_only")
        extras.append(co)

    lc = _length_cap_instruction(m)
    if lc:
        extras.append(lc[0])
        trace_tags.append(lc[1])

    gd = _guided_discovery_instruction(m)
    if gd:
        extras.append(gd[0])
        trace_tags.append(gd[1])

    ep = _ephemeral_privacy_instruction(m)
    if ep:
        extras.append(ep[0])
        trace_tags.append(ep[1])

    ax = _accessibility_sr_instruction(m)
    if ax:
        extras.append(ax[0])
        trace_tags.append(ax[1])

    if _embedded_simple_audience(m):
        overrides["audience"] = "simple"

    ert = _embedded_register_tone(m)
    if ert:
        overrides["register_tone"] = ert

    if _embedded_json_output(m):
        overrides["output_format"] = "json"

    if _embedded_speculation_strict(m):
        overrides["speculation"] = "strict"

    if _embedded_answer_lead_tldr(m):
        overrides["answer_lead"] = "tldr_first"

    if _embedded_actionability_commands(m):
        overrides["actionability"] = "commands"

    if _embedded_confidence_transparent(m):
        overrides["confidence_tone"] = "transparent"

    exd = _embedded_example_density(m)
    if exd:
        overrides["example_density"] = exd

    if len(m) < 48:
        return overrides, extras, trace_tags

    # Comparison layout (prefer narrative if user explicitly rejects rigid pros/cons).
    if re.search(r"\b(no pros|without pros|avoid pros|no pros\/cons)\b", m) and re.search(
        r"\b(compare|comparison|contrast|trade-?offs?)\b",
        m,
    ):
        overrides["comparison_frame"] = "narrative"
    elif re.search(r"\b(flowing prose|continuous prose|narrative comparison)\b", m) and re.search(
        r"\b(compare|comparison|contrast)\b",
        m,
    ):
        overrides["comparison_frame"] = "narrative"
    elif (
        re.search(r"\b(trade-?offs?|pros and cons|advantages and disadvantages)\b", m)
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
    ):
        overrides["comparison_frame"] = "pros_cons"

    # Procedure-style questions → numbered steps for this answer.
    if re.search(r"\b(step by step|step-by-step)\b", m) or re.search(
        r"\b(walk me through|show me how)\b",
        m,
    ):
        overrides["step_style"] = "numbered"
    elif re.search(r"\b(how do i|how can i|how should i|how to)\b", m) and re.search(
        r"\b(install|set up|setup|configure|enable|deploy|migrate|upgrade|fix|debug|troubleshoot)\b",
        m,
    ):
        overrides["step_style"] = "numbered"

    # Tables when the user names the shape they want.
    if re.search(r"\b(no tables?|without a table|avoid tables?)\b", m):
        overrides["table_style"] = "avoid"
    elif re.search(
        r"\b(in a table|as a table|markdown table|tabular format|two-?column|rows and columns)\b",
        m,
    ):
        overrides["table_style"] = "prefer"

    # Bullets from natural phrasing (longer prompts only).
    if re.search(r"\b(bullet points?|bulleted list|use bullets)\b", m):
        overrides["reply_format"] = "bullets"

    # Math-like rigor without a standalone "show your work" control line.
    if re.search(
        r"\b(show your work|show (all )?steps|with (a )?derivation|prove (that|it)|rigorously)\b",
        m,
    ):
        overrides["math_detail"] = "show_work"

    # Critique / red-team embedded in a longer prompt (not the short "Challenge my assumptions" control).
    if (
        len(m) >= 52
        and not re.search(r"\b(don'?t challenge|be gentle|go easy on me|no criticism|don'?t be harsh)\b", m)
        and re.search(
            r"\b(red team|red-team|stress[- ]?test|pick apart|tear down|what am i missing|sanity check|"
            r"challenge my|poke holes|find (?:weaknesses|gaps|flaws)|critique (?:my|this|our)|"
            r"devil'?s advocate)\b",
            m,
        )
        and re.search(
            r"\b(plan|plans|design|approach|idea|ideas|architecture|security|threat|attack|assumption|"
            r"proposal|strategy|implementation|rollout|schema|migration|deployment|code|system|thesis|"
            r"launch|release)\b",
            m,
        )
    ):
        overrides["counterpoint_tone"] = "challenge"

    eord = _embedded_exposition_order(m)
    if eord:
        overrides["exposition_order"] = eord

    fuc = _embedded_followup_close(m)
    if fuc:
        overrides["followup_close"] = fuc

    return overrides, extras, trace_tags

