#!/usr/bin/env python3
"""Chat-style UI (single-line input + history) for the local "Universal Brain" stack.

**Default:** generative LM + TinyModel encoder + FAQ RAG + SQLite memory. **`--lm-only`**
turns off encoder/RAG/memory.

**Natural language:** the model **routes** each line to an intent (summarize, retrieve, remember,
plain chat, …). Slash commands (`/help`, `/status`, …) still work as shortcuts.

Requirements:
  pip install -r optional-requirements-horizon2.txt

Examples:
  python scripts/universal_brain_chat.py
  python scripts/universal_brain_chat.py --no-smart-route
  python scripts/universal_brain_chat.py --lm-only --smoke

Say what you want in plain language, or type `/help`.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import uuid
import warnings
from pathlib import Path
from typing import Any

# Windows: avoid OpenMP/MKL oversubscription and duplicate CRT issues that can
# segfault during large `from_pretrained` CPU loads (common with torch+transformers).
if sys.platform == "win32":
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import torch

if sys.platform == "win32":
    torch.set_num_threads(1)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass

_scripts = Path(__file__).resolve().parent
_REPO = _scripts.parent
DEFAULT_MEMORY_DB = str(_REPO / ".tmp" / "ub_chat_memory.sqlite")
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))


def _load_dotenv_if_present(root: Path) -> None:
    """Load ``root / .env`` into ``os.environ`` without overriding existing keys (stdlib only)."""
    p = root / ".env"
    if not p.is_file():
        return
    try:
        text = p.read_text(encoding="utf-8")
    except OSError:
        return
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("export "):
            s = s[7:].strip()
        if "=" not in s:
            continue
        k, _, v = s.partition("=")
        k, v = k.strip(), v.strip()
        if not k or k in os.environ:
            continue
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        os.environ[k] = v


from horizon2_core import (  # noqa: E402
    DEFAULT_CHAT_SYSTEM,
    DEFAULT_INSTRUCTION_MODEL,
    SMOKE_MODEL_ID,
    LoadedLM,
    build_user_prompt,
    format_for_model,
    generate_chat_reply,
    generate_completion,
    load_causal_lm,
    pick_device,
)
from horizon3_store import (  # noqa: E402
    clear_session,
    connect,
    export_scope_json,
    forget_scope,
    init_schema,
    list_for_scope,
    put,
)
from google_cse_client import (  # noqa: E402
    format_cse_hits_markdown,
    google_cse_search,
    heuristic_suggests_web_search,
    read_google_cse_settings,
)
from nl_controls import analyze_embedded_prompt_signals, parse_control_action  # noqa: E402
from rag_faq_smoke import _pick_model, hybrid_retrieve, load_chunks  # noqa: E402
from tinymodel_runtime import TinyModelRuntime  # noqa: E402

HELP_TEXT = """**How to use**
- **Normal language:** ask in plain English (or mixed); the app **infers** what you want (summarize, search FAQ, save a note, etc.). Longer prompts may also **imply** reply shape for that turn only (for example trade-off questions → Pros/Cons layout, “in a table” → markdown table preference, “answer in Spanish” → reply language, **code only** → code-first output, **in under N words** → length cap, **hints only / don’t give the full solution** → guided discovery, **red team / sanity check my plan** → challenge-style pushback, **don’t remember this / off the record** → ephemeral hint, **screen reader friendly / WCAG** → accessibility layout hint, **ELI5 / lay audience in a long question** → beginner audience, **board-ready / Slack-casual wording** → formal or casual register, **valid JSON / return JSON in prose** → JSON output mode, **don’t guess / stick to facts in prose** → strict speculation, **TLDR first / BLUF in prose** → summary-first opening, **state assumptions / limitations / caveats** in prose → transparent confidence tone (explicit limits), **curl/bash/kubectl in prose** → runnable commands, **concrete / worked / toy example in prose** → richer examples, **example-free / skip examples in prose** → sparser examples, **define terms first / intuition or big-picture first in prose** → explanation order, **no questions at the end / suggest next steps in prose** → closing style, **ask questions before answering / answer without clarifiers in prose** → clarify-first mode, **markdown section headings vs flat prose in long prompts** → section layout, **analogy vs literal-only in long prompts** → analogy style) — see *Brain trace* **`prompt_signals:`** when detected.
- **Session controls (say it in chat, no slash command):**
  - *What is my current scope?*, *Show my session settings* -> prints scope + toggles (FAQ context, routing, trace)
  - *Start a new private session*, *Begin a fresh scope* -> generates a **new memory scope key** so notes are isolated from the shared default demo scope
  - *Switch to scope my-team-123* / *Use session demo-key* -> set the Horizon 3 **`scope_key`** from chat (ASCII id)
  - *Be brief* / *More detail please* / *Use bullet points* / *No bullets, plain paragraphs* -> soft **reply-style** hints (injected into the assistant system context; short control lines only)
  - *Strict FAQ* / *FAQ only* / *Stick to the FAQ* vs *Relaxed FAQ* / *FAQ plus general knowledge* vs *Balanced FAQ* / *Normal FAQ* -> **FAQ grounding** hints for how tightly to treat injected FAQ excerpts vs general knowledge
  - *Explain simply* / *ELI5* / *I'm a beginner* vs *Expert mode* / *Assume I'm technical* vs *Normal explanation level* -> **audience depth** hints (simple vs technical vs default)
  - *TLDR first* / *Lead with a summary* vs *No TLDR* / *Answer directly* vs *Default answer structure* -> **answer opening** style (short upfront summary vs dive straight in)
  - *Step by step* / *Numbered steps* vs *No numbered steps* / *Continuous prose* vs *Default step style* -> **procedure layout** (numbered steps vs flowing paragraphs)
  - *Flag your assumptions* / *Be explicit about uncertainty* vs *Be decisive* / *Don't hedge* vs *Reset uncertainty* -> **confidence tone** hints
  - *Suggest next steps* / *Offer follow-up questions* vs *No follow-up questions* / *No questions at the end* vs *Default follow-ups* -> **closing** style at end of answers
  - *Definitions first* / *Define terms first* vs *Intuition first* / *Big picture first* vs *Default explanation order* -> **concept order** in explanations
  - *Include examples* / *Use concrete examples* vs *Skip examples* / *No examples unless I ask* vs *Default examples* -> **example density**
  - *Use pros and cons* / *Pros and cons sections* vs *Compare in flowing prose* / *No pros and cons sections* vs *Default comparison style* -> **comparison layout** for trade-offs
  - *Formal tone* / *Professional register* vs *Casual tone* / *Speak casually* vs *Default tone* -> **writing register**
  - *Use code fences* / *Fenced code blocks* vs *Inline code only* / *No fenced code blocks* vs *Default code formatting* -> **markdown code layout**
  - *Use analogies* / *Analogies when helpful* vs *No analogies* / *Literal explanations only* vs *Default analogy style* -> **analogy / metaphor** usage
  - *Spell out acronyms* / *Expand acronyms on first use* vs *Assume I know acronyms* / *Don't expand acronyms* vs *Default acronym style* -> **acronym verbosity**
  - *Ask clarifying questions first* / *Clarify first* vs *No clarifying questions* / *Just answer without questions* vs *Default clarify mode* -> whether the assistant should ask for missing info before answering
  - *No speculation* / *Stick to high confidence only* vs *Brainstorm freely* / *Wild ideas ok* vs *Default speculation* -> how strictly to avoid guessing vs allow ideation
  - *Show your work* / *Show the derivation* vs *Final answer only* / *No derivation* vs *Default math detail* -> how much intermediate reasoning to show for math-like answers
  - *Answer in JSON* / *JSON output* vs *Plain text only* / *No JSON* vs *Default output format* -> structured output preference
  - *Be risk averse* / *Err on the side of safety* vs *Be pragmatic* / *Optimize for speed* vs *Default risk posture* -> conservative vs practical recommendations
  - *Give me runnable commands* / *Make it actionable* vs *No commands* / *Conceptual only* vs *Default actionability* -> how command-heavy responses should be
  - *Quote the FAQ excerpts* / *Use direct quotes* vs *Paraphrase only* / *Don't quote excerpts* vs *Default quote style* -> quoting vs paraphrasing when relying on injected excerpts
  - *Use tables* / *Tabular format* vs *No tables* / *Avoid tables* vs *Default table style* -> whether markdown tables are preferred
  - *Use emoji* / *Emoji ok* vs *No emoji* / *Avoid emoji* vs *Default emoji style* -> light **emoji** usage in answers
  - *Use section headings* / *Organize with headings* vs *No section headings* / *Flat answer* vs *Default section headings* -> **markdown headings** vs flat prose
  - *Bold key terms* / *Highlight important terms* vs *Minimal bold* / *Don't overuse bold* vs *Default emphasis* -> **inline bold** for key phrases vs sparse formatting
  - *Challenge my assumptions* / *Play devils advocate* vs *Be supportive* / *Assume good intent* vs *Default counterpoints* -> how much to **push back** vs stay encouraging
  - *Reset reply style* -> back to defaults for length + prose + balanced FAQ grounding + audience + opening + steps + confidence tone + follow-ups + concept order + examples + comparisons + register + code layout + analogy + acronym style + clarify + speculation + math detail + output format + risk posture + actionability + quote style + table style + emoji + section headings + term emphasis + counterpoints
  - *Export my memories*, *Download my notes as JSON* -> returns a Horizon 3 export blob for **this Space session scope**
  - *Delete all my memories for this chat* / *Erase everything you stored about me here* -> **forget-scope** wipe for this scope (**long-term + session** rows)
  - *Clear my session notes* -> wipes **session** notes only
  - *Turn off the FAQ context*, *Disable RAG snippets*, *Turn FAQ back on* -> toggles whether FAQ excerpts are injected into the chat system context
  - *Turn off smart routing*, *Go back to normal chat only* -> disables the JSON intent router (slash commands still work)
  - *Show the brain trace*, *Hide debug trace* -> toggles the optional *Brain trace* footer on replies
- **Shortcuts:** `/help`, `/status`, `/classify`, `/retrieve`, **`/web <query>`** (Google Programmable Search when `GOOGLE_CSE_API_KEY` + `GOOGLE_CSE_CX` are set), `/summarize`, `/reformulate`, `/grounded q ||| ctx`, `/remember`, `/session`, `/memories`, `/clear-session`, **`/similarity a ||| b`**, **`/embed` / `/embedding`**, **`/nearest q ||| c1 ||| c2`**.

**Intents the router understands** (examples, not exact wording):
- Ordinary chat / questions
- **Summarize** this text — provide the passage in the same message
- **Rewrite** professionally / rephrase
- **Answer using only** these facts — include both facts and question
- **Search** the FAQ / **find** in the knowledge base
- **Live web** (news, prices, “latest …”, fact-checking) — router uses **web_search**; with Google CSE configured, the server may also **auto-run** web search when your wording implies it (see brain trace **`+auto`**). Disable with **`--no-auto-web`** or env **`NO_AUTO_WEB=1`** on your own deployment.
- **Classify** (topic model) this paragraph
- **Similarity:** are these two snippets close in meaning? (encoder cosine)
- **Embedding** stats for a passage (dimension, norm, preview)
- **Nearest** among several options: which candidate is closest to a query? (`query ||| opt1 ||| opt2 …`)
- **Remember** / note / store: **long-term** vs **this session only**
- **Show** saved notes; **clear** session notes
- **Status** of loaded models

**Classifier** uses AG News–style labels on default Hub weights (World, Business, Sports, Sci/Tech).

If routing misfires, try rephrasing or use a slash command; **`--no-smart-route`** disables inference (chat only, plus `/…`)."""

# Shown under the chat + controls in the Gradio UI (Hugging Face Space and local).
GRADIO_INSTRUCTIONS_MARKDOWN = """### About this Space

**Universal Brain** pairs a small **generative** model with the **TinyModel1** encoder (AG News–style topics: World, Business, Sports, Sci/Tech), **FAQ retrieval** over a bundled corpus, **SQLite memory** scoped per session, and **natural-language routing** so many tasks work without slash commands. First CPU startup can take a few minutes while weights download.

---

### Using the layout

1. **Conversation** — scroll the transcript; replies may end with a *Brain trace* line (classify / RAG / memory hints) if that toggle is on.
2. **Message box** — type a line or paragraph; press **Send** or submit with Enter.
3. **Clear** — wipes the visible chat and the input (does not delete long-term memory unless you use the forget commands below).

