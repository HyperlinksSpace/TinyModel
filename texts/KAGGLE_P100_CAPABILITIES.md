# What You Can Do on Kaggle P100 (Free Tier)

Kaggle Tesla P100 is a strong free GPU option for practical ML work.
On most accounts, you get a weekly GPU quota (commonly around 30 hours), which is enough for serious prototyping and iterative training.

With 16 GB HBM2 VRAM and strong memory bandwidth, P100 often performs very well on workloads that are memory-heavy.

## 1) Train Deep Learning Models Effectively

P100 is good for training substantial models, not just toy experiments.

- Computer Vision:
  - ResNet, EfficientNet, YOLO, ViT, and similar architectures
  - 16 GB VRAM supports meaningful batch sizes for faster iteration
- NLP:
  - Fine-tuning BERT/RoBERTa-family models and other medium transformers
  - Text classification, sequence labeling, and retrieval tasks run comfortably

For very large LLM pretraining, P100 is not enough by itself, but for fine-tuning and practical applied NLP tasks it is very useful.

## 2) Run Mid-Size LLM Inference

P100 can run many 7B-8B class models in quantized form.

- Common examples: Llama-class 8B, Mistral 7B, Gemma 7B (quantized)
- Typical setup: 4-bit or 8-bit quantization for stable inference in 16 GB
- Good use case: evaluate prompts, build demo backends, test product flows

## 3) Image Generation and Generative Workloads

P100 can handle Stable Diffusion-style generation and related workflows.

- Useful for prototyping generative features
- Often faster than weaker GPUs on memory-sensitive pipelines

## 4) GPU-Accelerated Classical ML and Data Processing

Kaggle environments can support RAPIDS-style acceleration for tabular workflows.

- cuDF for large DataFrame operations
- cuML for fast model training on large tabular datasets
- Helpful for million-row scale preprocessing and rapid feature iteration

## 5) Kaggle Competitions and Fast Iteration

P100 remains a strong practical baseline for Kaggle competition notebooks.

- Quick train/eval loops
- Efficient hyperparameter sweeps within session limits
- Reliable final prediction runs before submission

## P100 vs T4 in Kaggle Context

- P100 (single GPU):
  - Strong raw throughput and memory bandwidth
  - Great for single-GPU model training from scratch
- T4 (dual-GPU option in some setups):
  - Higher combined VRAM across two devices
  - Better when model footprint is the main bottleneck

## Important Limits and Caveats

- Free-tier GPU hours are capped weekly
- Sessions are time-limited, so checkpointing is mandatory
- Environment/package updates can break CUDA compatibility if you upgrade core libraries blindly
- P100 is older architecture; modern tensor-core optimizations are less effective than on newer GPUs (A100/H100 class)

## Recommended Workflow for This Repository

For `TinyModel`, Kaggle P100 is a strong training backend:

1. Run training on Kaggle (GPU enabled)
2. Save outputs in notebook artifacts
3. Publish model artifact to Hugging Face (`TinyModel{version}`)
4. Deploy/update Space pointing to the published model

This gives you a low-cost path to production-like iteration without paid GPU infrastructure from day one.
