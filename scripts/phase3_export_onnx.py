#!/usr/bin/env python3
"""Export TinyModel-style checkpoints to ONNX (classifier logits + encoder pooled [CLS] embedding)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

_scripts = Path(__file__).resolve().parent
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))

from phase3_common import LogitsOnly, PooledClfToken, resolve_checkpoint_or_hub

try:
    from onnxruntime.quantization import QuantType, quantize_dynamic
except Exception:  # noqa: BLE001
    quantize_dynamic = None  # type: ignore[assignment, misc]
    QuantType = None  # type: ignore[assignment, misc]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--model",
        type=str,
        required=True,
        help=(
            "Path to a saved model directory, or Hub id (org/model). "
            "On Windows Git Bash, do not use /path/... placeholders — use a relative repo path."
        ),
    )
    p.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directory for .onnx files (default: <model>/onnx if --model is a path, else ./onnx_export).",
    )
    p.add_argument(
        "--max-seq-length",
        type=int,
        default=128,
        help="Tokenizer padding length; must match inference (e.g. TinyModel --max-seq-length / runtime).",
    )
    p.add_argument(
        "--opset",
        type=int,
        default=18,
        help="ONNX opset; dynamo export typically uses 17+ with PyTorch 2.6+.",
    )
    p.add_argument(
        "--dynamic-quantize",
        action="store_true",
        help="Also write classifier_int8.onnx and encoder_int8.onnx (weights quantized, ONNX Runtime).",
    )
    p.add_argument(
        "--use-legacy-torchscript-export",
        action="store_true",
        help="Fallback: old torch.onnx export (may fail on recent transformers + BERT; prefer default dynamo).",
    )
    return p.parse_args()


def default_out_dir(model_arg: str) -> Path:
    p = Path(model_arg)
    if p.is_dir() and p.exists():
        return p / "onnx"
    return Path("onnx_export")


def _export_dynamo(
    mod: torch.nn.Module,
    args: tuple[torch.Tensor, torch.Tensor],
    path: Path,
    *,
    in_names: tuple[str, str],
    out_name: str,
    opset: int,
) -> None:
    """TorchDynamo-based exporter (avoids trace bugs with latest transformers BERT)."""
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    torch.onnx.export(
        mod,
        args,
        str(path),
        input_names=[in_names[0], in_names[1]],
        output_names=[out_name],
        opset_version=opset,
        dynamo=True,
    )


def _export_legacy(
    mod: torch.nn.Module,
    args: tuple[torch.Tensor, torch.Tensor],
    path: Path,
    *,
    in_names: tuple[str, str],
    out_name: str,
    opset: int,
) -> None:
    dynamic = {
        in_names[0]: {0: "batch", 1: "seq"},
        in_names[1]: {0: "batch", 1: "seq"},
        out_name: {0: "batch"},
    }
    if out_name == "pooled":
        dynamic[out_name] = {0: "batch"}  # hidden dim is fixed
    torch.onnx.export(
        mod,
        args,
        str(path),
        input_names=[in_names[0], in_names[1]],
        output_names=[out_name],
        dynamic_axes=dynamic,
        opset_version=opset,
        do_constant_folding=True,
    )


def main() -> None:
    args = parse_args()
    args.model = resolve_checkpoint_or_hub(args.model)
    out = Path(args.output_dir) if args.output_dir else default_out_dir(args.model)
    out.mkdir(parents=True, exist_ok=True)

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForSequenceClassification.from_pretrained(
        args.model,
        attn_implementation="eager",
    )
    model.eval()

    dummy = tokenizer(
        "ONNX export dummy text for tracing.",
        return_tensors="pt",
        padding="max_length",
        max_length=args.max_seq_length,
        truncation=True,
    )
    input_ids = dummy["input_ids"]
    attention_mask = dummy["attention_mask"]
    payload = (input_ids, attention_mask)
    ex = _export_dynamo if not args.use_legacy_torchscript_export else _export_legacy

    clf_wrap = LogitsOnly(model)
    clf_path = out / "classifier.onnx"
    ex(
        clf_wrap,
        payload,
        clf_path,
        in_names=("input_ids", "attention_mask"),
        out_name="logits",
        opset=args.opset,
    )
    print(f"Wrote {clf_path}")

    enc_wrap = PooledClfToken(model)
    enc_path = out / "encoder.onnx"
    ex(
        enc_wrap,
        payload,
        enc_path,
        in_names=("input_ids", "attention_mask"),
        out_name="pooled",
        opset=args.opset,
    )
    print(f"Wrote {enc_path}")
    (out / "export_meta.txt").write_text(
        f"source_model={args.model}\nmax_seq_length={args.max_seq_length}\n"
        f"opset={args.opset}\nexport_mode={'legacy' if args.use_legacy_torchscript_export else 'dynamo'}\n"
        f"note=Default dynamo export uses batch=1; parity/benchmark use batch-1 ORT calls or repeat.\n",
        encoding="utf-8",
    )

    if args.dynamic_quantize:
        if quantize_dynamic is None or QuantType is None:
            print(
                "Warning: onnxruntime.quantization not available; skip dynamic quantize. "
                "Install onnxruntime.",
                file=sys.stderr,
            )
        else:
            for name, src in (("classifier_int8.onnx", clf_path), ("encoder_int8.onnx", enc_path)):
                dst = out / name
                try:
                    quantize_dynamic(
                        str(src),
                        str(dst),
                        weight_type=QuantType.QUInt8,
                    )
                    print(f"Wrote {dst}")
                except Exception as exc:  # noqa: BLE001
                    print(
                        f"Warning: dynamic quantize not applied for {src.name} ({exc}). "
                        "FP32 ONNX is still valid; int8 is optional for some graph shapes.",
                        file=sys.stderr,
                    )


if __name__ == "__main__":
    main()