---

### Testing embedded prompt signals (this Space)

These behaviors apply when your line is handled as **normal chat** (not a short dedicated control like *Be brief*). The app scans your wording and adds **one-turn** system hints. Say **Show the brain trace** first, send a message, then scroll to the bottom of the assistant reply.

| Goal | What to type (examples) | What to look for |
| --- | --- | --- |
| Comparison layout | One paragraph asking for **tradeoffs** or **pros and cons** between two concrete options (message **longer than ~50 characters**). | Footer line contains **`prompt_signals:`** and **`comparison_frame=pros_cons`** |
| Length cap | End your question with **in under 80 words** or **at most 3 sentences**. | **`len_cap=80w`** or **`len_cap=3s`** in **`prompt_signals:`**; the model should stay near that cap |
| Code-only | Ask for a tiny snippet and add **code only, no explanation** (or **just the code**). | **`code_only`** in **`prompt_signals:`**; reply should be mostly a fenced code block |
| Tables / steps / language | Ask for a summary **in a markdown table**, or a setup **step by step**, or **answer in spanish** in the same line as your question. | **`table_style=prefer`**, **`step_style=numbered`**, and/or **`language`** in **`prompt_signals:`** |
| Guided discovery (hints / Socratic) | Ask a **how / why** question and say you want **hints only** or **don’t give me the full solution yet** (keep the message substantive, not a one-liner control). | **`guided`** in **`prompt_signals:`**; first reply should skew toward questions and nudges |
| Red-team / critique | In one paragraph, describe a **plan or design** and ask for a **red team**, **sanity check**, **what am I missing**, or **devil’s advocate** review (not a one-line control). | **`counterpoint_tone=challenge`** inside **`prompt_signals:`**; reply should stress-test assumptions |
| Ephemeral / no memory | Say **off the record**, **don’t remember this**, **no memory for this**, or **don’t log this** in the same message as your question (demo: shared Space scopes are not true secrecy). | **`ephemeral`** in **`prompt_signals:`**; assistant should avoid pushing `/remember` for that content |
| Accessibility / screen readers | Ask for a **screen reader friendly** or **WCAG-aware** answer, or say the write-up is **for blind readers** / **for NVDA users** in a full sentence (not a one-word ping). | **`a11y`** in **`prompt_signals:`**; reply should favor linear structure, headings, and non-table-only facts |
| Beginner / ELI5 in context | In a **longer** question (not a one-line control), ask for **ELI5**, **explain like I'm five**, **total beginner**, **lay audience**, **no technical background**, etc., plus a normal **what/why/how** ask. | **`audience=simple`** in **`prompt_signals:`**; reply should use plain language and minimal jargon |
| Formal vs casual register | Ask for a **board-ready** / **client-facing** / **formal memo** / **for regulators** write-up, **or** say you want a **Slack message**, **keep it casual**, **water cooler** tone (one dominant style per message). | **`register_tone=formal`** or **`register_tone=casual`** in **`prompt_signals:`** |
| JSON / structured output | In a **long** message, ask for **valid JSON**, **return JSON**, **as a JSON object**, **machine-readable JSON**, etc. (say **no json** / **plain text only** if you want to opt out). | **`output_format=json`** in **`prompt_signals:`**; reply should be parseable JSON when practical |
| Strict facts / low speculation | In a **long** message, ask to **not guess**, **avoid hallucinations**, **only high confidence**, **stick to facts**, **if unsure say so**, etc. (avoid mixing with **brainstorm freely** in the same line). | **`speculation=strict`** in **`prompt_signals:`**; reply should label uncertainty clearly |
| Summary / BLUF first | In a **long** message, ask to **TLDR first**, **lead with a one-line summary**, **bottom line up front**, **BLUF**, **executive summary first**, etc. (say **skip the summary** / **answer directly** to opt out). | **`answer_lead=tldr_first`** in **`prompt_signals:`**; reply should open with a short summary line |
| Runnable commands | In a **long** message, ask for **curl one-liner**, **bash snippet**, **kubectl**, **copy-paste into terminal**, **docker run example**, etc. (say **conceptual only** / **no commands** to opt out). | **`actionability=commands`** in **`prompt_signals:`**; reply should include concrete commands where sensible |
| Assumptions / limitations | In a **long** message, ask to **state your assumptions**, **assumptions and limitations**, **caveats upfront**, **scope and assumptions**, **what we are assuming**, or to **flag key uncertainties** (say **don’t hedge** / **be decisive** or **skip assumptions** to opt out). | **`confidence_tone=transparent`** in **`prompt_signals:`**; reply should surface assumptions, limits, and uncertainty clearly |
| Concrete examples vs example-free | In a **long** message, ask for a **worked example**, **walk me through a toy example**, **illustrate with a concrete example**, **ground your answer in an example**, etc. **Or** ask to **skip examples**, **theory only**, **keep it abstract**, **example-free** (avoid mixing both in one line). | **`example_density=rich`** or **`example_density=sparse`** in **`prompt_signals:`**; reply should include or omit short illustrative examples accordingly |
| Explanation order | In a **long** message, ask to **define terms first**, **definitions before details**, **formal definitions upfront**, **terminology first**, etc. **Or** ask for **intuition before math**, **big picture first**, **motivation before the formal proof**, **start with the high-level sketch** (avoid asking for both orders in one line). | **`exposition_order=definitions_first`** or **`exposition_order=intuition_first`** in **`prompt_signals:`**; reply should lead with definitions or with intuition accordingly |
| Closing / follow-ups | In a **long** message, ask for **no questions at the end**, **don’t ask if I need anything else**, **finish crisply**, **skip the stock closer**, etc. **Or** ask to **suggest next steps**, **end with actionable next steps**, **what should we do next**, **offer ways to go deeper** (avoid mixing both in one line). | **`followup_close=minimal`** or **`followup_close=suggest`** in **`prompt_signals:`**; reply should omit or include a light optional follow-up line accordingly |
| Clarify-first vs answer-first | In a **long** message, ask to **ask clarifying questions before you answer**, **if anything is unclear ask me first**, **confirm my constraints before**, etc. **Or** say **no clarifying questions**, **answer without asking questions first**, **don’t interrogate me first**, **give your best answer without asking** (avoid mixing both in one line). | **`clarify_first=on`** or **`clarify_first=off`** in **`prompt_signals:`**; first reply should ask brief questions first or answer directly |
| Section headings vs flat | In a **long** message, ask to **use markdown headings**, **organize with headings**, **structure the answer with clear headings**, **h2 or h3 headings for each topic**, etc. **Or** ask for a **flat answer**, **no section headings**, **avoid markdown headings**, **continuous prose only** (avoid mixing both in one line). | **`section_headings=prefer`** or **`section_headings=avoid`** in **`prompt_signals:`**; reply should use or avoid `##` / `###` title lines accordingly |
| Analogies vs literal | In a **long** message, ask to **use a helpful analogy**, **explain with a simple analogy**, **liken this to something familiar**, **map it to an everyday example**, etc. **Or** say **no analogies**, **skip metaphors**, **literal explanations only**, **stick to literal technical description** (avoid mixing both in one line). | **`analogy_use=prefer`** or **`analogy_use=avoid`** in **`prompt_signals:`**; reply may include one tight analogy or stay metaphor-free accordingly |

If there is no footer, brain trace is off for that session, or this deployment has **no** encoder / FAQ / memory / web layers and no prompt signals fired yet—**prompt signals alone** still turn the footer on once this feature triggers.

---

### What to try (step-by-step)

| Goal | What to type |
| --- | --- |
| See what is loaded | `/status` |
| Full in-chat manual | `/help` |
| Normal Q&A | Ask any question in plain language. |
| **Classifier** (full probability table) | `/classify Stocks rallied after earnings.` or ask naturally to classify a paragraph. |
| **FAQ search** (scored chunks) | `/retrieve shipping policy` or “search the FAQ for …”. |
| **Web search** (Google CSE) | `/web latest Python 3.13 release notes` or ask for **live web** / **Google** news (needs `GOOGLE_CSE_API_KEY` + `GOOGLE_CSE_CX`). |
| **Summarize** | `/summarize` + long text, or “summarize this: …”. |
| **Rephrase** | `/reformulate` + text, or “rewrite this professionally: …”. |
| **Answer from facts only** | `/grounded Will you refund? ||| Our policy is 14-day returns.` (question and context separated by `|||`). |
| **Similarity** (encoder cosine) | `/similarity The market rose. ||| Stocks gained today.` |
| **Embedding** preview | `/embed A short passage` or `/embedding …`. |
| **Pick nearest option** | `/nearest query ||| option one ||| option two` (add more `|||` segments for more candidates). |
| **Memory — long-term** | `/remember My project code is alpha-42` or say you want to remember something. |
| **Memory — this session** | `/session Temporary note for this chat` |
| **List saved notes** | `/memories` or ask to show stored notes. |
| **Clear session notes only** | `/clear-session` |
| **Export notes (JSON)** | Say *Export my memories* / *Download my notes as JSON*. |
| **Wipe all notes for this scope** | Say *Delete all my memories for this chat* (long-term + session for current scope). |
| **Isolate your notes (new scope)** | *Start a new private session* / *Begin a fresh scope* — then use `/remember` and `/memories` to confirm only new notes appear. |
| **Switch scope** | *Switch to scope my-key* (ASCII id) to attach memory to a named scope. |
| **Brain trace on/off** | *Show the brain trace* / *Hide debug trace* — then ask a normal question and check the footer line. |
| **FAQ snippets on/off** | *Turn off the FAQ context* / *Turn FAQ back on*. |
| **Routing on/off** | *Turn off smart routing* returns to plain chat + slash shortcuts; turn back on per `/help` phrasing. |
| **Reply style** | Phrases like *Be brief*, *Use bullet points*, *Strict FAQ*, *ELI5*, *Formal tone*, *Reset reply style* (see `/help` for the full list). |

---

### Google web search — Hugging Face Space setup and how to test

This Space can call **Google Programmable Search (Custom Search JSON API)** when you configure credentials on the Hub (and redeploy if you added new files).

**1) Space settings (Repository → Settings)**

| Name | Type | Value |
| --- | --- | --- |
| `GOOGLE_CSE_API_KEY` | **Secret** | Google Cloud API key restricted to **Custom Search API** (Application restrictions: **None** is typical for server-side Spaces). |
| `GOOGLE_CSE_CX` | **Variable** or **Secret** | Search engine ID from [Programmable Search Engine control panel](https://programmablesearchengine.google.com/controlpanel/all) → your engine → **Overview** → **Search engine ID** (the `cx` value). |

Optional **Variables**: `GOOGLE_CSE_NUM` (1–10, default 5), `GOOGLE_CSE_SAFE` (e.g. `off` or `active` — see Google’s `cse.list` docs).

**2) Restart**

After saving secrets/variables, **Restart this Space** (or trigger a new deployment) so the container picks up env vars.

**3) Verify configuration**

Type **`/status`** and press **Send**. The line **Google web search (CSE)** should show **on** when both `GOOGLE_CSE_API_KEY` and `GOOGLE_CSE_CX` are set. If it says **off**, the Space process does not see those variables yet.

**4) Test the API directly (no router)**

- **`/web`** — returns **raw search hits** (titles, URLs, snippets) only. Example: `/web Python 3.13 release date`  
- Same as **`/search_web …`**

If you see an error about HTTP 403 or “API key not valid”, fix the key or enable **Custom Search API** for that GCP project.

**5) Test with the AI (smart routing)**

- Ensure **smart routing** is on (say *Turn on smart routing* if you turned it off).  
- Ask in plain language for **live web** / **Google** / **today’s** information, e.g. *Search the web for the latest SpaceX launch summary* or *What does the web say about …?*  
- The router uses intent **`web_search`**: the app fetches snippets, injects them into the model context, then the assistant replies **using those sources** (cite **[Web n]** when using a snippet).  
- **Automatic web:** if Google CSE is configured, the app may also run a web search when your message **implies** fresh public facts (e.g. *latest*, *today*, *who won*, *stock price*, a recent year + question) even if you do not say “search the web”. On a self-hosted Space you can disable that with **`--no-auto-web`** or env **`NO_AUTO_WEB=1`**. Brain trace may show **`+auto`** on the web line when the upgrade came from this layer rather than the router alone.  
- If the model stays in FAQ-only mode, use **`/web …`** first to confirm the API works, then try clearer web phrasing.

