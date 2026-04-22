#!/usr/bin/env python3
"""Compare PyTorch and ONNX Runtime outputs for a TinyModel checkpoint (logits + pooled embedding)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch
import torch.nn.functional as F
from transformers import AutoModelForSequenceClassification, AutoTokenizer

_scripts = Path(__file__).resolve().parent
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))

from phase3_common import PooledClfToken, resolve_checkpoint_or_hub


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", type=str, required=True, help="HuggingFace model path or Hub id.")
    p.add_argument(
        "--onnx-dir",
        type=str,
        default=None,
        help="Directory with classifier.onnx and encoder.onnx (default: <path>/onnx for local path).",
    )
    p.add_argument(
        "--rtol", type=float, default=1e-3, help="Allclose rtol for float comparison."
    )
    p.add_argument(
        "--atol", type=float, default=1e-4, help="Allclose atol for float comparison."
    )
    p.add_argument(
        "--max-seq-length", type=int, default=128, help="Tokenization max length (match export)."
    )
    return p.parse_args()


def resolve_onnx_dir(model_arg: str, onnx_dir: str | None) -> Path:
    if onnx_dir:
        return Path(onnx_dir)
    p = Path(model_arg)
    if p.is_dir() and p.exists():
        return p / "onnx"
    return Path("onnx_export")


def main() -> None:
    args = parse_args()
    args.model = resolve_checkpoint_or_hub(args.model)
    samples = [
        "Stocks rallied after the central bank held rates.",
        "The team won the final in extra time with a late goal.",
    ]
    d = resolve_onnx_dir(args.model, args.onnx_dir)
    clf_p = d / "classifier.onnx"
    enc_p = d / "encoder.onnx"
    if not clf_p.is_file() or not enc_p.is_file():
        print(
            f"Missing {clf_p} and/or {enc_p}. Run:\n"
            f"  python scripts/phase3_export_onnx.py --model {args.model}\n",
            file=sys.stderr,
        )
        raise SystemExit(1)

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    pt_model = AutoModelForSequenceClassification.from_pretrained(
        args.model,
        attn_implementation="eager",
    )
    pt_model.eval()
    enc_ref = PooledClfToken(pt_model)

    session_opts = ort.SessionOptions()
    session_opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    clf_sess = ort.InferenceSession(
        str(clf_p), session_opts, providers=["CPUExecutionProvider"]
    )
    enc_sess = ort.InferenceSession(
        str(enc_p), session_opts, providers=["CPUExecutionProvider"]
    )

    for text in samples:
        # Dynamo-exported ONNX in this repo is traced at batch=1; ORT then expects batch=1.
        batch = tokenizer(
            text,
            return_tensors="pt",
            padding="max_length",
            truncation=True,
            max_length=args.max_seq_length,
        )
        iid = batch["input_ids"]
        msk = batch["attention_mask"]
        with torch.inference_mode():
            pt_log = pt_model(input_ids=iid, attention_mask=msk).logits
            pt_pool = enc_ref(input_ids=iid, attention_mask=msk)

        ort_in = {
            "input_ids": iid.cpu().numpy().astype(np.int64),
            "attention_mask": msk.cpu().numpy().astype(np.int64),
        }
        o_log = torch.tensor(clf_sess.run(None, ort_in)[0], dtype=pt_log.dtype)
        o_pool = torch.tensor(enc_sess.run(None, ort_in)[0], dtype=pt_pool.dtype)

        ok_log = torch.allclose(pt_log, o_log, rtol=args.rtol, atol=args.atol)
        ok_pool = torch.allclose(pt_pool, o_pool, rtol=args.rtol, atol=args.atol)
        mae_log = float((pt_log - o_log).abs().max().item())
        mae_p = float((pt_pool - o_pool).abs().max().item())
        print(f"Text: {text[:48]}…")
        print(f"  logits  match: {ok_log}  max_abs_err={mae_log:.2e}")
        print(f"  encoder match: {ok_pool}  max_abs_err={mae_p:.2e}")
        if not (ok_log and ok_pool):
            print("  FAILED parity checks", file=sys.stderr)
            raise SystemExit(1)

    print("ONNX parity check passed (classifier + encoder).")


if __name__ == "__main__":
    main()
