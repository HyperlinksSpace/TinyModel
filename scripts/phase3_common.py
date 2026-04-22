"""Shared helpers for Phase 3 ONNX export and ONNX Runtime checks."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import torch
import torch.nn as nn
from transformers import PreTrainedModel

def backbone_module(model: PreTrainedModel) -> nn.Module:
    for name in ("bert", "distilbert", "roberta", "electra", "camembert", "xlm_roberta"):
        if hasattr(model, name):
            return getattr(model, name)
    raise ValueError("Unsupported encoder backbone for ONNX export; expected BERT-family checkpoint.")


class LogitsOnly(nn.Module):
    """ONNX traceable wrapper: (input_ids, attention_mask) -> logits."""

    def __init__(self, m: PreTrainedModel) -> None:
        super().__init__()
        self.model = m

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        return self.model(input_ids=input_ids, attention_mask=attention_mask).logits


class PooledClfToken(nn.Module):
    """ONNX traceable: first token (CLS / equivalent) of last hidden state."""

    def __init__(self, m: PreTrainedModel) -> None:
        super().__init__()
        self.encoder = backbone_module(m)
        self.hidden = int(
            getattr(m.config, "hidden_size", getattr(m.config, "dim", 768))
        )

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        out = self.encoder(
            input_ids=input_ids, attention_mask=attention_mask, return_dict=True
        )
        h = out.last_hidden_state
        return h[:, 0, :]


_HUB_ID_RE = re.compile(r"^[\w.-]+/[\w.-]+$")

# "org/model" with one slash is ambiguous vs a repo subpath. Reject as Hub if missing locally
# and the first segment looks like a top-level project folder, not a HF namespace.
_LIKELY_LOCAL_PREFIX = frozenset(
    {"artifacts", "scripts", "texts", "tests", "test", "data", "docs", "tmp", "temp", ".tmp"}
)


def is_plausible_hub_id(s: str) -> bool:
    """Hugging Face id `namespace/model` (not a resolvable local checkpoint)."""
    t = s.strip()
    if not t or t.count("/") != 1 or ".." in t:
        return False
    a, b = t.split("/", 1)
    if not a or not b:
        return False
    p = Path(t)
    if p.is_dir() and (p / "config.json").is_file():
        return False
    if a.lower() in _LIKELY_LOCAL_PREFIX:
        return False
    return _HUB_ID_RE.match(t) is not None


def resolve_checkpoint_or_hub(model_arg: str) -> str:
    """Return an absolute local path, or a Hub id string. Exit with a clear error if invalid."""
    s = model_arg.strip()
    p = Path(s)
    if p.is_dir() and (p / "config.json").is_file():
        return str(p.resolve())
    if is_plausible_hub_id(s):
        return s
    if p.exists() and p.is_dir() and not (p / "config.json").is_file():
        print(f"Not a model directory (missing config.json): {s!r}", file=sys.stderr)
        raise SystemExit(1)

    msg = f"Invalid --model: {s!r} (not a local checkpoint with config.json, and not a Hub id).\n"
    norm = s.replace("\\", "/").lower()
    if "program files" in norm and "git" in norm and "path" in s.lower():
        msg += (
            "  (Git Bash on Windows) A path like /path/to/checkpoint is rewritten to "
            "C:/Program Files/Git/... - not your project. Use a relative path, e.g. "
            "artifacts/phase1/runs/smoke/ag_news/scratch, or a Hub id HyperlinksSpace/TinyModel1.\n"
        )
    else:
        msg += (
            "  Example: --model artifacts/phase1/runs/smoke/ag_news/scratch "
            "or --model HyperlinksSpace/TinyModel1\n"
        )
    print(msg, file=sys.stderr)
    raise SystemExit(1)