**6) Brain trace**

With **Show the brain trace** on, look for **`web:CSE:N`** (N = number of hits) at the bottom of the assistant message after a web-backed reply.

**7) Limits**

Google enforces **quotas** and may **restrict new signups** for the legacy Custom Search JSON API — check current Google documentation. This demo does not store your API key in the repo; it only reads **Space env** at runtime.

---

### Natural-language routing (no `/` required)

The app can infer intents such as **chat**, **summarize**, **reformulate**, **grounded Q&A**, **FAQ retrieve**, **web_search** (public web via Google CSE when configured), **classify**, **similarity**, **embedding**, **nearest candidate**, **remember / list / clear memory**, and **status**. If the wrong tool runs, repeat with a clearer verb or use the matching **slash command** from the table above.

---

### Session controls (plain English, no `/`)

These adjust **scope**, **memory**, **FAQ injection**, **routing**, **brain trace**, and **reply style** (hints fed into the system prompt). Examples (not exact wording required):

- **Scope / visibility:** *What is my current scope?* · *Show my session settings* · *Start a new private session* · *Switch to scope my-key*
- **Reply shape:** *Be brief* · *More detail please* · *Use bullet points* · *Reset reply style*
- **FAQ grounding:** *Strict FAQ* · *Relaxed FAQ* · *Balanced FAQ*
- **Audience & structure:** *ELI5* · *Expert mode* · *TLDR first* · *Answer directly* · *Step by step* · *No numbered steps* · *Definitions first* · *Intuition first*
- **Tone & format:** *Formal tone* · *Casual tone* · *Use code fences* · *Inline code only* · *Use tables* · *No tables* · *Use emoji* · *No emoji* · *Use section headings* · *Flat answer* · *Bold key terms* · *Minimal bold*
- **Reasoning habits:** *Flag your assumptions* · *Be decisive* · *Suggest next steps* · *No follow-up questions* · *Clarify first* · *No clarifying questions* · *No speculation* · *Brainstorm freely* · *Show your work* · *Final answer only*
- **Output & safety:** *Answer in JSON* · *Plain text only* · *Be risk averse* · *Be pragmatic* · *Give me runnable commands* · *No commands* · *Quote the FAQ excerpts* · *Paraphrase only*
- **Style extras:** *Use analogies* · *No analogies* · *Spell out acronyms* · *Don't expand acronyms* · *Include examples* · *Skip examples* · *Use pros and cons* · *Compare in flowing prose* · *Challenge my assumptions* · *Be supportive*
- **Memory maintenance:** *Clear my session notes* · *Export my memories* · *Delete all my memories for this chat*
- **Debug / behavior:** *Turn off FAQ context* · *Turn FAQ back on* · *Turn off smart routing* · *Show the brain trace* · *Hide debug trace*

---

### Encoder + trace

The encoder adds a soft **topic hint** to the system context and can show **`classify:…`** in the brain trace. Labels reflect **TinyModel1** training (≈ AG News). Use `/classify` when you want the full markdown probability table in the reply.

---

### Hugging Face API

On the Space page, open **Use via API** to call the **`chat`** endpoint (same pipeline as the Send button) from HTTP or the Gradio client.

---

### Tips

- **Shared demo**: the default scope may be shared with other visitors; use *Start a new private session* for isolated memory.
- **Optional Space env**: `HORIZON2_MODEL` can override the generative model id; `HF_TOKEN` (secret) helps with Hub downloads; **`GOOGLE_CSE_API_KEY`** + **`GOOGLE_CSE_CX`** enable web search (see section **Google web search** above).
- **More phrases**: the repo `README` and `/help` list additional natural phrasings for session controls."""

ROUTER_SYSTEM = """You are an intent router for a desktop AI assistant. The user speaks naturally (any language). Output EXACTLY one JSON object, one line, no markdown fences, no explanation.

Schema:
{"intent":"<name>","text":"","question":"","context":""}

intent must be one of:
- chat — general talk, advice, open questions, follow-ups; put the FULL user message in "text"
- summarize — user wants a shorter summary; put source in "text"
- reformulate — rewrite/clarify/professional tone; source in "text"
- grounded — answer only from given facts; put QUESTION in "question", FACTS in "context" (if user mixes both in one blob, split sensibly)
- retrieve — search **FAQ / internal knowledge** corpus only; put search query in "text"
- web_search — user wants **live web** facts (news, current events, URLs); put the **search query** in "text" (not for FAQ-only lookup)
- classify — show topic-classifier probabilities; put passage in "text"
- similarity — cosine similarity between two texts; put "text_a ||| text_b" in "text"
- embedding — embedding vector summary for one passage; put passage in "text"
- nearest — encoder top-k over candidates; put "query ||| candidate1 ||| candidate2 ||| …" in "text" (at least one candidate)
- remember — save a durable note; put note body in "text"
- session_note — save a session-only note; put note in "text"
- list_memories — user wants to see saved notes
- clear_session — user wants session-only notes deleted
- status — loaded components / debug info
- help — explain available capabilities

