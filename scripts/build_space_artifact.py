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
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    version = str(args.version).strip()
    if not version.isdigit() or int(version) < 1:
        raise ValueError("Version must be a positive integer, e.g. 1 or 2.")

    model_name = f"TinyModel{version}"
    space_name = f"{model_name}Space"
    model_id = f"{args.namespace}/{model_name}"

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    app_py = f"""import gradio as gr
from transformers import pipeline

MODEL_ID = "{model_id}"
clf = pipeline("text-classification", model=MODEL_ID, tokenizer=MODEL_ID)


def predict(text):
    result = clf(text, truncation=True, max_length=128, top_k=None)[0]
    result = sorted(result, key=lambda x: x["score"], reverse=True)
    return {{item["label"]: float(item["score"]) for item in result}}


demo = gr.Interface(
    fn=predict,
    inputs=gr.Textbox(lines=4, label="Input text"),
    outputs=gr.Label(num_top_classes=4, label="Predicted class"),
    title="{space_name}",
    description="Demo Space for {model_name} (AG News classifier).",
)

if __name__ == "__main__":
    demo.launch()
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
