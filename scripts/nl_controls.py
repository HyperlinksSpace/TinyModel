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
    if len(m) <= 140 and (
        re.search(r"\breset\b.*\b(reply |answer )?(style|format|length)\b", m)
        or re.search(r"\b(default|normal)\b.*\b(reply |answer )?(style|format)\b", m)
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

    return None

