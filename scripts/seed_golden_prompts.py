#!/usr/bin/env python3
"""Generate texts/golden-prompts/*.jsonl (300 rows: nl_signals, routing, e2e).

Run once after editing templates:
  python scripts/seed_golden_prompts.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_SCRIPTS = _REPO / "scripts"
_OUT = _REPO / "texts" / "golden-prompts"
_TESTS = _REPO / "tests" / "test_nl_controls.py"

if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _detected_signal_string(message: str) -> str | None:
    from nl_controls import analyze_embedded_prompt_signals, parse_control_action

    if parse_control_action(message):
        return None
    overrides, _extras, trace_tags = analyze_embedded_prompt_signals(message)
    bits = [f"{k}={v}" for k, v in sorted(overrides.items())]
    bits.extend(trace_tags)
    return "+".join(bits) if bits else None


def _harvest_nl_prompts_from_tests() -> list[tuple[str, list[str]]]:
    """Return (prompt, expect_tags[]) from TestEmbeddedPromptSignals messages."""
    src = _TESTS.read_text(encoding="utf-8")
    messages: list[str] = []
    for m in re.finditer(
        r'def test_\w+\(self\)[^:]*:\s*(?:[^\n]*\n)*?\s*msg = \(\s*\n((?:\s+"[^"]+"\s*\n)+)\s*\)',
        src,
    ):
        parts = re.findall(r'"([^"]+)"', m.group(1))
        messages.append(" ".join(parts))
    for m in re.finditer(r'def test_\w+\(self\)[^:]*:\s*msg = "([^"]+)"', src):
        messages.append(m.group(1))

    out: list[tuple[str, list[str]]] = []
    seen: set[str] = set()
    for msg in messages:
        detected = _detected_signal_string(msg)
        if not detected or msg in seen:
            continue
        seen.add(msg)
        out.append((msg, detected.split("+")))
    return out


def _nl_rows() -> list[dict]:
    """100 embedded prompt-signal cases validated against nl_controls."""
    harvested = _harvest_nl_prompts_from_tests()
    if not harvested:
        raise RuntimeError(f"No prompts harvested from {_TESTS}")

    rows: list[dict] = []
    idx = 0
    while len(rows) < 100:
        prompt, tags = harvested[idx % len(harvested)]
        idx += 1
        rows.append(
            {
                "id": f"nl_{len(rows) + 1:03d}",
                "suite": "nl_signals",
                "prompt": prompt,
                "expect_tags": tags,
            }
        )
    return rows


def _routing_rows() -> list[dict]:
    """100 intent-routing cases (evaluated with --with-router and a causal LM)."""
    cases: list[tuple[str, list[str]]] = [
        ("summarize", [
            "Summarize this article for me: The central bank held rates steady but signaled cuts later in the year.",
            "TL;DR please — long email thread about the vendor contract renewal and open legal questions.",
            "Give me a short summary of the meeting notes pasted below about Q4 hiring plan.",
            "Can you condense this policy document into a few bullet points for executives?",
        ]),
        ("reformulate", [
            "Rewrite this customer apology more professionally: Sorry we broke your export again.",
            "Rephrase the following paragraph for a formal board update without changing facts.",
            "Make this Slack message sound more diplomatic before I send it to the VP.",
            "Reformulate my rough notes into polished prose for the stakeholder newsletter.",
        ]),
        ("retrieve", [
            "Search the FAQ for how refunds work when a subscription is cancelled mid-cycle.",
            "Look up our documentation — what is the policy on data export for enterprise tenants?",
            "Find the FAQ answer about resetting two-factor authentication for locked accounts.",
            "Retrieve from FAQ: how long do support tickets typically take to get a first response?",
        ]),
        ("classify", [
            "Classify this headline: Tech stocks rally as chipmaker unveils new AI accelerator.",
            "What category is this news item? Central bank holds rates; markets mixed on inflation data.",
            "Label this text with your topic classifier: Team signs striker before weekend derby.",
            "Run classification on: Parliament debates new tax policy amid budget shortfall.",
        ]),
        ("similarity", [
            "How similar are these two sentences: Markets rose on cooling inflation ||| Stocks gained as prices slowed?",
            "Compare semantic similarity between: API latency improved overnight ||| Response times dropped after the patch.",
            "Similarity score for: We delayed the launch ||| The release date moved to next month.",
            "Are these two support macros close in meaning? Compare them for similarity.",
        ]),
        ("embedding", [
            "Embed this sentence for me: Hybrid retrieval combines keyword overlap with dense vectors.",
            "Give me the embedding vector summary for this product description paragraph.",
            "Encode this short passage into your embedding space for later search indexing.",
            "Run embed on: Customer requested GDPR export within the 30-day SLA window.",
        ]),
        ("nearest", [
            "Which option is closest to this query: outage during checkout ||| payment gateway down ||| CSS bug on homepage ||| slow search?",
            "Find the nearest candidate to 'refund delay' among: billing error, shipping slip, password reset.",
            "Nearest match for the query among these FAQ titles about exports, refunds, and SSO.",
            "Pick the top nearest option to 'disk full alert' from the candidate list I provide.",
        ]),
        ("remember", [
            "Remember that our production scope key is team-platform-prod for future turns.",
            "Save a long-term note: legal requires 90-day retention on audit logs for EU tenants.",
            "Please remember my preference to always cite FAQ sources in strict mode for this project.",
            "Store this fact in memory: our change window is Sundays 02:00-06:00 UTC.",
        ]),
        ("list_memories", [
            "Show me everything you have stored in memory for this scope.",
            "List my saved notes and long-term memories for this chat session.",
            "What memories do you have on file for me right now?",
            "Display all memory entries associated with my current scope.",
        ]),
        ("clear_session", [
            "Clear my session notes but keep long-term memory intact please.",
            "Wipe the temporary session memory from this conversation.",
            "Delete session-scoped notes only — not the long-term entries.",
            "Clear session memory for this chat now.",
        ]),
        ("help", [
            "What slash commands and features can you help me with?",
            "Show help for available tools and how to use this assistant.",
            "List the commands I can use in this chat interface.",
            "Help — what can this brain do?",
        ]),
        ("status", [
            "What models and settings are loaded right now?",
            "Show status: encoder, RAG, memory scope, and web search configuration.",
            "Give me a status report on what is enabled in this deployment.",
            "What's my current scope and which subsystems are active?",
        ]),
        ("web_search", [
            "Search the web for today's Federal Reserve interest rate decision headlines.",
            "Look up on the internet what changed in Python 3.13 release notes this week.",
            "Web search: current EU AI Act compliance deadline for general-purpose models.",
            "Find recent news on the web about Acme Corp earnings call guidance.",
        ]),
        ("grounded", [
            "Using only these facts, answer: What is the refund window? Facts: Refunds within 30 days if unused.",
            "Grounded Q&A — question: Is SSO included? Context: Enterprise tier includes SAML SSO; Starter does not.",
            "Answer from context only: When is maintenance? Context: Maintenance Sundays 02:00-06:00 UTC.",
            "Based on the provided context snippet, is export available on free tier? Context says no.",
        ]),
        ("session_note", [
            "Add a session note: today's standup agreed to freeze dependencies until release RC1.",
            "Save this as a session-scoped note only: QA found flaky test in checkout flow.",
            "Session note for this chat: stakeholder demo moved to Thursday 15:00 UTC.",
            "Put in session memory: we are testing golden prompt regression this sprint.",
        ]),
        ("chat", [
            "What are some good habits for writing clear technical documentation?",
            "Explain the difference between precision and recall in classification metrics.",
            "I'm feeling stuck prioritizing backlog items — any frameworks to choose?",
            "How would you explain APIs to a non-technical product manager in two minutes?",
            "What is the trade-off between latency and accuracy for small embedding models?",
            "When should a team prefer rules-based routing over LLM JSON routing?",
        ]),
    ]
    extras: list[tuple[str, list[str]]] = [
        ("summarize", [
            "Short summary of the quarterly reliability review attached in my message please.",
            "Condense the vendor comparison memo into executive bullets.",
        ]),
        ("reformulate", [
            "Tone down this escalation email before I send it to the customer success director.",
            "Make the incident timeline paragraph clearer for executives.",
        ]),
        ("retrieve", [
            "FAQ lookup: what are the steps to rotate API keys for enterprise tenants?",
            "Find in FAQ how billing proration works when upgrading mid-cycle.",
        ]),
        ("classify", [
            "Topic label for: Olympic sprinter breaks national record at regional meet.",
            "Classify: Startup raises Series B to expand inference chip production.",
        ]),
        ("remember", [
            "Remember for later: staging environment URL is https://staging.example.com",
            "Save note: compliance requires PII redaction in all exported chat logs.",
        ]),
        ("web_search", [
            "Search the web for recent changes to OWASP Top 10 2025 draft list.",
            "Web lookup: current status of the EU Digital Markets Act enforcement timeline.",
        ]),
        ("similarity", [
            "Similarity check: 'latency dropped' vs 'response time improved after caching layer'.",
            "How close in meaning: 'budget overrun' and 'cost exceeded forecast'?",
        ]),
        ("nearest", [
            "Nearest to 'password reset loop' among: MFA lockout, SSO misconfig, expired token.",
            "Which candidate is closest to 'slow dashboard load': DB index, CDN cache, auth timeout?",
        ]),
        ("embedding", [
            "Embedding for: Monthly invoice PDFs are available in the billing portal.",
            "Vector encode: Support SLA is 4 business hours for enterprise severity-2 tickets.",
        ]),
        ("grounded", [
            "From context only — is phone support included? Context: Enterprise includes phone; Pro is chat only.",
            "Grounded answer: refund window? Context: 30-day refund if service unused.",
        ]),
        ("help", [
            "What tools and slash commands are available in Universal Brain?",
            "How do I turn on the brain trace and strict FAQ mode?",
        ]),
        ("status", [
            "Report current encoder model id and whether Google web search is configured.",
            "Status check: is smart routing on and how many RAG chunks are loaded?",
        ]),
        ("list_memories", [
            "List all notes saved under my current scope key.",
            "Show memory entries including long-term ones for this tenant.",
        ]),
        ("session_note", [
            "Session-only note: load test capped at 500 RPS for tonight's drill.",
            "Temporary session note: disable auto-web for this debugging thread.",
        ]),
        ("clear_session", [
            "Clear session notes for this thread only, not long-term storage.",
            "Remove ephemeral session memories from this conversation.",
        ]),
        ("chat", [
            "What is retrieval-augmented generation in plain language?",
            "How do calibration histograms help when tuning routing thresholds?",
            "Explain embedding normalization for cosine similarity search.",
            "When is a small encoder enough instead of a frontier LLM?",
        ]),
    ]
    rows: list[dict] = []
    n = 0
    for intent, prompts in cases:
        for prompt in prompts:
            n += 1
            rows.append(
                {
                    "id": f"route_{n:03d}",
                    "suite": "routing",
                    "prompt": prompt,
                    "expect_intent": intent,
                }
            )
    for intent, prompts in extras:
        for prompt in prompts:
            n += 1
            rows.append(
                {
                    "id": f"route_{n:03d}",
                    "suite": "routing",
                    "prompt": prompt,
                    "expect_intent": intent,
                }
            )
    return rows[:100]


def _e2e_rows() -> list[dict]:
    """100 end-to-end task prompts (manual rubric / future LLM-judge; skipped in stdlib --verify)."""
    tasks = [
        ("chat", "Explain when to use hybrid RAG versus fine-tuning a small classifier for support triage."),
        ("chat", "What are three risks of relying on a 360M parameter model for customer-facing answers?"),
        ("summarize", "Summarize: Our team shipped FAQ RAG, memory scopes, and NL routing in one Gradio app."),
        ("retrieve", "Search the FAQ: How do I export my data or request account deletion?"),
        ("classify", "Classify: Semiconductor firm announces new GPU for datacenter training workloads."),
        ("remember", "Remember that our demo scope for QA is golden-prompts-regression."),
        ("chat", "Compare fine-tuned encoders versus general LLMs for intent routing cost and latency."),
        ("reformulate", "Reformulate professionally: hey team sorry the deploy broke prod again lol."),
        ("chat", "Describe how prompt_signals overlays differ from session control phrases in Universal Brain."),
        ("retrieve", "FAQ search: What happens if smart routing picks the wrong tool?"),
    ]
    rows: list[dict] = []
    for i in range(100):
        base = tasks[i % len(tasks)]
        rows.append(
            {
                "id": f"e2e_{i + 1:03d}",
                "suite": "e2e",
                "prompt": base[1],
                "expect_intent": base[0],
                "note": "Manual or LLM-judge rubric; not scored in stdlib --verify.",
            }
        )
    return rows


def _hsp_intent_rows() -> list[dict]:
    """100 HSP shell intent cases (stdlib route-hint router; scored in --verify)."""
    cases: list[tuple[str | None, list[str]]] = [
        (
            "navigate:/swap",
            [
                "open swap page",
                "go to swap",
                "show swap screen",
                "navigate to swap tokens",
                "Open the Swap page please",
                "Can you show me the swap screen?",
                "Go to swap — I need to exchange TON",
                "Navigate to swap tokens on TON",
                "open swap",
                "show swap page",
                "go to the swap page",
                "navigate to swap",
                "Open swap for me",
                "Show swap tokens screen",
                "Please go to swap page",
                "Navigate me to swap",
                "open the swap page now",
                "show the swap route",
                "go to swap page thanks",
                "navigate to the swap screen",
            ],
        ),
        (
            "navigate:/send",
            [
                "send TON from my wallet",
                "transfer jetton to a friend",
                "I need to send tokens from wallet",
                "transfer TON to another wallet",
                "send jetton from wallet",
                "transfer token from my wallet",
                "Send TON to this address from wallet",
                "Transfer tokens from wallet please",
                "send token to my contact",
                "transfer TON jetton from wallet",
                "Send from wallet — TON transfer",
                "Transfer jetton tokens from wallet",
                "send wallet TON to user",
                "transfer wallet token amount",
                "Send TON token from wallet now",
            ],
        ),
        (
            "navigate:/get",
            [
                "show my wallet address",
                "get wallet receive details",
                "where is my receive wallet address",
                "show wallet address to receive TON",
                "get wallet QR for receiving",
                "receive TON — show wallet address",
                "wallet address for receive please",
                "get wallet receive screen",
                "show receive wallet address",
                "I need my wallet address to receive",
                "get wallet address for incoming payments",
                "show wallet address on Get screen",
                "receive funds — wallet address?",
                "get wallet page for receiving",
                "show my receive wallet address",
            ],
        ),
        (
            "feature:connect_telegram",
            [
                "connect telegram messages",
                "how do I connect telegram messages",
                "Connect Telegram to read chats",
                "link connect telegram messages in app",
                "Connect telegram messages from home footer",
                "I want connect telegram messages access",
                "Connect Telegram messages feature please",
                "help me connect telegram messages",
                "Connect telegram messages for feed",
                "steps to connect telegram messages",
                "Connect Telegram messages gateway",
                "connect telegram messages on this device",
            ],
        ),
        (
            "feature:shield",
            [
                "open shield security settings",
                "what is shield in this app",
                "Shield protection settings please",
                "explain shield security settings",
                "go to shield settings",
                "Shield — security settings overview",
                "Tell me about Shield protection",
                "where are shield security settings",
                "Shield feature security settings help",
                "show shield security settings",
                "What does Shield do for security settings?",
                "Shield security settings on home screen",
            ],
        ),
        (
            None,
            [
                "Explain gas fees on TON in plain language",
                "What is slippage when I swap tokens?",
                "Compare TON and ETH for small payments",
                "How do I back up my wallet safely?",
                "USDT price and holders on TON",
                "Summarize the home feed item types",
                "What can this program do?",
                "Explain smart layout on wide screens",
                "Is my swap rate fair right now?",
                "Help me understand jetton decimals",
                "What languages does the UI support?",
                "Tell me about Swap.Coffee integration",
                "How does sign in with Google work?",
                "Explain the trade screen vs swap",
                "What is a recovery phrase?",
                "Compare rates before I swap 10 TON",
                "General question about TON staking",
                "How do premade prompts in the bar work?",
                "Explain NFT feed cards",
                "What is EXPO_PUBLIC_API_BASE_URL for?",
                "Describe Telegram Mini App theme colors",
                "When should I confirm a send transaction?",
                "Explain verification badges on tokens",
                "How does the AI bar differ from bot chat?",
                "What is token_info mode?",
                "Draft a polite message to support",
            ],
        ),
    ]
    rows: list[dict] = []
    n = 0
    for expect_route, prompts in cases:
        for prompt in prompts:
            n += 1
            rows.append(
                {
                    "id": f"hsp_{n:03d}",
                    "suite": "hsp_intents",
                    "prompt": prompt,
                    "expect_route": expect_route,
                }
            )
    if len(rows) != 100:
        raise RuntimeError(f"expected 100 hsp_intents rows, got {len(rows)}")
    from hsp_intent_router import score_hsp_intent_row

    for row in rows:
        ok, detail, _ = score_hsp_intent_row(row)
        if not ok:
            raise RuntimeError(f"hsp seed self-check failed for {row['id']}: {detail}")
    return rows


def main() -> None:
    nl = _nl_rows()
    routing = _routing_rows()
    e2e = _e2e_rows()
    hsp = _hsp_intent_rows()
    assert len(nl) == 100, len(nl)
    assert len(routing) == 100, len(routing)
    assert len(e2e) == 100, len(e2e)
    assert len(hsp) == 100, len(hsp)
    _write_jsonl(_OUT / "nl_signals.jsonl", nl)
    _write_jsonl(_OUT / "routing.jsonl", routing)
    _write_jsonl(_OUT / "e2e.jsonl", e2e)
    _write_jsonl(_OUT / "hsp_intents.jsonl", hsp)
    manifest = {
        "schema": "golden_prompts_manifest/1.0",
        "counts": {
            "nl_signals": len(nl),
            "routing": len(routing),
            "e2e": len(e2e),
            "hsp_intents": len(hsp),
        },
        "files": [
            "nl_signals.jsonl",
            "routing.jsonl",
            "e2e.jsonl",
            "hsp_intents.jsonl",
        ],
    }
    (_OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(
        f"Wrote {len(nl) + len(routing) + len(e2e) + len(hsp)} prompts under {_OUT}"
    )


if __name__ == "__main__":
    main()
