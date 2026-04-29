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
import warnings
from pathlib import Path

_scripts = Path(__file__).resolve().parent
_REPO = _scripts.parent
DEFAULT_MEMORY_DB = str(_REPO / ".tmp" / "ub_chat_memory.sqlite")
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))

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
from horizon3_store import clear_session, connect, init_schema, list_for_scope, put  # noqa: E402
from rag_faq_smoke import _pick_model, hybrid_retrieve, load_chunks  # noqa: E402
from tinymodel_runtime import TinyModelRuntime  # noqa: E402

HELP_TEXT = """**How to use**
- **Normal language:** ask in plain English (or mixed); the app **infers** what you want (summarize, search FAQ, save a note, etc.).
- **Shortcuts:** slash commands still work (`/help`, `/status`, …).

**Intents the router understands** (examples, not exact wording):
- Ordinary chat / questions
- **Summarize** this text — provide the passage in the same message
- **Rewrite** professionally / rephrase
- **Answer using only** these facts — include both facts and question
- **Search** the FAQ / **find** in the knowledge base
- **Classify** (topic model) this paragraph
- **Remember** / note / store: **long-term** vs **this session only**
- **Show** saved notes; **clear** session notes
- **Status** of loaded models

**Classifier** uses AG News–style labels on default Hub weights (World, Business, Sports, Sci/Tech).

If routing misfires, try rephrasing or use a slash command; **`--no-smart-route`** disables inference (chat only, plus `/…`)."""

ROUTER_SYSTEM = """You are an intent router for a desktop AI assistant. The user speaks naturally (any language). Output EXACTLY one JSON object, one line, no markdown fences, no explanation.

Schema:
{"intent":"<name>","text":"","question":"","context":""}

intent must be one of:
- chat — general talk, advice, open questions, follow-ups; put the FULL user message in "text"
- summarize — user wants a shorter summary; put source in "text"
- reformulate — rewrite/clarify/professional tone; source in "text"
- grounded — answer only from given facts; put QUESTION in "question", FACTS in "context" (if user mixes both in one blob, split sensibly)
- retrieve — search FAQ/knowledge; put search query in "text"
- classify — show topic-classifier probabilities; put passage in "text"
- remember — save a durable note; put note body in "text"
- session_note — save a session-only note; put note in "text"
- list_memories — user wants to see saved notes
- clear_session — user wants session-only notes deleted
- status — loaded components / debug info
- help — explain available capabilities

Rules:
- Default to "chat" when unsure; copy the entire user message into "text".
- Do not invent facts for "grounded": if no clear facts/context, use "chat" instead.
- Extract minimal "text" for tool intents (do not repeat system chatter)."""

VALID_INTENTS = frozenset(
    {
        "chat",
        "summarize",
        "reformulate",
        "grounded",
        "retrieve",
        "classify",
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
}


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
    lines = [
        "### Status\n",
        f"- **Generative:** `{meta_mid}`",
        f"- **Encoder:** {meta_encoder}",
        f"- **RAG corpus:** {_clip(meta_rag_path or '—', 80)} · **chunks:** {rag_n}",
        f"- **Memory DB:** `{meta_mem_db or 'off'}` · **scope:** `{scope_key}`",
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
        "--router-max-new-tokens",
        type=int,
        default=192,
        help="Max new tokens for the routing JSON completion.",
    )

    return p.parse_args()


def main() -> None:
    args = parse_args()
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

    meta_encoder = encoder_id or "off"
    meta_rag = str(rag_path.resolve()) if rag_path else None
    meta_mem = mem_path

    print(f"Loading generative model {mid!r} on {dev!r} ...", flush=True)
    lm = load_causal_lm(mid, dev)
    turn_counter = {"n": 0}
    show_trace = not args.no_trace and (
        encoder is not None or mem_conn is not None or (rag_chunks is not None)
    )

    def respond(
        message: str,
        history: list[dict],
    ) -> tuple[str, list[dict]]:
        msg = (message or "").strip()
        hist = list(history or [])
        if not msg:
            return "", hist

        turn_counter["n"] += 1
        seed = (args.seed + turn_counter["n"]) % (2**31)

        slash_out = handle_slash(
            msg,
            lm=lm,
            mem_conn=mem_conn,
            scope_key=args.memory_scope,
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
            return "", hist

        chat_line = msg
        if not args.no_smart_route:
            try:
                route = infer_route(
                    lm,
                    msg,
                    seed=seed,
                    max_new_tokens=args.router_max_new_tokens,
                )
            except Exception:
                route = {"intent": "chat", "text": msg, "question": "", "context": ""}

            if route["intent"] != "chat":
                tool_reply = run_routed_tool(
                    route,
                    msg=msg,
                    lm=lm,
                    mem_conn=mem_conn,
                    scope_key=args.memory_scope,
                    encoder=encoder,
                    rag_chunks=rag_chunks,
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
                    return "", hist

            chat_line = route["text"] or msg

        trace: list[str] = []
        extras: list[str] = []

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
        if encoder and rag_chunks:
            hr = hybrid_retrieve(encoder, chat_line, rag_chunks, top_k=args.rag_top_k)
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

        if mem_conn:
            items = list_for_scope(mem_conn, args.memory_scope)
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
        if show_trace and trace:
            out += "\n\n---\n*Brain trace:* " + " · ".join(trace)

        hist.append({"role": "user", "content": msg})
        hist.append({"role": "assistant", "content": out})
        return "", hist

    brain_bits = []
    if encoder:
        brain_bits.append("encoder")
    if rag_chunks:
        brain_bits.append("RAG")
    if mem_conn:
        brain_bits.append("memory")
    brain_label = "+".join(brain_bits) if brain_bits else "LM only"

    with gr.Blocks(title="Universal Brain (chat prototype)") as demo:
        gr.Markdown(
            "### Universal Brain — chat prototype\n"
            f"**Generative:** `{mid}` ({lm.device}) · **Brain layers:** {brain_label}\n\n"
            "**NL routing:** the model infers what you want (summarize, FAQ search, save note, …). "
            "Use **`--no-smart-route`** for plain chat-only + slash shortcuts. "
            "`/help` lists slash commands.\n\n"
            "Encoder topics (Hub TinyModel1 ≈ AG News) still feed context and an optional *Brain trace* line; "
            "use `/classify` or ask naturally to see the full probability table in chat."
        )
        chat = gr.Chatbot(type="messages", height=520, label="Conversation", allow_tags=False)
        with gr.Row():
            inp = gr.Textbox(
                lines=1,
                max_lines=1,
                show_label=False,
                placeholder="Ask in plain language, or use /help …",
                scale=9,
            )
            go = gr.Button("Send", variant="primary", scale=1)
        gr.ClearButton([chat, inp])

        def _submit(m: str, h: list[dict]) -> tuple[str, list[dict]]:
            return respond(m, h)

        go.click(_submit, [inp, chat], [inp, chat])
        inp.submit(_submit, [inp, chat], [inp, chat])

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
