# Optional R&D lane (backlog, not in the critical path)

The **further development plan** leaves this lane for experiments that might improve quality or product fit **after** Phases 1–3 and the current baseline are good enough to justify extra time.

**Backlog (pick any as a 1–2 day spike when metrics demand it):**

- **PEFT / LoRA** on a pretrained head — see the Hugging Face [PEFT](https://huggingface.co/docs/peft) library; typical entry is `LoraConfig` + `get_peft_model` around `AutoModelForSequenceClassification` with a frozen base, then the same `eval_report.json` pipeline for comparison.
- **Multilingual or domain-adapted encoders** — swap `--base-model` in `finetune_pretrained_classifier.py` (or a LoRA-tuned equivalent), keep the same data caps and compare `macro_f1` / per-class F1 in `eval_report.json`.
- **Retrieval** — try mean-pooling, attention pooling, or a small projection on top of `[CLS]` before cosine retrieval; use `embeddings_smoke_test.py` and a fixed candidate list for A/B.
- **Scaling laws** on your own data — more epochs, more samples, and label error correction often beat architecture tweaks; track cost vs. metrics under the **decision gates** in `texts/further-development-plan.md`.

**Exit (when you do run a spike):** short write-up, metrics vs. baseline, and merge/drop/schedule decision—per the plan’s optional R&D exit steps.