Rules:
- Default to "chat" when unsure; copy the entire user message into "text".
- Do not invent facts for "grounded": if no clear facts/context, use "chat" instead.
- Use **retrieve** for bundled FAQ / help-base search; use **web_search** when the user clearly needs the **public web** (today, external site, breaking news, "google this", etc.).
- **web_search vs chat (critical):** choose **web_search** when a good answer depends on **recent events**, **live or site-specific data** (prices, sports scores, releases after your knowledge cutoff, "what happened today", laws/regulations that change), **verifying a claim against the public web**, or **finding an official URL**. Choose **chat** for timeless explanations, coding how-to without needing today's docs, brainstorming, role-play, or personal opinion where web snippets would not change the answer.
- Extract minimal "text" for tool intents (do not repeat system chatter)."""

VALID_INTENTS = frozenset(
    {
        "chat",
        "summarize",
        "reformulate",
        "grounded",
        "retrieve",
        "web_search",
        "classify",
        "similarity",
        "embedding",
        "nearest",
        "remember",
        "session_note",
        "list_memories",
        "clear_session",
        "status",
        "help",
    }
)

_INTENT_ALIASES = {
    "memory": "list_memories",
    "memories": "list_memories",
    "notes": "list_memories",
    "search": "retrieve",
    "faq": "retrieve",
    "lookup": "retrieve",
    "internet": "web_search",
    "google": "web_search",
    "browse_web": "web_search",
    "similar": "similarity",
    "cosine": "similarity",
    "embed": "embedding",
    "embeddings": "embedding",
    "knn": "nearest",
    "triage": "nearest",
    "encoder_retrieve": "nearest",
}


def _parse_two_segments(blob: str) -> tuple[str, str]:
    if "|||" not in blob:
        raise ValueError("Need two segments separated by `|||` (e.g. `text A ||| text B`).")
    a, _, b = blob.partition("|||")
    a, b = a.strip(), b.strip()
    if not a or not b:
        raise ValueError("Both sides of `|||` must be non-empty.")
    return a, b


def _parse_nearest_blob(blob: str) -> tuple[str, list[str]]:
    parts = [p.strip() for p in blob.split("|||") if p.strip()]
    if len(parts) < 2:
        raise ValueError(
            "Need `query ||| candidate1 ||| candidate2` (at least one candidate after `|||`)."
        )
    return parts[0], parts[1:]


def _embedding_summary_markdown(encoder: TinyModelRuntime, passage: str) -> str:
    vec = encoder.embed([passage], normalize=False)[0]
    dim = int(vec.shape[0])
    norm = float(torch.linalg.vector_norm(vec))
    k = min(8, dim)
    head = ", ".join(f"{float(vec[i]):.4f}" for i in range(k))
    return "\n".join(
        [
            "### Encoder embedding (raw [CLS], not L2-normalized)\n",
            f"- **dim:** {dim}",
            f"- **L2 norm:** {norm:.4f}",
            f"- **first {k} values:** {head}",
        ]
    )


def _nearest_markdown(
    encoder: TinyModelRuntime,
    query: str,
    candidates: list[str],
    *,
    top_k: int,
) -> str:
    hits = encoder.retrieve(query, candidates, top_k=top_k)
    if not hits:
        return "(No candidates.)"
    lines = ["### Encoder nearest neighbors (cosine on pooled embeddings)\n"]
    for rank, h in enumerate(hits, 1):
        lines.append(
            f"**#{rank}** score={h.score:.4f} · index={h.index}\n{_clip(h.text, 700)}\n"
        )
    return "\n".join(lines)


def _classifier_result_markdown(probs: dict[str, float]) -> str:
    ranked = sorted(probs.items(), key=lambda x: -x[1])
    top_lab, top_p = ranked[0]
    lines = [
        "### Classifier (TinyModel)\n",
        f"**Winner:** `{top_lab}` · **p = {top_p:.4f}**\n",
        "\n| rank | label | p |\n|:---:|:---|---:|",
    ]
    for i, (lab, p) in enumerate(ranked[:12], 1):
        mark = " **←**" if i == 1 else ""
        lines.append(f"| {i} | {lab}{mark} | {p:.4f} |")
    return "\n".join(lines)


def _ensure_gradio_can_reach_localhost() -> None:
    """Gradio probes localhost via httpx; HTTP(S)_PROXY can break that on Windows/VPN."""
    extras = ("localhost", "127.0.0.1", "::1")
    for var in ("NO_PROXY", "no_proxy"):
        raw = os.environ.get(var, "")
        parts = [p.strip() for p in raw.replace(";", ",").split(",") if p.strip()]
        for h in extras:
            if h not in parts:
                parts.append(h)
        os.environ[var] = ",".join(parts)


def _patch_gradio_localhost_probe() -> None:
    """Gradio's built-in `url_ok` uses httpx with env proxies; on Windows/VPN, HEAD to
    127.0.0.1 often fails even though the app is up. Use direct (no-proxy) requests.
    """
    import time as time_mod
    import warnings as warn_mod

    import gradio.networking as gn
    import httpx

    def url_ok(url: str) -> bool:
        ok_codes = (200, 204, 401, 302, 303, 307)
        for _ in range(5):
            try:
                with warn_mod.catch_warnings():
                    warn_mod.filterwarnings("ignore")
                with httpx.Client(
                    timeout=5,
                    verify=False,
                    trust_env=False,
                    follow_redirects=True,
                ) as client:
                    r = client.head(url)
                    if r.status_code in ok_codes:
                        return True
                    r = client.get(url)
                    if r.status_code in ok_codes:
                        return True
            except (ConnectionError, OSError, httpx.HTTPError, httpx.TimeoutException):
                pass
            time_mod.sleep(0.4)
        return False

    gn.url_ok = url_ok  # type: ignore[assignment]


def _clip(s: str, n: int) -> str:
    s = (s or "").strip()
    if len(s) <= n:
        return s
    return s[: n - 3] + "..."


def _extract_json_object(s: str) -> dict | None:
    s = (s or "").strip()
    try:
        d = json.loads(s)
        return d if isinstance(d, dict) else None
    except json.JSONDecodeError:
        pass
    start = s.find("{")
    end = s.rfind("}")
    if start >= 0 and end > start:
        try:
            d = json.loads(s[start : end + 1])
            return d if isinstance(d, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def _normalize_intent(raw: str) -> str:
    x = (raw or "chat").strip().lower().replace("-", "_")
    x = _INTENT_ALIASES.get(x, x)
    return x if x in VALID_INTENTS else "chat"


def infer_route(
    lm: LoadedLM,
    user_message: str,
    *,
    seed: int,
    max_new_tokens: int,
) -> dict[str, str]:
    u = (
        f"USER_MESSAGE (verbatim):\n{user_message}\n\n"
        "Output the JSON object now."
    )
    if getattr(lm.tokenizer, "chat_template", None):
        prompt = lm.tokenizer.apply_chat_template(
            [{"role": "system", "content": ROUTER_SYSTEM}, {"role": "user", "content": u}],
            tokenize=False,
            add_generation_prompt=True,
        )
    else:
        prompt = f"{ROUTER_SYSTEM}\n\n{u}\nJSON:"
    raw, _, _, _ = generate_completion(
        lm,
        prompt,
        max_new_tokens=max_new_tokens,
        seed=seed,
        do_sample=False,
    )
    data = _extract_json_object(raw) or {}
    intent = _normalize_intent(str(data.get("intent", "chat")))
    return {
        "intent": intent,
        "text": str(data.get("text", "")).strip(),
        "question": str(data.get("question", "")).strip(),
        "context": str(data.get("context", "")).strip(),
    }


def _format_status(
    *,
    meta_mid: str,
    meta_encoder: str,
    meta_rag_path: str | None,
    rag_chunks: list[str] | None,
    meta_mem_db: str | None,
    scope_key: str,
) -> str:
    rag_n = len(rag_chunks) if rag_chunks else 0
    g_key, g_cx, _, _ = read_google_cse_settings()
    cse_line = (
        "**on** (`GOOGLE_CSE_API_KEY` + `GOOGLE_CSE_CX`)"
        if g_key and g_cx
        else "**off** (set `GOOGLE_CSE_API_KEY` and `GOOGLE_CSE_CX` for `/web` + routed web search)"
    )
    lines = [
        "### Status\n",
        f"- **Generative:** `{meta_mid}`",
        f"- **Encoder:** {meta_encoder}",
        f"- **RAG corpus:** {_clip(meta_rag_path or '—', 80)} · **chunks:** {rag_n}",
        f"- **Memory DB:** `{meta_mem_db or 'off'}` · **scope:** `{scope_key}`",
        f"- **Google web search (CSE):** {cse_line}",
    ]
    return "\n".join(lines)


def run_routed_tool(
    route: dict[str, str],
    *,
    msg: str,
    lm: LoadedLM,
    mem_conn: sqlite3.Connection | None,
    scope_key: str,
    encoder: TinyModelRuntime | None,
    rag_chunks: list[str] | None,
    rag_top_k: int,
    task_max_new_tokens: int,
    seed: int,
    meta_mid: str,
    meta_encoder: str,
    meta_mem_db: str | None,
    meta_rag_path: str | None,
) -> str:
    intent = route["intent"]
    text = route["text"]
    question = route["question"]
    context = route["context"]

    if intent == "help":
        return HELP_TEXT
    if intent == "status":
        return _format_status(
            meta_mid=meta_mid,
            meta_encoder=meta_encoder,
            meta_rag_path=meta_rag_path,
            rag_chunks=rag_chunks,
            meta_mem_db=meta_mem_db,
            scope_key=scope_key,
        )
    if intent == "classify":
        if not encoder:
            return "Classifier is not loaded (try without `--lm-only` / `--no-encoder`)."
        passage = text or msg
        if not passage:
            return "Tell me what text to classify."
        return _classifier_result_markdown(encoder.classify([passage])[0])
    if intent == "retrieve":
        if not encoder or not rag_chunks:
            return "FAQ search needs encoder + corpus (defaults on unless disabled)."
        q = text or msg
        if not q:
            return "What should I search for?"
        hr = hybrid_retrieve(encoder, q, rag_chunks, top_k=rag_top_k)
        if not hr:
            return "(No matching chunks.)"
        out = ["### Retrieved chunks\n"]
        for i, (sc, _idx, txt) in enumerate(hr, 1):
            out.append(f"**#{i}** score={sc:.4f}\n{_clip(txt, 700)}\n")
        return "\n".join(out)

    if intent == "similarity":
        if not encoder:
            return "Similarity needs the encoder (drop `--lm-only` / `--no-encoder`)."
        blob = (text or msg).strip()
        if not blob:
            return "Provide two texts: `first ||| second`."
        try:
            ta, tb = _parse_two_segments(blob)
        except ValueError as e:
            return str(e)
        score = encoder.similarity(ta, tb)
        return (
            "### Similarity (encoder cosine)\n"
            f"**Score:** {score:.4f}\n\n"
            f"**A:** {_clip(ta, 480)}\n\n"
            f"**B:** {_clip(tb, 480)}"
        )

    if intent == "embedding":
        if not encoder:
            return "Embedding stats need the encoder (drop `--lm-only` / `--no-encoder`)."
        passage = (text or msg).strip()
        if not passage:
            return "What text should I embed?"
        return _embedding_summary_markdown(encoder, passage)

    if intent == "nearest":
        if not encoder:
            return "Nearest-neighbor search needs the encoder (drop `--lm-only` / `--no-encoder`)."
        blob = (text or msg).strip()
        if not blob:
            return "Usage: `query ||| option1 ||| option2 ...`"
        try:
            query, cands = _parse_nearest_blob(blob)
        except ValueError as e:
            return str(e)
        k = max(1, min(rag_top_k, len(cands)))
        return _nearest_markdown(encoder, query, cands, top_k=k)

    if intent in ("summarize", "reformulate", "grounded"):
        if intent == "grounded":
            qn = question or text
            ctx = context
            if not qn or not ctx:
                bod = text or msg
                # one-blob fallback: first sentence as question rest as context heuristic weak
                if "?" in bod:
                    qn = bod.split("?", 1)[0] + "?"
                    ctx = bod.split("?", 1)[1].strip() or bod
                else:
                    return (
                        "For a grounded answer I need **facts** and a **question**. "
                        "Say both in one message (e.g. facts first, then your question)."
                    )
            try:
                up = build_user_prompt("grounded", qn.strip(), context=ctx.strip())
            except ValueError as e:
                return str(e)
        else:
            src = text or msg
            if not src:
                return "What text should I process?"
            task = "summarize" if intent == "summarize" else "reformulate"
            up = build_user_prompt(task, src)
        prompt = format_for_model(lm.tokenizer, up)
        out, _, _, sec = generate_completion(
            lm,
            prompt,
            max_new_tokens=task_max_new_tokens,
            seed=seed,
            do_sample=True,
        )
        return f"**{intent}** ({sec:.2f}s)\n\n{out or '(empty)'}"

    if intent in ("remember", "session_note", "list_memories", "clear_session"):
        if mem_conn is None:
            return "Memory is off (enable default DB or drop `--no-memory`)."
        if intent == "remember":
            note = text or msg
            if not note:
                return "What should I remember?"
            put(mem_conn, scope_key=scope_key, kind="long_term", content=note)
            return "Saved to **long-term** memory."
        if intent == "session_note":
            note = text or msg
            if not note:
                return "What should I store for this session?"
            put(mem_conn, scope_key=scope_key, kind="session", content=note)
            return "Saved to **session** memory."
        if intent == "list_memories":
            items = list_for_scope(mem_conn, scope_key)
            if not items:
                return "(No saved notes for this scope.)"
            lines = [f"- **{it.kind}** · {_clip(it.content, 320)}" for it in items[:24]]
            extra = f"\n\n… {len(items) - 24} more" if len(items) > 24 else ""
            return "Saved notes:\n" + "\n".join(lines) + extra
        if intent == "clear_session":
            n = clear_session(mem_conn, scope_key)
            return f"Cleared **{n}** session note(s). Long-term notes unchanged."

    return ""


def handle_nl_control(
    msg: str,
    session: dict[str, Any],
    *,
    mem_conn: sqlite3.Connection | None,
    scope_key: str,
    rag_chunks_base: list[str] | None,
    locked_no_smart_route: bool,
) -> str | None:
    act = parse_control_action(msg)
    if act is None:
        return None

    if act.name == "show_session":
        bits = [
            f"- scope: `{scope_key}`",
            f"- smart routing: **{'on' if session.get('smart_route') and not locked_no_smart_route else 'off'}**",
            f"- FAQ context: **{'on' if session.get('rag') and rag_chunks_base is not None else 'off'}**",
            f"- brain trace footer: **{'on' if session.get('trace') else 'off'}**",
            f"- memory store: **{'on' if mem_conn is not None else 'off'}**",
            f"- reply length: **{session.get('verbosity', 'normal')}**",
            f"- lists: **{'bullets when helpful' if session.get('reply_format') == 'bullets' else 'prose'}**",
            f"- FAQ grounding: **{session.get('faq_grounding', 'normal')}**",
            f"- audience: **{session.get('audience', 'normal')}**",
            f"- answer opening: **{session.get('answer_lead', 'normal')}**",
            f"- procedure steps: **{session.get('step_style', 'normal')}**",
            f"- confidence tone: **{session.get('confidence_tone', 'normal')}**",
            f"- follow-up ending: **{session.get('followup_close', 'normal')}**",
            f"- concept order: **{session.get('exposition_order', 'normal')}**",
            f"- examples: **{session.get('example_density', 'normal')}**",
            f"- comparisons: **{session.get('comparison_frame', 'normal')}**",
            f"- register: **{session.get('register_tone', 'normal')}**",
            f"- code blocks: **{session.get('code_block_style', 'normal')}**",
            f"- analogies: **{session.get('analogy_use', 'normal')}**",
            f"- acronyms: **{session.get('acronym_style', 'normal')}**",
            f"- clarify-first: **{session.get('clarify_first', 'normal')}**",
            f"- speculation: **{session.get('speculation', 'normal')}**",
            f"- math detail: **{session.get('math_detail', 'normal')}**",
            f"- output format: **{session.get('output_format', 'normal')}**",
            f"- risk posture: **{session.get('risk_posture', 'normal')}**",
            f"- actionability: **{session.get('actionability', 'normal')}**",
            f"- quote style: **{session.get('quote_style', 'normal')}**",
            f"- tables: **{session.get('table_style', 'normal')}**",
            f"- emoji: **{session.get('emoji_style', 'normal')}**",
            f"- section headings: **{session.get('section_headings', 'normal')}**",
            f"- term emphasis: **{session.get('term_emphasis', 'normal')}**",
            f"- counterpoints: **{session.get('counterpoint_tone', 'normal')}**",
        ]
        return "### Session settings\n" + "\n".join(bits)

    if act.name == "new_private_session":
        # Keep it readable and low-collision; not a secret, just a scope id.
        new_scope = f"ub-{uuid.uuid4().hex[:8]}"
        session["scope_key"] = new_scope
        return (
            f"**Started a new private session scope.**\n\n"
            f"Current scope is now `{new_scope}`.\n"
            "Memory operations (remember/export/forget) will apply to this new scope."
        )

    if act.name == "set_scope":
        if not act.value:
            return "Tell me the scope key, e.g. `Switch to scope demo-123`."
        session["scope_key"] = act.value
        return f"Switched session scope to `{act.value}`."

    if act.name == "export_memory":
        if mem_conn is None:
            return "Memory is off for this Space (no SQLite store); nothing to export."
        blob = export_scope_json(mem_conn, scope_key)
        js = json.dumps(blob, indent=2, ensure_ascii=False)
        max_chars = 48_000
        if len(js) > max_chars:
            js = js[:max_chars] + "\n…(truncated for chat; schema is horizon3_export/1.0)…"
        return f"### Memory export (`{scope_key}`)\nPaste/save externally if needed.\n\n```json\n{js}\n```"

    if act.name == "forget_scope":
        if mem_conn is None:
            return "Memory is off; nothing to delete."
        n = forget_scope(mem_conn, scope_key)
        return (
            f"**Erased stored memory for this Space session.**\n\n"
            f"Deleted **{n}** row(s) (**session + long-term**) for `{scope_key}`."
        )

    if act.name == "list_memories":
        if mem_conn is None:
            return "Memory is off."
        items = list_for_scope(mem_conn, scope_key)
        if not items:
            return "(No saved notes for this scope.)"
        lines = [f"- **{it.kind}** · {_clip(it.content, 320)}" for it in items[:24]]
        extra = f"\n\n… {len(items) - 24} more" if len(items) > 24 else ""
        return "**Saved notes:**\n" + "\n".join(lines) + extra

    if act.name == "clear_session":
        if mem_conn is None:
            return "Memory is off."
        n = clear_session(mem_conn, scope_key)
        return f"Cleared **{n}** session note(s). Long-term notes unchanged."

    if act.name == "set_trace":
        session["trace"] = act.value == "on"
        return f"**Brain trace** is now **{'on' if session['trace'] else 'off'}** (footer on assistant replies)."

    if act.name == "set_smart_route":
        if locked_no_smart_route:
            return "Smart routing is **locked off** for this server (`--no-smart-route`)."
        session["smart_route"] = act.value == "on"
        return (
            f"**Smart routing** is now **{'on' if session['smart_route'] else 'off'}** "
            "(off = plain chat + FAQ context injection + slash shortcuts only)."
        )

    if act.name == "set_rag":
        if rag_chunks_base is None:
            return "FAQ/RAG corpus is **not loaded** on this deployment; nothing to toggle."
        session["rag"] = act.value == "on"
        return (
            f"**FAQ/RAG excerpts in prompts** are now **{'on' if session['rag'] else 'off'}**."
        )

    if act.name == "reset_reply_style":
        session["verbosity"] = "normal"
        session["reply_format"] = "prose"
        session["faq_grounding"] = "normal"
        session["audience"] = "normal"
        session["answer_lead"] = "normal"
        session["step_style"] = "normal"
        session["confidence_tone"] = "normal"
        session["followup_close"] = "normal"
        session["exposition_order"] = "normal"
        session["example_density"] = "normal"
        session["comparison_frame"] = "normal"
        session["register_tone"] = "normal"
        session["code_block_style"] = "normal"
        session["analogy_use"] = "normal"
        session["acronym_style"] = "normal"
        session["clarify_first"] = "normal"
        session["speculation"] = "normal"
        session["math_detail"] = "normal"
        session["output_format"] = "normal"
        session["risk_posture"] = "normal"
        session["actionability"] = "normal"
        session["quote_style"] = "normal"
        session["table_style"] = "normal"
        session["emoji_style"] = "normal"
        session["section_headings"] = "normal"
        session["term_emphasis"] = "normal"
        session["counterpoint_tone"] = "normal"
        return (
            "**Reply style reset:** normal length, prose, balanced FAQ grounding, general audience, "
            "default opening, default steps, normal confidence tone, default follow-ups, default concept order, "
            "default examples, default comparisons, default register, default code blocks, default analogies, "
            "default acronyms, default clarify mode, default speculation, default math detail, default output format, "
            "default risk posture, default actionability, default quote style, default tables, default emoji, "
            "default section headings, default term emphasis, default counterpoints."
        )

    if act.name == "set_verbosity":
        v = (act.value or "normal").lower()
        if v not in ("brief", "normal", "detailed"):
            v = "normal"
        session["verbosity"] = v
        return f"**Reply length** is now **{v}** (applies to assistant chat replies)."

    if act.name == "set_reply_format":
        f = (act.value or "prose").lower()
        if f not in ("prose", "bullets"):
            f = "prose"
        session["reply_format"] = f
        return f"**List formatting** is now **{f}** (how the assistant structures multi-point answers)."

    if act.name == "set_faq_grounding":
        mode = (act.value or "normal").lower()
        if mode not in ("strict", "normal", "relaxed"):
            mode = "normal"
        session["faq_grounding"] = mode
        extra = ""
        if rag_chunks_base is None or not session.get("rag", True):
            extra = (
                "\n\n**Note:** FAQ excerpt injection is currently **off** in this chat session "
                "(or no FAQ corpus loaded). Grounding hints apply whenever FAQ snippets are present."
            )
        return f"**FAQ grounding** is now **{mode}**.{extra}"

    if act.name == "set_audience":
        aud = (act.value or "normal").lower()
        if aud not in ("simple", "normal", "technical"):
            aud = "normal"
        session["audience"] = aud
        label = {"simple": "beginner-friendly", "normal": "general", "technical": "technical"}.get(aud, aud)
        return f"**Audience** is now **{label}** (how deep or jargon-heavy explanations should feel)."

    if act.name == "set_answer_lead":
        lead = (act.value or "normal").lower()
        if lead not in ("tldr_first", "direct", "normal"):
            lead = "normal"
        session["answer_lead"] = lead
        human = {"tldr_first": "TL;DR first line", "direct": "straight in (no TL;DR line)", "normal": "default"}.get(
            lead, lead
        )
        return f"**Answer opening** is now **{human}**."

    if act.name == "set_step_style":
        st = (act.value or "normal").lower()
        if st not in ("numbered", "continuous", "normal"):
            st = "normal"
        session["step_style"] = st
        human = {
            "numbered": "numbered steps when explaining procedures",
            "continuous": "continuous prose (avoid numbered step lists)",
            "normal": "default",
        }.get(st, st)
        return f"**Procedure layout** is now **{human}**."

    if act.name == "set_confidence_tone":
        ct = (act.value or "normal").lower()
        if ct not in ("transparent", "assertive", "normal"):
            ct = "normal"
        session["confidence_tone"] = ct
        human = {
            "transparent": "flag limits and assumptions",
            "assertive": "decisive, minimal hedging",
            "normal": "default",
        }.get(ct, ct)
        return f"**Confidence tone** is now **{human}**."

    if act.name == "set_followup_close":
        fu = (act.value or "normal").lower()
        if fu not in ("suggest", "minimal", "normal"):
            fu = "normal"
        session["followup_close"] = fu
        human = {
            "suggest": "offer brief next steps / follow-ups when useful",
            "minimal": "no rhetorical closing questions",
            "normal": "default",
        }.get(fu, fu)
        return f"**Follow-up closing** is now **{human}**."

    if act.name == "set_exposition_order":
        eo = (act.value or "normal").lower()
        if eo not in ("definitions_first", "intuition_first", "normal"):
            eo = "normal"
        session["exposition_order"] = eo
        human = {
            "definitions_first": "definitions and terms before intuition",
            "intuition_first": "big-picture intuition before formal detail",
            "normal": "default",
        }.get(eo, eo)
        return f"**Concept order** is now **{human}**."

    if act.name == "set_example_density":
        ed = (act.value or "normal").lower()
        if ed not in ("rich", "sparse", "normal"):
            ed = "normal"
        session["example_density"] = ed
        human = {
            "rich": "include concrete examples when they help",
            "sparse": "minimal examples unless asked",
            "normal": "default",
        }.get(ed, ed)
        return f"**Examples** preference is now **{human}**."

    if act.name == "set_comparison_frame":
        cf = (act.value or "normal").lower()
        if cf not in ("pros_cons", "narrative", "normal"):
            cf = "normal"
        session["comparison_frame"] = cf
        human = {
            "pros_cons": "explicit Pros / Cons sections for trade-offs",
            "narrative": "flowing prose comparisons (no rigid Pros/Cons headings)",
            "normal": "default",
        }.get(cf, cf)
        return f"**Comparison layout** is now **{human}**."

    if act.name == "set_register_tone":
        rt = (act.value or "normal").lower()
        if rt not in ("formal", "casual", "normal"):
            rt = "normal"
        session["register_tone"] = rt
        human = {
            "formal": "professional / polished wording",
            "casual": "friendly conversational wording",
            "normal": "default",
        }.get(rt, rt)
        return f"**Register** is now **{human}**."

    if act.name == "set_code_block_style":
        cs = (act.value or "normal").lower()
        if cs not in ("fenced", "inline", "normal"):
            cs = "normal"
        session["code_block_style"] = cs
        human = {
            "fenced": "use ``` fenced blocks for multi-line code",
            "inline": "prefer inline `backticks`, avoid large fences",
            "normal": "default",
        }.get(cs, cs)
        return f"**Code markdown** is now **{human}**."

    if act.name == "set_analogy_use":
        au = (act.value or "normal").lower()
        if au not in ("prefer", "avoid", "normal"):
            au = "normal"
        session["analogy_use"] = au
        human = {
            "prefer": "use concise analogies when they clarify",
            "avoid": "literal wording; skip analogies and metaphors",
            "normal": "default",
        }.get(au, au)
        return f"**Analogy usage** is now **{human}**."

    if act.name == "set_acronym_style":
        ac = (act.value or "normal").lower()
        if ac not in ("spell_out", "terse", "normal"):
            ac = "normal"
        session["acronym_style"] = ac
        human = {
            "spell_out": "expand unfamiliar acronyms on first mention",
            "terse": "keep acronym forms without spelling them out first",
            "normal": "default",
        }.get(ac, ac)
        return f"**Acronym style** is now **{human}**."

    if act.name == "set_clarify_first":
        cf = (act.value or "normal").lower()
        if cf not in ("on", "off", "normal"):
            cf = "normal"
        session["clarify_first"] = cf
        human = {
            "on": "ask 1–3 targeted clarifying questions before answering when info is missing",
            "off": "answer immediately; do not ask clarifying questions first",
            "normal": "default",
        }.get(cf, cf)
        return f"**Clarify-first** is now **{human}**."

    if act.name == "set_speculation":
        sp = (act.value or "normal").lower()
        if sp not in ("strict", "creative", "normal"):
            sp = "normal"
        session["speculation"] = sp
        human = {
            "strict": "avoid guessing; stick to high-confidence statements",
            "creative": "brainstorm and speculate (label assumptions clearly)",
            "normal": "default",
        }.get(sp, sp)
        return f"**Speculation level** is now **{human}**."

    if act.name == "set_math_detail":
        md = (act.value or "normal").lower()
        if md not in ("show_work", "final_only", "normal"):
            md = "normal"
        session["math_detail"] = md
        human = {
            "show_work": "show intermediate steps/derivation when doing math-like reasoning",
            "final_only": "final results only (no derivation/steps)",
            "normal": "default",
        }.get(md, md)
        return f"**Math detail** is now **{human}**."

    if act.name == "set_output_format":
        of = (act.value or "normal").lower()
        if of not in ("json", "plain", "normal"):
            of = "normal"
        session["output_format"] = of
        human = {
            "json": "reply in a JSON-shaped object when possible",
            "plain": "plain text (no forced JSON structure)",
            "normal": "default",
        }.get(of, of)
        return f"**Output format** is now **{human}**."

    if act.name == "set_risk_posture":
        rp = (act.value or "normal").lower()
        if rp not in ("conservative", "pragmatic", "normal"):
            rp = "normal"
        session["risk_posture"] = rp
        human = {
            "conservative": "risk-averse / safety-first recommendations",
            "pragmatic": "practical, speed-oriented recommendations",
            "normal": "default",
        }.get(rp, rp)
        return f"**Risk posture** is now **{human}**."

    if act.name == "set_actionability":
        ac = (act.value or "normal").lower()
        if ac not in ("commands", "conceptual", "normal"):
            ac = "normal"
        session["actionability"] = ac
        human = {
            "commands": "include runnable commands/snippets when possible",
            "conceptual": "avoid commands; stay conceptual/high-level",
            "normal": "default",
        }.get(ac, ac)
        return f"**Actionability** is now **{human}**."

    if act.name == "set_quote_style":
        qs = (act.value or "normal").lower()
        if qs not in ("quote", "paraphrase", "normal"):
            qs = "normal"
        session["quote_style"] = qs
        human = {
            "quote": "prefer short direct quotes when relying on FAQ excerpts",
            "paraphrase": "paraphrase excerpts; avoid quoting",
            "normal": "default",
        }.get(qs, qs)
        return f"**Quote style** is now **{human}**."

    if act.name == "set_table_style":
        ts = (act.value or "normal").lower()
        if ts not in ("prefer", "avoid", "normal"):
            ts = "normal"
        session["table_style"] = ts
        human = {
            "prefer": "use markdown tables when presenting structured comparisons",
            "avoid": "avoid tables; use bullets/prose instead",
            "normal": "default",
        }.get(ts, ts)
        return f"**Tables** preference is now **{human}**."

    if act.name == "set_emoji_style":
        es = (act.value or "normal").lower()
        if es not in ("include", "avoid", "normal"):
            es = "normal"
        session["emoji_style"] = es
        human = {
            "include": "a few tasteful emoji are welcome when they aid scanning",
            "avoid": "no emoji unless the user uses them first",
            "normal": "default",
        }.get(es, es)
        return f"**Emoji style** is now **{human}**."

    if act.name == "set_section_headings":
        sh = (act.value or "normal").lower()
        if sh not in ("prefer", "avoid", "normal"):
            sh = "normal"
        session["section_headings"] = sh
        human = {
            "prefer": "use markdown ##/### headings to structure longer answers",
            "avoid": "avoid markdown heading lines; keep flowing paragraphs/lists",
            "normal": "default",
        }.get(sh, sh)
        return f"**Section headings** preference is now **{human}**."

    if act.name == "set_term_emphasis":
        te = (act.value or "normal").lower()
        if te not in ("highlight", "minimal", "normal"):
            te = "normal"
        session["term_emphasis"] = te
        human = {
            "highlight": "bold a few crucial terms/phrases for scanability",
            "minimal": "avoid decorative bold; use it sparingly",
            "normal": "default",
        }.get(te, te)
        return f"**Term emphasis** is now **{human}**."

    if act.name == "set_counterpoint_tone":
        cp = (act.value or "normal").lower()
        if cp not in ("challenge", "supportive", "normal"):
            cp = "normal"
        session["counterpoint_tone"] = cp
        human = {
            "challenge": "look for gaps; name risks and counterarguments respectfully",
            "supportive": "prioritize encouragement and constructive framing",
            "normal": "default",
        }.get(cp, cp)
        return f"**Counterpoint tone** is now **{human}**."

    return None


def _append_reply_style_hints(extras: list[str], session: dict[str, Any]) -> None:
    verbosity = str(session.get("verbosity") or "normal").lower()
    rformat = str(session.get("reply_format") or "prose").lower()
    if verbosity not in ("brief", "normal", "detailed"):
        verbosity = "normal"
    if rformat not in ("prose", "bullets"):
        rformat = "prose"
    lines: list[str] = []
    if verbosity == "brief":
        lines.append(
            "Keep replies concise (about a short paragraph or less) unless the user explicitly asks for depth."
        )
    elif verbosity == "detailed":
        lines.append("Prefer fuller, well-structured explanations when they help the user.")
    if rformat == "bullets":
        lines.append("When listing multiple points, use markdown bullet or numbered lists.")
    audience = str(session.get("audience") or "normal").lower()
    if audience not in ("simple", "normal", "technical"):
        audience = "normal"
    if audience == "simple":
        lines.append(
            "Assume the reader is new to the topic: define jargon when you use it, prefer plain language and small steps."
        )
    elif audience == "technical":
        lines.append(
            "Assume a technical reader: standard domain terms and shorthand are fine; prioritize precision over hand-holding."
        )
    lead = str(session.get("answer_lead") or "normal").lower()
    if lead not in ("tldr_first", "direct", "normal"):
        lead = "normal"
    if lead == "tldr_first":
        lines.append(
            "Start substantive answers with one short **TL;DR:** line (one sentence), then elaborate."
        )
    elif lead == "direct":
        lines.append(
            "Do not add a standalone TL;DR/summary prelude; answer immediately in-flow (still use lists if configured)."
        )
    steps = str(session.get("step_style") or "normal").lower()
    if steps not in ("numbered", "continuous", "normal"):
        steps = "normal"
    if steps == "numbered":
        lines.append(
            "When explaining procedures or multi-part how-tos, structure the answer with clear **numbered steps** "
            "(1. 2. 3.) and one action per step when practical."
        )
    elif steps == "continuous":
        lines.append(
            "Avoid numbered step lists; explain procedures as **connected paragraphs** unless the user explicitly "
            "asks for steps."
        )
    conf = str(session.get("confidence_tone") or "normal").lower()
    if conf not in ("transparent", "assertive", "normal"):
        conf = "normal"
    if conf == "transparent":
        lines.append(
            "Be explicit about uncertainty: say when you are guessing, label key assumptions, and avoid overstating "
            "facts you cannot support from the prompt or supplied excerpts."
        )
    elif conf == "assertive":
        lines.append(
            "Answer in a direct, confident tone: minimize throat-clearing and hedging unless a short disclaimer is "
            "truly necessary for safety or policy."
        )
    fu = str(session.get("followup_close") or "normal").lower()
    if fu not in ("suggest", "minimal", "normal"):
        fu = "normal"
    if fu == "suggest":
        lines.append(
            "When helpful, end with concise **optional next steps** or a short **follow-up invitation** "
            '(e.g., one line like "Want me to drill into X?" — optional, not repetitive).'
        )
    elif fu == "minimal":
        lines.append(
            "Avoid stock closers such as prompting whether the user needs anything else unless they explicitly invite it; "
            "finish crisply after the core answer."
        )
    expo = str(session.get("exposition_order") or "normal").lower()
    if expo not in ("definitions_first", "intuition_first", "normal"):
        expo = "normal"
    if expo == "definitions_first":
        lines.append(
            "Prefer stating **definitions and key terms upfront**, then intuition, analogies, and examples."
        )
    elif expo == "intuition_first":
        lines.append(
            "Prefer a short **motivation / big-picture intuition** section first, then formal definitions and details."
        )
    ex_density = str(session.get("example_density") or "normal").lower()
    if ex_density not in ("rich", "sparse", "normal"):
        ex_density = "normal"
    if ex_density == "rich":
        lines.append(
            "When it clarifies the answer, include at least one **short concrete example** or miniature scenario."
        )
    elif ex_density == "sparse":
        lines.append(
            "Unless the user explicitly requests an example, keep answers **example-free** (no illustrative stories)."
        )
    comp = str(session.get("comparison_frame") or "normal").lower()
    if comp not in ("pros_cons", "narrative", "normal"):
        comp = "normal"
    if comp == "pros_cons":
        lines.append(
            "For trade-offs or comparing options, use markdown subheadings **Pros** and **Cons** (short bullets under each)."
        )
    elif comp == "narrative":
        lines.append(
            "For trade-offs or comparing options, weave pros/cons into **continuous prose** rather than labeled sections."
        )
    reg = str(session.get("register_tone") or "normal").lower()
    if reg not in ("formal", "casual", "normal"):
        reg = "normal"
    if reg == "formal":
        lines.append(
            "Use a **polished professional register**: clear sentences, minimal slang/emoji unless the topic demands it."
        )
    elif reg == "casual":
        lines.append(
            "**Conversational register** is preferred: contractions and light phrasing are fine; sound like a helpful teammate."
        )
    cb = str(session.get("code_block_style") or "normal").lower()
    if cb not in ("fenced", "inline", "normal"):
        cb = "normal"
    if cb == "fenced":
        lines.append(
            "For multi-line commands or code, use **markdown fenced code blocks** with a language hint when recognizable."
        )
    elif cb == "inline":
        lines.append(
            "Prefer **inline backticks** for short snippets; **avoid triple-backtick fences** unless the user pastes a block."
        )
    an = str(session.get("analogy_use") or "normal").lower()
    if an not in ("prefer", "avoid", "normal"):
        an = "normal"
    if an == "prefer":
        lines.append(
            "When stuck on an abstract concept, optionally add **one tight analogy/metaphor** (label it plainly; keep it respectful)."
        )
    elif an == "avoid":
        lines.append(
            "Keep explanations **literal and direct**: do **not** use analogies, metaphors, or cute comparisons."
        )
    acr = str(session.get("acronym_style") or "normal").lower()
    if acr not in ("spell_out", "terse", "normal"):
        acr = "normal"
    if acr == "spell_out":
        lines.append(
            'On **first substantive mention** of a non-obvious acronym/title-case initialism (e.g. API, SLA), '
            'write the **expanded form once** (`Long Form (ACRONYM)`), then use the acronym afterwards.'
        )
    elif acr == "terse":
        lines.append(
            "Assume the reader is acronym-literate: **reuse acronyms** as written without mandatory expansion."
        )

    clarify = str(session.get("clarify_first") or "normal").lower()
    if clarify not in ("on", "off", "normal"):
        clarify = "normal"
    if clarify == "on":
        lines.append(
            "If the request is underspecified, ask **1–3 short clarifying questions first** (only the minimum needed), "
            "then wait for the user's answers before giving a full solution."
        )
    elif clarify == "off":
        lines.append(
            "Do not pause to ask clarifying questions first; provide the best answer immediately and note assumptions briefly."
        )

    spec = str(session.get("speculation") or "normal").lower()
    if spec not in ("strict", "creative", "normal"):
        spec = "normal"
    if spec == "strict":
        lines.append(
            "Avoid speculation: prefer high-confidence statements, and say when something is unknown or not supported by the prompt."
        )
    elif spec == "creative":
        lines.append(
            "Brainstorming is allowed: you may propose speculative ideas, but label assumptions and uncertainty clearly."
        )

    md = str(session.get("math_detail") or "normal").lower()
    if md not in ("show_work", "final_only", "normal"):
        md = "normal"
    if md == "show_work":
        lines.append(
            "When the user asks for math/derivations, show concise intermediate steps and explain symbols briefly."
        )
    elif md == "final_only":
        lines.append(
            "When the user asks for math/derivations, give the final result directly (no intermediate derivation)."
        )

    of = str(session.get("output_format") or "normal").lower()
    if of not in ("json", "plain", "normal"):
        of = "normal"
    if of == "json":
        lines.append(
            "When appropriate, format the answer as a single JSON object with stable keys; avoid extra prose outside the JSON."
        )
    elif of == "plain":
        lines.append("Do not force JSON or rigid schemas; answer in normal plain text.")

    rp = str(session.get("risk_posture") or "normal").lower()
    if rp not in ("conservative", "pragmatic", "normal"):
        rp = "normal"
    if rp == "conservative":
        lines.append(
            "Prefer safer, low-risk recommendations; call out risks and choose options that minimize downside."
        )
    elif rp == "pragmatic":
        lines.append(
            "Prefer practical, time-efficient recommendations; avoid over-engineering unless clearly needed."
        )

    actz = str(session.get("actionability") or "normal").lower()
    if actz not in ("commands", "conceptual", "normal"):
        actz = "normal"
    if actz == "commands":
        lines.append(
            "When proposing a solution, include runnable commands/snippets/checklists where appropriate."
        )
    elif actz == "conceptual":
        lines.append(
            "Avoid command dumps; focus on concepts, rationale, and decision points."
        )

    qs = str(session.get("quote_style") or "normal").lower()
    if qs not in ("quote", "paraphrase", "normal"):
        qs = "normal"
    if qs == "quote":
        lines.append(
            "When you rely on an injected **[FAQ excerpt N]**, include a short verbatim quote (a sentence or clause) "
            "before paraphrasing."
        )
    elif qs == "paraphrase":
        lines.append(
            "Prefer paraphrasing FAQ excerpts; avoid quoting unless the user asks for exact wording."
        )

    ts = str(session.get("table_style") or "normal").lower()
    if ts not in ("prefer", "avoid", "normal"):
        ts = "normal"
    if ts == "prefer":
        lines.append(
            "When comparing several options, prefer a **markdown table** if it makes the structure clearer."
        )
    elif ts == "avoid":
        lines.append(
            "Avoid markdown tables; use bullets or short sections instead."
        )

    es = str(session.get("emoji_style") or "normal").lower()
    if es not in ("include", "avoid", "normal"):
        es = "normal"
    if es == "include":
        lines.append(
            "You may use a few tasteful emoji in replies when they help readability (keep it sparse and professional)."
        )
    elif es == "avoid":
        lines.append("Do not use emoji in replies unless the user explicitly uses emoji first.")

    sh = str(session.get("section_headings") or "normal").lower()
    if sh not in ("prefer", "avoid", "normal"):
        sh = "normal"
    if sh == "prefer":
        lines.append(
            "For multi-part answers, organize with short **markdown headings** (## / ###) before each major block."
        )
    elif sh == "avoid":
        lines.append(
            "Avoid leading lines that look like markdown headings (no `#` / `##` title lines); use bold inline labels or paragraphs instead."
        )

    te = str(session.get("term_emphasis") or "normal").lower()
    if te not in ("highlight", "minimal", "normal"):
        te = "normal"
    if te == "highlight":
        lines.append(
            "Use **bold** on a handful of key terms or short phrases (not whole sentences) to help the reader scan."
        )
    elif te == "minimal":
        lines.append(
            "Keep inline **bold** rare; prefer plain text unless emphasis is truly needed for clarity."
        )

    cp = str(session.get("counterpoint_tone") or "normal").lower()
    if cp not in ("challenge", "supportive", "normal"):
        cp = "normal"
    if cp == "challenge":
        lines.append(
            "Briefly stress-test the user's plan: note plausible failure modes, missing constraints, or stronger "
            "alternatives—stay respectful and specific."
        )
    elif cp == "supportive":
        lines.append(
            "Lean supportive: acknowledge effort, frame improvements as next steps, and avoid needless harsh critique."
        )

    g = str(session.get("faq_grounding") or "normal").lower()
    if g not in ("strict", "normal", "relaxed"):
        g = "normal"
    if g == "strict":
        lines.append(
            "FAQ grounding (strict): Treat product/process/policy claims as supported only when clearly stated in "
            "the FAQ excerpts provided in this turn. If not stated there, say you are unsure or that it is outside "
            "the provided FAQ. When you rely on an excerpt, cite it as **[FAQ excerpt N]** matching the numbered "
            "excerpt headings you were given."
        )
    elif g == "relaxed":
        lines.append(
            "FAQ grounding (relaxed): Prefer the supplied FAQ excerpts for product/support specifics, but you may add "
            "brief general-knowledge context if you clearly separate it from anything implied by FAQ text."
        )
    # "normal": default product behavior --- rely on FAQ block wording without duplicating instructions.
    if lines:
        extras.append(
            "Preferred reply style for this chat session:\n" + "\n".join(f"- {ln}" for ln in lines)
        )


def handle_slash(
    msg: str,
    *,
    lm: LoadedLM | None,
    mem_conn: sqlite3.Connection | None,
    scope_key: str,
    encoder: TinyModelRuntime | None,
    rag_chunks: list[str] | None,
    rag_top_k: int,
    task_max_new_tokens: int,
    seed: int,
    meta_mid: str,
    meta_encoder: str,
    meta_mem_db: str | None,
    meta_rag_path: str | None,
) -> str | None:
    if not msg.startswith("/"):
        return None
    parts = msg.split(maxsplit=1)
    cmd = parts[0].lower()
    rest = parts[1].strip() if len(parts) > 1 else ""

    if cmd == "/help":
        return HELP_TEXT

    if cmd == "/status":
        return _format_status(
            meta_mid=meta_mid,
            meta_encoder=meta_encoder,
            meta_rag_path=meta_rag_path,
            rag_chunks=rag_chunks,
            meta_mem_db=meta_mem_db,
            scope_key=scope_key,
        )

    if cmd == "/classify":
        if not encoder:
            return "Classifier off. Drop `--lm-only` / `--no-encoder` or pass `--encoder`."
        if not rest:
            return "Usage: `/classify <text>`"
        return _classifier_result_markdown(encoder.classify([rest])[0])

    if cmd in ("/web", "/search_web"):
        g_key, g_cx, g_num, g_safe = read_google_cse_settings()
        if not g_key or not g_cx:
            return (
                "Web search needs **`GOOGLE_CSE_API_KEY`** (secret) and **`GOOGLE_CSE_CX`** (search engine id) "
                "in Space settings or local `.env`. See `/status`."
            )
        if not rest:
            return "Usage: `/web <search query>`"
        try:
            hits = google_cse_search(rest, api_key=g_key, cx=g_cx, num=g_num, safe=g_safe)
        except Exception as e:
            return f"### Web search error\n{_clip(str(e), 1200)}"
        return format_cse_hits_markdown(hits, for_chat=False)

    if cmd == "/retrieve":
        if not encoder or not rag_chunks:
            return "Retrieve needs encoder + FAQ corpus (default on unless `--lm-only` / `--no-rag` / `--no-encoder`)."
        if not rest:
            return "Usage: `/retrieve <query>`"
        hr = hybrid_retrieve(encoder, rest, rag_chunks, top_k=rag_top_k)
        if not hr:
            return "(No chunks.)"
        out = ["### Retrieve (hybrid)\n"]
        for i, (sc, _idx, txt) in enumerate(hr, 1):
            out.append(f"**#{i}** score={sc:.4f}\n{_clip(txt, 700)}\n")
        return "\n".join(out)

    if cmd == "/similarity":
        if not encoder:
            return "Encoder off. Drop `--lm-only` / `--no-encoder`."
        if "|||" not in rest:
            return "Usage: `/similarity text A ||| text B`"
        try:
            ta, tb = _parse_two_segments(rest)
        except ValueError as e:
            return str(e)
        score = encoder.similarity(ta, tb)
        return (
            f"**Similarity:** {score:.4f}\n\n**A:** {_clip(ta, 480)}\n\n**B:** {_clip(tb, 480)}"
        )

    if cmd in ("/embedding", "/embed"):
        if not encoder:
            return "Encoder off. Drop `--lm-only` / `--no-encoder`."
        if not rest:
            return f"Usage: `{cmd} <text>`"
        return _embedding_summary_markdown(encoder, rest)

    if cmd == "/nearest":
        if not encoder:
            return "Encoder off. Drop `--lm-only` / `--no-encoder`."
        if "|||" not in rest:
            return "Usage: `/nearest query ||| cand1 ||| cand2 ...`"
        try:
            qn, cands = _parse_nearest_blob(rest)
        except ValueError as e:
            return str(e)
        k = max(1, min(rag_top_k, len(cands)))
        return _nearest_markdown(encoder, qn, cands, top_k=k)

    if cmd in ("/summarize", "/reformulate", "/grounded"):
        if lm is None:
            return "Generative model not loaded."
        if cmd == "/grounded":
            if "|||" not in rest:
                return "Usage: `/grounded <question> ||| <context>`"
            qpart, _, ctxpart = rest.partition("|||")
            question, context = qpart.strip(), ctxpart.strip()
            if not question or not context:
                return "Both question and context required (use `|||`)."
            try:
                up = build_user_prompt("grounded", question, context=context)
            except ValueError as e:
                return str(e)
        else:
            if not rest:
                return f"Usage: `{cmd} <text>`"
            task = "summarize" if cmd == "/summarize" else "reformulate"
            up = build_user_prompt(task, rest)
        prompt = format_for_model(lm.tokenizer, up)
        out, _np, _nn, sec = generate_completion(
            lm,
            prompt,
            max_new_tokens=task_max_new_tokens,
            seed=seed,
            do_sample=True,
        )
        tag = cmd.lstrip("/")
        return f"**/{tag}** ({sec:.2f}s)\n\n{out or '(empty)'}"

    mem_cmds = {"/remember", "/session", "/memories", "/clear-session"}
    if cmd in mem_cmds and mem_conn is None:
        return "Memory off. Drop `--no-memory` or pass `--memory-db` (default DB is used when memory is on)."

    if cmd == "/remember":
        if not rest:
            return "Usage: `/remember <text>`"
        put(mem_conn, scope_key=scope_key, kind="long_term", content=rest)  # type: ignore[arg-type]
        return "Saved to **long-term** memory for this scope."
    if cmd == "/session":
        if not rest:
            return "Usage: `/session <text>`"
        put(mem_conn, scope_key=scope_key, kind="session", content=rest)  # type: ignore[arg-type]
        return "Saved to **session** memory for this scope."
    if cmd == "/memories":
        items = list_for_scope(mem_conn, scope_key)  # type: ignore[arg-type]
        if not items:
            return "(No memory items for this scope.)"
        lines = [f"- **{it.kind}** · {_clip(it.content, 320)}" for it in items[:24]]
        extra = f"\n\n… {len(items) - 24} more" if len(items) > 24 else ""
        return "Stored notes:\n" + "\n".join(lines) + extra
    if cmd == "/clear-session":
        n = clear_session(mem_conn, scope_key)  # type: ignore[arg-type]
        return f"Cleared **{n}** session item(s). Long-term notes are unchanged."

    return None


def _resolve_rag_path(arg: str | None, no_rag: bool) -> Path | None:
    if no_rag:
        return None
    if arg:
        p = Path(arg)
        if not p.is_file():
            p = _REPO / arg
        return p if p.is_file() else None
    default = _REPO / "texts" / "rag_faq_corpus.md"
    return default if default.is_file() else None


def _encoder_device(lm_device: str, explicit: str) -> str:
    if explicit != "auto":
        return explicit
    return "cpu" if lm_device == "cuda" else lm_device


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--model", type=str, default=None, help="HF generative model id.")
    p.add_argument("--smoke", action="store_true", help=f"Tiny generative model {SMOKE_MODEL_ID!r}.")
    p.add_argument("--device", default="auto", help="auto | cpu | cuda | mps")
    p.add_argument("--host", type=str, default="127.0.0.1")
    p.add_argument("--port", type=int, default=7860)
    p.add_argument("--share", action="store_true", help="Gradio share=True (tunnel).")
    p.add_argument("--max-new-tokens", type=int, default=512)
    p.add_argument(
        "--task-max-new-tokens",
        type=int,
        default=256,
        help="Max new tokens for /summarize, /reformulate, /grounded.",
    )
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--system-prompt", type=str, default="", help="Override system prompt.")

    p.add_argument("--lm-only", action="store_true", help="Chat-only: no encoder, RAG, or SQLite memory.")
    p.add_argument(
        "--no-encoder",
        action="store_true",
        help="Disable TinyModel classifier and FAQ retrieval.",
    )
    p.add_argument("--no-memory", action="store_true", help="Disable Horizon 3 SQLite memory.")
    p.add_argument(
        "--brain",
        action="store_true",
        help="(Optional) Log which default encoder path was resolved; on by default unless --lm-only.",
    )
    p.add_argument(
        "--encoder",
        type=str,
        default=None,
        help="Classifier checkpoint dir or Hub id (overrides --brain default when both set).",
    )
    p.add_argument(
        "--encoder-device",
        type=str,
        default="auto",
        choices=("auto", "cpu", "cuda", "mps"),
        help="Device for TinyModelRuntime (default auto: cpu if generative model is on CUDA).",
    )
    p.add_argument("--no-rag", action="store_true", help="Disable FAQ retrieval even with an encoder.")
    p.add_argument("--rag-corpus", type=str, default=None, help="FAQ markdown path; default texts/rag_faq_corpus.md.")
    p.add_argument("--rag-top-k", type=int, default=2)

    p.add_argument(
        "--memory-db",
        type=str,
        default=None,
        help=f"SQLite path (default when memory on: {DEFAULT_MEMORY_DB}).",
    )
    p.add_argument(
        "--memory-scope",
        type=str,
        default="ub-chat-default",
        help="scope_key for stored memory (tenant/session id).",
    )
    p.add_argument("--no-trace", action="store_true", help="Do not append Brain trace line to assistant replies.")
    p.add_argument(
        "--no-smart-route",
        action="store_true",
        help="Disable NL intent routing (plain chat only; slash commands still work).",
    )
    p.add_argument(
        "--no-auto-web",
        action="store_true",
        help="Disable chat→web_search heuristic (only explicit router web_search or /web uses Google CSE).",
    )
    p.add_argument(
        "--router-max-new-tokens",
        type=int,
        default=192,
        help="Max new tokens for the routing JSON completion.",
    )

    return p.parse_args()


def main() -> None:
    args = parse_args()
    _load_dotenv_if_present(_REPO)
    if os.environ.get("NO_AUTO_WEB", "").strip().lower() in ("1", "true", "yes", "on"):
        args.no_auto_web = True
    _gk, _gc, _, _ = read_google_cse_settings()
    cse_on = bool(_gk and _gc)
    _ensure_gradio_can_reach_localhost()
    try:
        import gradio as gr
    except ImportError as e:
        print("Install Gradio: pip install 'gradio>=5.49,<6'", file=sys.stderr)
        raise SystemExit(1) from e

    _patch_gradio_localhost_probe()

    # Gradio 5.x warns whenever allow_tags is not True (including explicit False); noise only.
    warnings.filterwarnings(
        "ignore",
        message=r".*allow_tags.*gr\.Chatbot.*",
        category=DeprecationWarning,
    )

    if args.smoke:
        mid = SMOKE_MODEL_ID
    elif args.model:
        mid = args.model
    else:
        mid = os.environ.get("HORIZON2_MODEL", DEFAULT_INSTRUCTION_MODEL)
    dev = pick_device(args.device)
    system_text = (args.system_prompt or "").strip() or DEFAULT_CHAT_SYSTEM

    encoder: TinyModelRuntime | None = None
    rag_chunks: list[str] | None = None
    encoder_id: str | None = None

    if args.lm_only or args.no_encoder:
        if args.encoder:
            print("Note: --encoder ignored with --lm-only or --no-encoder.", file=sys.stderr)
        encoder_id = None
    elif args.encoder:
        encoder_id = _pick_model(args.encoder)
    else:
        encoder_id = _pick_model(None)
        if args.brain:
            print(f"--brain: encoder {encoder_id!r}", flush=True)
        else:
            print(f"Encoder (default): {encoder_id!r}", flush=True)

    rag_path = _resolve_rag_path(args.rag_corpus, args.no_rag or args.lm_only)
    if encoder_id:
        enc_dev = _encoder_device(dev, args.encoder_device)
        print(f"Loading encoder {encoder_id!r} on {enc_dev!r} ...", flush=True)
        encoder = TinyModelRuntime(encoder_id, device=enc_dev, max_length=128)
    if encoder and rag_path:
        rag_chunks = load_chunks(rag_path)
        print(f"RAG: {len(rag_chunks)} chunks from {rag_path}", flush=True)
    elif rag_path and not encoder:
        print("Note: FAQ corpus not loaded without encoder.", file=sys.stderr)

    mem_path: str | None = None
    if not args.lm_only and not args.no_memory:
        mem_path = args.memory_db or DEFAULT_MEMORY_DB

    mem_conn: sqlite3.Connection | None = None
    if mem_path:
        mem_conn = connect(mem_path, check_same_thread=False)
        init_schema(mem_conn)
        print(f"Memory: scope={args.memory_scope!r} db={mem_path!r}", flush=True)

    if cse_on:
        print("Google CSE web search: configured (`/web` + smart-route `web_search`)", flush=True)

    meta_encoder = encoder_id or "off"
    meta_rag = str(rag_path.resolve()) if rag_path else None
    meta_mem = mem_path

    print(f"Loading generative model {mid!r} on {dev!r} ...", flush=True)
    lm = load_causal_lm(mid, dev)
    turn_counter = {"n": 0}
    initial_ub_session = {
        "trace": not args.no_trace
        and (
            encoder is not None
            or mem_conn is not None
            or (rag_chunks is not None)
            or cse_on
        ),
        "smart_route": not args.no_smart_route,
        "rag": rag_chunks is not None,
        "scope_key": args.memory_scope,
        "verbosity": "normal",
        "reply_format": "prose",
        "faq_grounding": "normal",
        "audience": "normal",
        "answer_lead": "normal",
        "step_style": "normal",
        "confidence_tone": "normal",
        "followup_close": "normal",
        "exposition_order": "normal",
        "example_density": "normal",
        "comparison_frame": "normal",
        "register_tone": "normal",
        "code_block_style": "normal",
        "analogy_use": "normal",
        "acronym_style": "normal",
        "clarify_first": "normal",
        "speculation": "normal",
        "math_detail": "normal",
        "output_format": "normal",
        "risk_posture": "normal",
        "actionability": "normal",
        "quote_style": "normal",
        "table_style": "normal",
        "emoji_style": "normal",
        "section_headings": "normal",
        "term_emphasis": "normal",
        "counterpoint_tone": "normal",
    }

    def respond(
        message: str,
        history: list[dict],
        ub_session: dict[str, Any],
    ) -> tuple[str, list[dict], dict[str, Any]]:
        msg = (message or "").strip()
        hist = list(history or [])
        if not msg:
            return "", hist, ub_session

        turn_counter["n"] += 1
        seed = (args.seed + turn_counter["n"]) % (2**31)

        cur_scope = str(ub_session.get("scope_key") or args.memory_scope)

        slash_out = handle_slash(
            msg,
            lm=lm,
            mem_conn=mem_conn,
            scope_key=cur_scope,
            encoder=encoder,
            rag_chunks=rag_chunks,
            rag_top_k=args.rag_top_k,
            task_max_new_tokens=args.task_max_new_tokens,
            seed=seed,
            meta_mid=mid,
            meta_encoder=meta_encoder,
            meta_mem_db=meta_mem,
            meta_rag_path=meta_rag,
        )
        if slash_out is not None:
            hist.append({"role": "user", "content": msg})
            hist.append({"role": "assistant", "content": slash_out})
            return "", hist, ub_session

        nl_out = handle_nl_control(
            msg,
            ub_session,
            mem_conn=mem_conn,
            scope_key=cur_scope,
            rag_chunks_base=rag_chunks,
            locked_no_smart_route=args.no_smart_route,
        )
        if nl_out is not None:
            hist.append({"role": "user", "content": msg})
            hist.append({"role": "assistant", "content": nl_out})
            return "", hist, ub_session

        effective_rag = (
            rag_chunks if rag_chunks is not None and ub_session.get("rag") else None
        )
        use_smart = bool(ub_session.get("smart_route")) and not args.no_smart_route

        chat_line = msg
        web_block = ""
        web_trace = ""
        if use_smart:
            try:
                route = infer_route(
                    lm,
                    msg,
                    seed=seed,
                    max_new_tokens=args.router_max_new_tokens,
                )
            except Exception:
                route = {"intent": "chat", "text": msg, "question": "", "context": ""}

            g_key, g_cx, _, _ = read_google_cse_settings()
            web_from_auto = False
            if (
                not args.no_auto_web
                and route["intent"] == "chat"
                and g_key
                and g_cx
                and heuristic_suggests_web_search(msg)
            ):
                route = {
                    "intent": "web_search",
                    "text": msg,
                    "question": "",
                    "context": "",
                }
                web_from_auto = True

            if route["intent"] == "web_search":
                g_key, g_cx, g_num, g_safe = read_google_cse_settings()
                q_web = (route["text"] or msg).strip()
                _as = "+auto" if web_from_auto else ""
                web_trace = f"web:CSE:cfg{_as}"
                if g_key and g_cx and q_web:
                    try:
                        hits = google_cse_search(
                            q_web,
                            api_key=g_key,
                            cx=g_cx,
                            num=g_num,
                            safe=g_safe,
                        )
                        web_block = format_cse_hits_markdown(hits, for_chat=True)
                        web_trace = f"web:CSE:{len(hits)}{_as}"
                    except Exception as ex:
                        web_block = (
                            f"(Google web search failed: {_clip(str(ex), 500)})\n\n"
                            "Answer from general knowledge where appropriate; do not invent URLs or page titles."
                        )
                        web_trace = f"web:CSE:err{_as}"
                elif not q_web:
                    web_block = "(Empty web search query. Ask again with a concrete search topic.)"
                    web_trace = f"web:CSE:empty{_as}"
                else:
                    web_block = (
                        "(Web search is not configured: set **GOOGLE_CSE_API_KEY** and **GOOGLE_CSE_CX** "
                        "in Hugging Face Space secrets/variables or local `.env`. See `/status`.)"
                    )
                route = {"intent": "chat", "text": msg, "question": "", "context": ""}

            if route["intent"] != "chat":
                tool_reply = run_routed_tool(
                    route,
                    msg=msg,
                    lm=lm,
                    mem_conn=mem_conn,
                    scope_key=cur_scope,
                    encoder=encoder,
                    rag_chunks=effective_rag,
                    rag_top_k=args.rag_top_k,
                    task_max_new_tokens=args.task_max_new_tokens,
                    seed=(seed + 11) % (2**31),
                    meta_mid=mid,
                    meta_encoder=meta_encoder,
                    meta_mem_db=meta_mem,
                    meta_rag_path=meta_rag,
                ).strip()
                if tool_reply:
                    foot = f"\n\n---\n*Routed intent:* `{route['intent']}`"
                    hist.append({"role": "user", "content": msg})
                    hist.append({"role": "assistant", "content": tool_reply + foot})
                    return "", hist, ub_session

            chat_line = route["text"] or msg

        sig_overrides, sig_extras, sig_trace_tags = analyze_embedded_prompt_signals(msg)
        eff_session = dict(ub_session)
        eff_session.update(sig_overrides)
        trace: list[str] = []
        prompt_sig_active = bool(sig_overrides or sig_extras or sig_trace_tags)
        if prompt_sig_active:
            bits = [f"{k}={v}" for k, v in sorted(sig_overrides.items())]
            bits.extend(sig_trace_tags)
            trace.append("prompt_signals:" + "+".join(bits))
        extras: list[str] = []
        _append_reply_style_hints(extras, eff_session)
        for para in sig_extras:
            extras.append(para)
        if web_trace:
            trace.append(web_trace)

        if encoder:
            probs = encoder.classify([chat_line])[0]
            top_lab = max(probs, key=probs.get)
            top_p = probs[top_lab]
            trace.append(f"classify:{top_lab}({top_p:.2f})")
            extras.append(
                f"Encoder routing hint: the line most resembles label {top_lab!r} "
                f"(winner probability {top_p:.2f}). Use as soft context only."
            )

        rag_block = ""
        if encoder and effective_rag:
            hr = hybrid_retrieve(encoder, chat_line, effective_rag, top_k=args.rag_top_k)
            if hr:
                trace.append(f"RAG:{len(hr)}chunk(s)")
                pieces = []
                for i, (_sc, _idx, txt) in enumerate(hr):
                    pieces.append(f"[FAQ excerpt {i + 1}]\n{_clip(txt, 900)}")
                rag_block = "\n\n".join(pieces)
                extras.append(
                    "Relevant FAQ excerpts (may be incomplete). "
                    "Ground factual claims in them when they apply; do not invent policy."
                    f"\n\n{rag_block}"
                )

        if web_block:
            extras.append(web_block)

        if mem_conn:
            items = list_for_scope(mem_conn, cur_scope)
            if items:
                trace.append(f"mem:{len(items)}item(s)")
                mem_lines = []
                for it in items[:10]:
                    mem_lines.append(f"- ({it.kind}) {_clip(it.content, 240)}")
                extras.append(
                    "User-visible stored notes for this chat scope (from /remember and /session):\n"
                    + "\n".join(mem_lines)
                )

        extra_system = "\n\n".join(extras) if extras else ""
        if extra_system:
            extra_system = "\n\n---\n" + extra_system

        eff_system = system_text + extra_system
        messages: list[dict[str, str]] = [{"role": "system", "content": eff_system}]
        messages.extend(hist)
        messages.append({"role": "user", "content": chat_line})

        seed_chat = (seed + 97) % (2**31)
        reply, _, _, _ = generate_chat_reply(
            lm,
            messages,
            max_new_tokens=args.max_new_tokens,
            seed=seed_chat,
            do_sample=True,
        )
        out = reply or "(empty generation)"
        show_trace_footer = (
            (not args.no_trace)
            and bool(ub_session.get("trace"))
            and (
                encoder is not None
                or mem_conn is not None
                or effective_rag is not None
                or bool(web_trace)
                or prompt_sig_active
            )
        )
        if show_trace_footer and trace:
            out += "\n\n---\n*Brain trace:* " + " · ".join(trace)

        hist.append({"role": "user", "content": msg})
        hist.append({"role": "assistant", "content": out})
        return "", hist, ub_session

    brain_bits = []
    if encoder:
        brain_bits.append("encoder")
    if rag_chunks:
        brain_bits.append("RAG")
    if mem_conn:
        brain_bits.append("memory")
    if cse_on:
        brain_bits.append("Google CSE")
    brain_label = "+".join(brain_bits) if brain_bits else "LM only"

    _css = """
    /* Space UX: keep the input compact and predictable. */
    #ub_input textarea { height: 120px !important; }
    """
    with gr.Blocks(title="Universal Brain (chat prototype)", css=_css) as demo:
        chat = gr.Chatbot(type="messages", height=260, label="Conversation", allow_tags=False)
        ub_state = gr.State(initial_ub_session)
        with gr.Row():
            inp = gr.Textbox(
                lines=4,
                max_lines=8,
                show_label=False,
                placeholder="Ask in plain language, or use /help …",
                scale=9,
                elem_id="ub_input",
            )
            go = gr.Button("Send", variant="primary", scale=1)
        gr.ClearButton([chat, inp])
        gr.Markdown(
            f"### Universal Brain — chat prototype\n\n"
            f"**Generative:** `{mid}` ({lm.device}) · **Brain layers:** {brain_label}\n\n"
            f"Use **Conversation** above, type a message, then **Send** (or Enter). **Clear** resets the on-screen chat only.\n\n"
            f"{GRADIO_INSTRUCTIONS_MARKDOWN}"
        )

        def _submit(
            m: str,
            h: list[dict],
            s: dict[str, Any],
        ) -> tuple[str, list[dict], dict[str, Any]]:
            return respond(m, h, s)

        go.click(
            _submit,
            [inp, chat, ub_state],
            [inp, chat, ub_state],
            api_name="chat",
            api_description="Universal Brain chat endpoint (routing + optional RAG + memory + classifier context).",
        )
        inp.submit(_submit, [inp, chat, ub_state], [inp, chat, ub_state])

    demo.queue(default_concurrency_limit=2)
    share = args.share
    if share is False and os.environ.get("GRADIO_SHARE", "").lower() == "true":
        share = True
    try:
        demo.launch(
            server_name=args.host,
            server_port=args.port,
            share=share,
            ssr_mode=False,
            show_api=True,
        )
    except ValueError as e:
        err = str(e)
        if "localhost is not accessible" in err:
            print(
                "\nGradio could not verify localhost (often HTTP_PROXY / corporate VPN).\n"
                "Try one of:\n"
                "  python scripts/universal_brain_chat.py --share\n"
                "  set GRADIO_SHARE=True   (Windows cmd)\n"
                "  $env:GRADIO_SHARE='true'   (PowerShell)\n",
                file=sys.stderr,
            )
        raise


if __name__ == "__main__":
    main()
