"""Shared generation helpers for Horizon 2 (causal LMs, optional RAG context)."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from typing import Any

# Small model for fast verification / CPU smoke (poor text quality; use --model for real runs).
SMOKE_MODEL_ID = "sshleifer/tiny-gpt2"
# Sensible default for local quality (still small; override with HORIZON2_DEFAULT_MODEL or --model).
DEFAULT_INSTRUCTION_MODEL = "HuggingFaceTB/SmolLM2-360M-Instruct"


@dataclass
class OneSample:
    id: int
    input: str
    output: str
    seconds: float
    n_prompt_tokens: int
    n_new_tokens: int


def pick_device(explicit: str) -> str:
    import torch

    if explicit == "auto":
        if torch.cuda.is_available():
            return "cuda"
        if torch.backends.mps.is_available() if hasattr(torch.backends, "mps") else False:  # type: ignore[union-attr]
            return "mps"
        return "cpu"
    return explicit


def set_seed(seed: int) -> None:
    import random
    import numpy as np
    import torch

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def build_user_prompt(
    task: str,
    text: str,
    *,
    context: str | None = None,
) -> str:
    c = (context or "").strip()
    if c:
        ctx_block = (
            "You must use ONLY the following CONTEXT; do not invent facts.\n\n"
            f"CONTEXT:\n{c}\n\n"
        )
    else:
        ctx_block = ""
    t = text.strip()
    if task == "summarize":
        return (
            f"{ctx_block}Summarize the user text in 2-4 short sentences. Be concise.\n\n"
            f"USER_TEXT:\n{t}"
        )
    if task == "reformulate":
        return (
            f"{ctx_block}Rewrite USER_TEXT as a clear, professional support reply. "
            f"Keep the same meaning. Under 120 words if possible.\n\n"
            f"USER_TEXT:\n{t}"
        )
    if task == "grounded":
        if not c:
            raise ValueError("task 'grounded' requires --context or --context-file")
        return (
            f"{ctx_block}Answer the user using ONLY the context above. If the context does not "
            f"contain the answer, say you do not have enough information.\n\nUSER_QUESTION:\n{t}"
        )
    raise ValueError(f"unknown task: {task!r} (use summarize, reformulate, or grounded)")


def format_for_model(
    tokenizer: Any,
    user_prompt: str,
) -> str:
    if getattr(tokenizer, "chat_template", None):
        try:
            messages = [{"role": "user", "content": user_prompt}]
            return tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        except Exception:
            pass
    return f"{user_prompt}\n\n### Assistant\n"


@dataclass
class LoadedLM:
    model: Any
    tokenizer: Any
    device: str


def load_causal_lm(
    model_id: str,
    device: str,
) -> LoadedLM:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    d = device if device in ("cpu", "cuda", "mps") else "cpu"
    tok = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    if tok.pad_token is None and tok.eos_token is not None:
        tok.pad_token = tok.eos_token

    if d == "cuda":
        dt = (
            torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
        )
    else:
        dt = torch.float32
    # Prefer `dtype` (newer Transformers); fall back to `torch_dtype` (older).
    try:
        model = AutoModelForCausalLM.from_pretrained(
            model_id, trust_remote_code=True, dtype=dt
        )
    except TypeError:
        model = AutoModelForCausalLM.from_pretrained(
            model_id, trust_remote_code=True, torch_dtype=dt
        )
    model.eval()
    model = model.to(d)
    return LoadedLM(model=model, tokenizer=tok, device=d)


def generate_completion(
    lm: LoadedLM,
    prompt: str,
    *,
    max_new_tokens: int,
    seed: int,
    do_sample: bool = True,
) -> tuple[str, int, int, float]:
    import torch
    from transformers import set_seed as hf_set_seed

    set_seed(seed)
    hf_set_seed(seed)
    tok = lm.tokenizer
    t0 = time.perf_counter()
    enc = tok(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=2048,
        padding="longest",
    )
    input_ids = enc["input_ids"]
    attention_mask = enc.get("attention_mask")
    if lm.device == "cuda":
        input_ids = input_ids.to("cuda")
        if attention_mask is not None:
            attention_mask = attention_mask.to("cuda")
    elif lm.device == "mps":
        input_ids = input_ids.to("mps")
        if attention_mask is not None:
            attention_mask = attention_mask.to("mps")
    n_prompt = int(input_ids.shape[1])
    gen_kw: dict[str, Any] = {
        "max_new_tokens": max_new_tokens,
        "pad_token_id": tok.eos_token_id,
    }
    if attention_mask is not None:
        gen_kw["attention_mask"] = attention_mask
    if do_sample:
        gen_kw["do_sample"] = True
        gen_kw["temperature"] = 0.7
        gen_kw["top_p"] = 0.9
    else:
        gen_kw["do_sample"] = False
    with torch.inference_mode():
        out = lm.model.generate(input_ids, **gen_kw)
    full = out[0]
    new_tokens = full[n_prompt:]
    text = tok.decode(new_tokens, skip_special_tokens=True)
    text = (text or "").strip()
    dt = time.perf_counter() - t0
    n_new = int(new_tokens.shape[0])
    return text, n_prompt, n_new, dt


def run_json_artifact(
    *,
    model_id: str,
    device: str,
    task: str,
    max_new_tokens: int,
    seed: int,
    samples_in: list[tuple[str, str | None]],
    do_sample: bool = True,
) -> dict[str, Any]:
    import transformers

    lm = load_causal_lm(model_id, device)
    out_samples: list[OneSample] = []
    for i, (raw_text, ctx) in enumerate(samples_in):
        up = build_user_prompt(task, raw_text, context=ctx)
        prompt = format_for_model(lm.tokenizer, up)
        out, np_, nn_, sec = generate_completion(
            lm,
            prompt,
            max_new_tokens=max_new_tokens,
            seed=seed + i,
            do_sample=do_sample,
        )
        out_samples.append(
            OneSample(
                id=i,
                input=raw_text,
                output=out,
                seconds=round(sec, 4),
                n_prompt_tokens=np_,
                n_new_tokens=nn_,
            )
        )
    return {
        "horizon": 2,
        "schema": "horizon2_generative_run/1.0",
        "model_id": model_id,
        "device": lm.device,
        "transformers_version": transformers.__version__,
        "task": task,
        "max_new_tokens": max_new_tokens,
        "seed": seed,
        "samples": [asdict(s) for s in out_samples],
    }


def dump_json(d: dict[str, Any], path: str) -> None:
    p = __import__("pathlib").Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")
