#!/usr/bin/env python3
"""Build a versioned Hugging Face Space artifact for TinyModel."""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Space files for TinyModel{version}Space."
    )
    parser.add_argument("--namespace", required=True, help="HF org/user namespace")
    parser.add_argument("--version", required=True, help="Artifact version number")
    parser.add_argument("--output-dir", required=True, help="Output directory path")
    parser.add_argument(
        "--model-id",
        required=False,
        default="",
        help="Explicit HF model repo id for the Space to use.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    version = str(args.version).strip()
    if not version.isdigit() or int(version) < 1:
        raise ValueError("Version must be a positive integer, e.g. 1 or 2.")

    model_name = f"TinyModel{version}"
    space_name = f"{model_name}Space"
    model_id = args.model_id.strip() or f"{args.namespace}/{model_name}"
    space_host = f"{args.namespace.lower()}-{space_name.lower()}.hf.space"
    space_url = f"https://{space_host}"

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    app_py = f"""import os
import gradio as gr
from transformers import pipeline

MODEL_ID = "{model_id}"
SPACE_URL = "{space_url}"
_clf = None


def get_pipeline():
    global _clf
    if _clf is not None:
        return _clf
    token = os.getenv("HF_TOKEN")
    kwargs = {{}}
    if token:
        kwargs["token"] = token
    _clf = pipeline(
        "text-classification",
        model=MODEL_ID,
        tokenizer=MODEL_ID,
        top_k=None,
        **kwargs,
    )
    return _clf


def _prediction_list(batch_output):
    # One batch item: either a single {{label, score}} dict or a list of them.
    if not batch_output:
        return []
    first = batch_output[0]
    if isinstance(first, dict):
        return [first]
    if isinstance(first, list):
        return first
    return []


def predict(text):
    text = (text or "").strip()
    if not text:
        return {{}}, "Please enter some text first."
    try:
        clf = get_pipeline()
    except Exception as exc:
        return {{}}, f"Model load failed for {{MODEL_ID}}: {{exc}}"
    raw = clf(text, truncation=True, max_length=128)
    preds = _prediction_list(raw)
    if not preds:
        return {{}}, "Empty model output (unexpected pipeline shape)."
    preds = sorted(preds, key=lambda x: float(x["score"]), reverse=True)
    return {{item["label"]: float(item["score"]) for item in preds}}, "OK"


EXAMPLES = [
    ["Apple reported strong quarterly revenue growth and raised guidance."],
    ["The team won the championship after a dramatic overtime finish."],
    ["Scientists announced a new breakthrough in battery technology."],
    ["Leaders met to discuss tensions and trade policy in the region."],
]

with gr.Blocks(title="{space_name}") as demo:
    gr.Markdown("# {space_name}")
    gr.Markdown("Model: `{model_id}`")
    gr.Markdown("Public URL: [{space_url}]({space_url})")
    inp = gr.Textbox(lines=4, label="Input text", placeholder="Paste a news sentence here...")
    out = gr.Label(num_top_classes=4, label="Predicted class probabilities")
    status = gr.Textbox(label="Status", interactive=False)
    run_btn = gr.Button("Run Inference", variant="primary")
    run_btn.click(fn=predict, inputs=inp, outputs=[out, status])
    inp.submit(fn=predict, inputs=inp, outputs=[out, status])
    gr.Examples(examples=EXAMPLES, inputs=inp)

if __name__ == "__main__":
    print(f"Space URL: {{SPACE_URL}}")
    demo.launch(ssr_mode=False)
"""
    requirements = "gradio\ntransformers\ntorch\n"
    readme = f"""---
title: {space_name}
emoji: 🤗
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: 5.49.1
app_file: app.py
pinned: false
---

# {space_name}

Interactive demo for `{model_id}`.
"""

    (output_dir / "app.py").write_text(app_py, encoding="utf-8")
    (output_dir / "requirements.txt").write_text(requirements, encoding="utf-8")
    (output_dir / "README.md").write_text(readme, encoding="utf-8")
    print(f"Built Space artifact in {output_dir}")


if __name__ == "__main__":
    main()
