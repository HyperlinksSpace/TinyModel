# Universal Brain — what you can do (reference)

This file is the maintainer reference for the [TinyModel1Space](https://huggingface.co/spaces/HyperlinksSpace/TinyModel1Space) chat. The live Space UI copies the **Testing embedded prompt signals** table from `scripts/universal_brain_chat.py` (`GRADIO_INSTRUCTIONS_MARKDOWN`).

## How to interact

1. **Plain language** — describe what you want (summarize, search FAQ, remember a note, compare options, etc.). A JSON **intent router** picks a tool when smart routing is on.
2. **Slash shortcuts** — `/help`, `/status`, `/classify`, `/retrieve`, `/web`, `/summarize`, `/reformulate`, `/grounded`, `/similarity`, `/embed`, `/nearest`, `/remember`, `/session`, `/memories`, …
3. **Short control phrases** — no slash; adjust **session** settings (scope, trace, FAQ, routing, reply style). Persist until you reset or start a new session.
4. **Long normal chat** — embed preferences in a full question; **embedded prompt signals** apply for **one turn** only (see brain-trace footer `prompt_signals:`).

Say **Show the brain trace** to see classifier hints, RAG/memory flags, and `prompt_signals:` on replies.

## Tools (via routing or slash)

| Task | Natural language (examples) | Slash |
| --- | --- | --- |
| Chat | General Q&A | (default) |
| Summarize | “Summarize this: …” | `/summarize` |
| Rephrase | “Rewrite professionally: …” | `/reformulate` |
| Grounded Q&A | Facts in the message, `question \|\|\| context` | `/grounded` |
| FAQ search | “Search the FAQ for …” | `/retrieve` |
| Web search | “Search the web for …” (needs Google CSE secrets) | `/web` |
| Classify topic | “Classify: …” (4 AG News–style labels) | `/classify` |
| Similarity | Two texts, `a \|\|\| b` | `/similarity` |
| Embedding | Short passage | `/embed` |
| Nearest option | `query \|\|\| opt1 \|\|\| opt2 …` | `/nearest` |
| Memory | Remember / list / export / clear / forget scope | `/remember`, `/session`, `/memories`, … |
| Status | What is loaded, scope, toggles | `/status` |

## Session control phrases (short; persist)

| Area | Example phrases |
| --- | --- |
| **Scope & memory** | *What is my current scope?*, *Start a new private session*, *Switch to scope team-a*, *Export my memories*, *Delete all my memories for this chat* |
| **Toggles** | *Show the brain trace*, *Turn off FAQ context*, *Turn off smart routing* |
| **Reply length & format** | *Be brief*, *More detail please*, *Use bullet points*, *No bullets plain paragraphs*, *Reset reply style* |
| **FAQ grounding** | *Strict FAQ*, *Relaxed FAQ*, *Balanced FAQ* |
| **Audience** | *ELI5*, *Explain simply*, *Expert mode*, *Assume I'm technical* |
| **Answer shape** | *TLDR first*, *Answer directly*, *Step by step*, *No numbered steps* |
| **Tone & style** | *Flag your assumptions*, *Be decisive*, *Formal tone*, *Casual tone* |
| **Content style** | *Use tables*, *No tables*, *Use analogies*, *Bold key terms*, *Spell out acronyms*, … (see `/help` for full list) |

## Embedded prompt signals (one turn; long chat)

Detected from wording inside a **normal** message (not a dedicated control line). Conflicting cues in one line usually disable both sides.

| Group | Example tags in `prompt_signals:` |
| --- | --- |
| **Layout & comparison** | `comparison_frame=pros_cons`, `comparison_frame=narrative`, `table_style=prefer/avoid`, `reply_format=bullets/prose`, `step_style=numbered/continuous`, `section_headings=prefer/avoid`, `faq_qa` |
| **Length & caps** | `verbosity=brief/detailed`, `len_cap=80w`, `len_cap=3s`, … |
| **Code** | `code_only`, `code_explained`, `pseudocode`, `runnable_code`, `code_block_style=fenced/inline` |
| **Decisions** | `ranked_options`, `decision_matrix`, `options_n=3`, `checklist`, `no_checklist` |
| **Visual & structure** | `diagram`, `no_diagram`, `frame_star`, `frame_prep`, `frame_irac`, `timeline_chron`, `timeline_reverse` |
| **Planning & editing** | `risks_first`, `benefits_first`, `revise_draft`, `revise_diff`, `topic_guard`, `topic_must`, `glossary` |
| **Learning & tone** | `guided`, `full_solution`, `counterpoint_tone=challenge/supportive`, `audience=simple/technical`, `register_tone=formal/casual`, `voice_second`, `voice_third` |
| **Facts & sources** | `speculation=strict/creative`, `cite_sources`, `cite_minimal`, `faq_grounding=strict/relaxed`, `quote_style=quote/paraphrase` |
| **Other** | `language`, `spelling_uk`, `spelling_us`, `summary_last`, `faq_qa`, `ephemeral`, `a11y`, `answer_lead=tldr_first/direct`, `actionability=commands/conceptual`, `math_detail=show_work/final_only`, … |

**Step-by-step examples:** scroll to **Testing embedded prompt signals** under the chat on the Space.

## What is not supported here

- **Images, audio, video** (text-in / text-out only).
- **Private auth** on the public demo (shared default scope unless you start a *private session*).
- **Guaranteed correctness** — small LMs can hallucinate; FAQ/web snippets help but do not eliminate errors.
