#!/usr/bin/env python3
"""CPU latency and artifact size for TinyModel: PyTorch vs ONNX (classify, embed, retrieve)."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import onnxruntime as ort
import torch
import torch.nn.functional as F
from transformers import AutoModelForSequenceClassification, AutoTokenizer

_scripts = Path(__file__).resolve().parent
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))

from phase3_common import resolve_checkpoint_or_hub

from tinymodel_runtime import TinyModelRuntime


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", type=str, required=True, help="Path or Hub id to checkpoint.")
    p.add_argument(
        "--onnx-dir",
        type=str,
        default=None,
        help="ONNX directory (default: <model>/onnx for local path).",
    )
    p.add_argument(
        "--compare-model",
        type=str,
        default=None,
        help="Optional second checkpoint (e.g. pretrained fine-tune) to compare file sizes and throughput.",
    )
    p.add_argument("--repeats", type=int, default=80, help="Timing iterations after warmup.")
    p.add_argument("--warmup", type=int, default=5)
    p.add_argument(
        "--output-json",
        type=str,
        default=None,
        help="Write full report JSON (default: artifacts/phase3/reports/benchmark_<slug>.json).",
    )
    p.add_argument(
        "--output-md",
        type=str,
        default=None,
        help="Write human-readable report (default: same dir as JSON, .md).",
    )
    return p.parse_args()


def resolve_onnx_dir(model_arg: str, onnx_dir: str | None) -> Path | None:
    d = Path(onnx_dir) if onnx_dir else None
    if d is not None and d.is_dir():
        return d
    p = Path(model_arg)
    if p.is_dir() and p.exists():
        cand = p / "onnx"
        if cand.is_dir() and (cand / "classifier.onnx").is_file():
            return cand
    return None


def file_sizes_mib_for_checkpoint(model_path: str) -> dict[str, float]:
    p = Path(model_path)
    out: dict[str, float] = {}
    if not p.is_dir() or not p.exists():
        return out
    mib = 1024 * 1024
    for name in (
        "model.safetensors",
        "pytorch_model.bin",
        "classifier.onnx",
        "encoder.onnx",
    ):
        fp = p / name
        if name.startswith("classifier") or name.startswith("encoder"):
            fp = p / "onnx" / name
        if fp.is_file():
            out[str(fp.name)] = round(fp.stat().st_size / mib, 3)
    return out


def percentile_ms(xs: list[float], p: float) -> float:
    if not xs:
        return 0.0
    xs = sorted(xs)
    k = (len(xs) - 1) * (p / 100.0)
    f = int(k)
    c = f + 1
    if c >= len(xs):
        return xs[-1] * 1000.0
    w = k - f
    return (xs[f] * (1 - w) + xs[c] * w) * 1000.0


def bench_times(fn, n_warm: int, n_rep: int) -> dict[str, float]:
    for _ in range(n_warm):
        fn()
    times = []
    for _ in range(n_rep):
        t0 = time.perf_counter()
        fn()
        times.append(time.perf_counter() - t0)
    m = [x * 1000.0 for x in times]
    return {
        "mean_ms": float(statistics.fmean(m)),
        "p50_ms": percentile_ms(times, 50.0),
        "p90_ms": percentile_ms(times, 90.0),
    }


def run_benchmark_for_model(
    model_id: str,
    onnx_d: Path | None,
    *,
    repeats: int,
    warmup: int,
) -> dict[str, Any]:
    q = "Shipping delays caused frustration among holiday shoppers."
    cands = [
        "The parcel arrived two days after the expected date.",
        "The home side scored a dramatic winner in the final minutes.",
        "The central bank left interest rates unchanged at today's meeting.",
    ]
    text_one = "Markets were mixed as investors digested the jobs report."
    out: dict[str, Any] = {"model": model_id, "onnx_dir": str(onnx_d) if onnx_d else None}

    rt = TinyModelRuntime(model_id, device="cpu", max_length=128)

    b_cls = bench_times(lambda: rt.classify([text_one]), warmup, repeats)
    b_emb = bench_times(
        lambda: rt.embed(
            [q, cands[0], cands[1]],
        ),
        warmup,
        repeats,
    )
    b_ret = bench_times(lambda: rt.retrieve(q, cands, top_k=2), warmup, repeats)
    out["pytorch"] = {
        "classify_batch1": b_cls,
        "embed_batch3": b_emb,
        "retrieve_top2_query3cand": b_ret,
    }

    p = Path(model_id)
    if p.is_dir():
        out["file_sizes_mib"] = file_sizes_mib_for_checkpoint(str(p))

    if onnx_d and (onnx_d / "classifier.onnx").is_file() and (onnx_d / "encoder.onnx").is_file():
        tok = AutoTokenizer.from_pretrained(model_id)
        sess_c = ort.InferenceSession(
            str(onnx_d / "classifier.onnx"), providers=["CPUExecutionProvider"]
        )
        sess_e = ort.InferenceSession(
            str(onnx_d / "encoder.onnx"), providers=["CPUExecutionProvider"]
        )

        def onnx_classify() -> None:
            batch = tok(
                text_one,
                return_tensors="pt",
                padding="max_length",
                truncation=True,
                max_length=128,
            )
            ort_in = {
                "input_ids": batch["input_ids"].cpu().numpy().astype(np.int64),
                "attention_mask": batch["attention_mask"].cpu().numpy().astype(np.int64),
            }
            logits = sess_c.run(None, ort_in)[0]
            ex = np.exp(logits - logits.max(axis=1, keepdims=True))
            _ = ex / ex.sum(axis=1, keepdims=True)  # noqa: F841

        def _enc_run_batch1(text: str) -> torch.Tensor:
            b = tok(
                text,
                return_tensors="pt",
                padding="max_length",
                truncation=True,
                max_length=128,
            )
            oi = {
                "input_ids": b["input_ids"].cpu().numpy().astype(np.int64),
                "attention_mask": b["attention_mask"].cpu().numpy().astype(np.int64),
            }
            return torch.tensor(sess_e.run(None, oi)[0], dtype=torch.float32)

        def onnx_embed3() -> None:
            # Default ONNX in this repo is batch=1; run encoder per string.
            parts = []
            for t in (q, cands[0], cands[1]):
                parts.append(_enc_run_batch1(t))
            poo = torch.cat(parts, dim=0)
            _ = F.normalize(poo, p=2, dim=1)  # noqa: F841

        def onnx_retrieve() -> None:
            parts = []
            for t in (q, *cands):
                parts.append(_enc_run_batch1(t))
            poo = F.normalize(torch.cat(parts, dim=0), p=2, dim=1)
            qe = poo[0:1]
            ce = poo[1:]
            _ = (qe @ ce.T).squeeze(0)  # noqa: F841

        out["onnx"] = {
            "classify_batch1": bench_times(onnx_classify, warmup, repeats),
            "embed_batch3": bench_times(onnx_embed3, warmup, repeats),
            "retrieve_top2_query3cand": bench_times(onnx_retrieve, warmup, repeats),
        }
    return out


def main() -> None:
    args = parse_args()
    args.model = resolve_checkpoint_or_hub(args.model)
    if args.compare_model:
        args.compare_model = resolve_checkpoint_or_hub(args.compare_model)
    onnx_d = resolve_onnx_dir(args.model, args.onnx_dir)
    p_model = Path(args.model)
    slug = p_model.name if p_model.name not in (".", "") else str(args.model).replace("/", "_")

    rep: dict[str, Any] = {
        "primary": run_benchmark_for_model(
            args.model, onnx_d, repeats=args.repeats, warmup=args.warmup
        ),
    }
    if args.compare_model:
        p2 = Path(args.compare_model)
        onnx2 = p2 / "onnx" if p2.is_dir() else None
        if onnx2 and not (onnx2 / "classifier.onnx").is_file():
            onnx2 = None
        rep["compare"] = run_benchmark_for_model(
            args.compare_model, onnx2, repeats=args.repeats, warmup=args.warmup
        )

    out_dir = Path("artifacts/phase3/reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    jpath = Path(
        args.output_json
        if args.output_json
        else out_dir / f"benchmark_{slug}.json"
    )
    mpath = Path(args.output_md) if args.output_md else jpath.with_suffix(".md")
    jpath.write_text(json.dumps(rep, indent=2) + "\n", encoding="utf-8")
    mpath.write_text(_render_md(rep, slug), encoding="utf-8")
    print(f"Wrote {jpath}")
    print(f"Wrote {mpath}")


def _render_md(rep: dict[str, Any], slug: str) -> str:
    lines = [
        f"# Phase 3 runtime benchmark ({slug})",
        "",
        "CPU timings (mean / p50 / p90 in ms). `retrieve` includes embedding the query and candidates, then a dot-product top-k (same work as `TinyModelRuntime.retrieve` but ONNX uses ORT for the encoder).",
        "",
    ]
    for name, block in rep.items():
        lines.append(f"## {name.title()}")
        m = block.get("model", "")
        lines.append(f"- **Model:** `{Path(m).as_posix()}`")
        if block.get("onnx_dir"):
            lines.append(f"- **ONNX dir:** `{Path(block['onnx_dir']).as_posix()}`")
        if block.get("file_sizes_mib"):
            lines.append(
                f"- **Artifact sizes (MiB, selected files):** "
                f"{json.dumps(block['file_sizes_mib'], sort_keys=True)}"
            )
        lines.append("")
        for k in ("pytorch", "onnx"):
            if k not in block:
                continue
            lines.append(f"### {k}")
            b = block[k]
            for op, t in b.items():
                lines.append(
                    f"- **{op}** — mean {t['mean_ms']:.3f} ms, p50 {t['p50_ms']:.3f} ms, p90 {t['p90_ms']:.3f} ms"
                )
        lines.append("")
    lines.append(
        "Re-run with: `python scripts/phase3_benchmark.py --model <path> [--compare-model <path2>]` (ensure `phase3_export_onnx.py` ran so ONNX numbers appear)."
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
