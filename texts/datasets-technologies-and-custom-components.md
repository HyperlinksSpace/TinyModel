# Datasets, do-it-yourself data, tools, and what you must build yourself

This note lists **where to get data**, **how to create your own**, **what to reuse off the shelf**, and **what typically remains custom**—especially in the context of text models and systems like TinyModel.

## 1. Public datasets you can use

**General NLP & benchmarks (English and multilingual)**  

- **Hugging Face Hub** — `datasets`: GLUE/SuperGLUE-style tasks, sentiment, NLI, QA, summarization, translation, and domain packs (legal, biomedical, etc.).  
- **Kaggle** — competitions and community datasets; good for prototypes; check **licenses** carefully.  
- **Wikipedia / Wikidata** — dumps for pretraining or knowledge-oriented work (license: open content; follow attribution).  
- **Common Crawl–derived** corpora — large-scale text (heavy; used for pretraining, not quick fine-tunes).  
- **Government & open data** — statistics, registers, public reports (great for **domain** models; cleanup required).

**Task-specific (often commercially relevant)**  

- Customer support logs (rarely public; usually **private**).  
- **Synthetic** or **anonymized** industry datasets from vendors or benchmarks (always verify license and leakage).

**For TinyModel-style training today**  

- Any Hub **single-label text classification** dataset compatible with `scripts/train_tinymodel1_classifier.py` (configurable columns and splits).  
- Start small (e.g. sentiment, topic) to validate pipelines before scaling data or model size.

## 2. Datasets you can create yourself — and how

| Approach | What it is | When to use it |
|----------|------------|----------------|
| **Manual labeling** | Humans assign labels or spans (Excel, Label Studio, Argilla, Prodigy, etc.) | Gold standard for production; expensive |
| **Rules + weak supervision** | Heuristics, dictionaries, regex, distant supervision | Bootstrap labels fast; expect noise |
| **LLM-assisted labeling** | Model proposes labels; humans audit or sample | Speed + scale; needs QA and debiasing |
| **Synthetic generation** | Templates, paraphrases, LLM-generated examples | Augment rare classes; watch distribution shift |
| **User feedback loops** | Thumbs up/down, corrections in-product | Continuous improvement; needs privacy design |
| **Distillation** | Train a small model on outputs/scores from a larger teacher | Compress behavior into deployable models |

**Practical recipe**  

1. Define **labels** and a **labeling guide** (with edge cases).  
2. Start with **500–5,000** reviewed examples if you can; iterate on confusion errors.  
3. Version data like code (**DVC**, lakeFS, or HF dataset revisions).  
4. Split **train / validation / test** with **no leakage** (same document in multiple splits = bad).

## 3. Available technologies, libraries, and packages

**Deep learning & training**  

- **PyTorch** — default for research-style training and custom loops.  
- **Hugging Face Transformers** — pretrained architectures, trainers, export.  
- **Hugging Face `datasets`** — streaming, caching, mapping.  
- **Tokenizers** — fast text preprocessing (used in this repo’s training script).  
- **PEFT / LoRA** — parameter-efficient fine-tuning of large models.  
- **DeepSpeed / FSDP** — scale-up training (multi-GPU).

**Inference & serving**  

- **vLLM**, **TGI (Text Generation Inference)**, **llama.cpp**, **ONNX Runtime**, **TensorRT** — throughput and latency optimizations.  
- **OpenAI-compatible APIs** — swap backends behind one client.

**Orchestration & “brain-like” systems**  

- **LangChain**, **LlamaIndex**, **Haystack**, **semantic-kernel**-style patterns — RAG, agents, tool calling (pick minimal abstractions; avoid framework lock-in if you can).

**MLOps & quality**  

- **Weights & Biases**, **MLflow** — experiments.  
- **Great Expectations** — data tests.  
- **Evaluation**: HELM-style ideas, custom task suites, red-teaming toolkits (choose what matches your risk).

**This repository already uses**  

- `transformers`, `datasets`, `tokenizers`, `torch` — see `scripts/train_tinymodel1_classifier.py` and `scripts/tinymodel_runtime.py`.

## 4. What you typically must create yourself

Libraries give **building blocks**; products need **glue** and **ownership**:

- **Problem formulation** — exact task, success metrics, failure modes.  
- **Private data pipelines** — ETL, PII handling, consent, retention.  
- **Evaluation that matches your users** — not only public leaderboard scores.  
- **Deployment & cost model** — batch vs real-time, regions, SLAs.  
- **Safety & policy layer** — what the model is allowed to do in *your* product.  
- **Proprietary value** — curated data, workflow integration, UX, and operations often matter more than a novel architecture.

---

*Always read dataset and model licenses before commercial use; this note is not legal advice.*
