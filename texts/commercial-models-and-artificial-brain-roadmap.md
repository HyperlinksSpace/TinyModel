# Commercially demanded models and a roadmap toward general-purpose systems

This note connects **what the market pays for today** with a **long-term direction** toward more general, “brain-like” AI—without pretending that goal is a single product you ship next quarter.

## What companies actually buy (near-term demand)

These are the categories that most often show up in RFPs, product roadmaps, and vendor budgets:

| Area | Typical deliverable | Why it sells |
|------|---------------------|--------------|
| **Search & retrieval** | Embeddings, re-rankers, hybrid lexical+vector search | Faster support, compliance discovery, internal knowledge |
| **Classification & routing** | Topic, intent, urgency, language, toxicity “triage” models | Automate queues, reduce human load |
| **Structured extraction** | Entities, tables, forms, key fields from documents | Workflows, analytics, automation |
| **Assistants (scoped)** | Chat over *your* data (RAG), with guardrails | Productivity without full AGI claims |
| **Code & tools** | Completion, review helpers, codegen with CI integration | Measurable dev velocity |
| **Vision & multimodal** (where relevant) | OCR+understanding, defect detection, media moderation | Regulated or operational use cases |

Baselines like **TinyModel1** sit in the **classification + small encoder** lane: cheap to run, easy to deploy, good for **routing and prototypes** before you invest in larger models.

## Moving toward “general purpose” in a sober way

“General purpose” in industry usually means **one model family** that handles many tasks via:

- **Instruction following** (do what the user asked in natural language)
- **In-context learning** (few-shot or tool use)
- **Unified interfaces** (same API for classify, summarize, extract, generate)

That is the lane of **large language models (LLMs)** and **multimodal foundation models**, not a 2-layer BERT trained from scratch on one dataset.

A realistic ladder for *this* repository and your ambitions:

1. **Specialized small models** (today): fast text classifiers, embeddings from encoders, clear evaluation.
2. **Adapted mid-size models**: fine-tuning, LoRA/PEFT, instruction tuning on domain data—still bounded tasks.
3. **General LLM serving**: host or call frontier/open models; focus on **data, eval, safety, and orchestration** (RAG, agents, policies).
4. **Research-grade “brain” direction**: memory over time, world models, continual learning, embodied or multimodal grounding—mostly **lab + selective products**, not a single “brain.exe”.

## What “lab + selective products” means

**Lab** (research lab, not “laboratory software”) is work done **off the main revenue path**: experiments, prototypes, and papers-grade ideas that are **not** yet reliable or cheap enough to expose to every customer. Examples: continual learning that forgets unpredictably, embodied agents in unconstrained environments, or world models that only work on narrow simulators. You pursue them to learn and to **option** future capabilities—not because next quarter’s roadmap depends on them.

**Selective products** means you ship advanced “brain-like” features only where the **risk–reward** profile fits: a **closed beta**, a **single enterprise** with contractual guardrails, an **internal** tool, or a **vertical** where failure modes are understood (e.g. assistive tech with human oversight). The opposite is a **universal product**: one feature flag for everyone, same SLA, same support load—which cutting-edge AI rarely survives without hardening.

Together, **lab + selective products** is the honest posture: **most** frontier “brain” work stays in **R&D**; **some** of it graduates into **narrow, controlled** offerings. It is not “we will never productize research”—it is “we will not pretend the lab demo is already the global product.”

The next section turns the roadmap ladder into a **concrete migration plan** from where TinyModel starts today.

## Plan: from a 2-layer BERT (scratch, one dataset) to LLMs and multimodal foundations

**Starting point:** a tiny encoder (`BertForSequenceClassification`), shallow depth, WordPiece tokenizer fit on one task, trained with standard supervised learning. **End state:** systems built on **large language models** (generation, instruction following, tools) and, where needed, **multimodal foundation models** (text + vision/audio + structured inputs).

This is not one continuous “make BERT bigger until it speaks”—it is a **sequence of capability jumps**, each with different data, compute, and code.

### Phase A — Harden the encoder lane (same family, stronger practice)

**Goal:** keep a small BERT-style stack but stop being limited to a single dataset and a toy training recipe.

- Train on **multiple classification datasets** or a **unified label schema**; standardize **eval** (per-class F1, calibration, error analysis).
- Move tokenizer + preprocessing toward **reusable pipelines** (Hub datasets, versioning, reproducible splits).
- Optionally **increase capacity slightly** (more layers/hidden size) *or* switch to **initializing from a public pretrained encoder** (e.g. small BERT/RoBERTa) and fine-tune—often beats training from scratch on limited data.

**Outcome:** a credible **embedding + classification** product lane; you are still not an LLM.

### Phase B — Generation: introduce a causal (decoder) model

**Goal:** go from “predict a class” to **predict token sequences** (the core of LLMs).

- Learn **causal language modeling** (next-token prediction) on text corpora—either:
  - **Fine-tune an open decoder** (GPT-style, Llama-class, Mistral-class, etc.) with LoRA/PEFT for cost control, or  
  - Train a **small decoder from scratch** only as an *educational or extreme-budget* path; pretraining at LLM scale needs huge data and compute.
- Add **task formats**: prompt templates, supervised fine-tune (SFT) on instruction–response pairs.

**Outcome:** you can ship **generation** (summaries, drafts, chat-shaped UIs) while reusing your data and eval discipline from Phase A.

### Phase C — “LLM product” without training a foundation model yourself

**Goal:** behave like a **general-purpose text system** in production.

- **Serve or API-call** strong open or commercial LLMs; invest in **RAG** (retrieval, chunking, citations), **guardrails**, and **observability**.
- If you must **own weights**: full fine-tune or **instruction-tune** open models on your domain; optional **preference alignment** (DPO/RLHF-style) if quality bar demands it.

**Outcome:** customers experience an **LLM-backed product**; your moat is **data, workflow, eval, and operations**, not necessarily a novel pretraining run.

### Phase D — True large-scale LLM pretraining (optional, org-scale)

**Goal:** train or continue-pretrain a **large** transformer on **web-scale or proprietary corpora**.

- Requires **massive data** (filtered Common Crawl, licensed mixes, synthetic augmentation), **multi-GPU clusters** (often thousands of GPU-hours or more), and **stability tooling** (checkpointing, monitoring, scaling laws–aware budgeting).
- This phase is **optional** for most product teams; **adapting** open LLMs (Phase C) covers most commercial needs.

**Outcome:** a **custom foundation LLM** only where regulation, IP, or latency economics justify the cost.

### Phase E — Multimodal foundation models

**Goal:** one model (or one **fused system**) that conditions on **images, audio, and/or video** together with text—without treating each modality as a separate silo forever.

Typical technical paths:

- **Vision + language:** image encoder (ViT/CLIP-style) + connector + language model (**LLaVA-style** adapters, or proprietary multimodal transformers); train on image–caption and instruction-following multimodal data.
- **Audio + language:** speech encoders (wav2vec-style, Whisper-style) feeding text decoders or unified architectures.
- **Unified transformers:** larger “native” multimodal pretraining (expensive; often starts from strong text LLMs + adapters).

**Prerequisites:** solid **Phase C** text stack (serving, safety, eval); multimodal adds **data complexity** (alignment of modalities, bias, moderation across images/audio).

**Outcome:** products that **see, hear, and read** in one interface—still governed by the same deployment and safety layers as text-only LLMs.

### How this ties back to the 2-layer BERT in this repo

| Today (TinyModel-style) | Bridge | Later (LLM / multimodal) |
|-------------------------|--------|---------------------------|
| Encoder, classification | Same **PyTorch + Transformers** skills; add **causal LM** and **prompting** | Decoder or API-served LLM |
| One dataset | **Many datasets**, versioning, eval harness | Large corpora or vendor APIs |
| Scratch tiny weights | **PEFT** on pretrained models | Full fine-tune or pretrain at scale |
| Text only | Text **RAG** and tools | **Vision/audio** adapters + multimodal data |

Skipping straight from “2-layer BERT on one dataset” to “train GPT-4” is not a plan—it is a **resource mismatch**. The plan above is **sequential**: each phase builds **data discipline, eval, and serving** that the next phase depends on.

## “Artificial brain” as a useful north star (not a marketing claim)

If you use **artificial brain** as a *design metaphor*, it helps to decompose it into engineering capabilities:

- **Perception** — text, images, audio, structured signals  
- **Memory** — retrieval over corpora, user/session state, knowledge bases  
- **Reasoning & planning** — chains of thought, tools, verifiers (often hybrid: model + code + rules)  
- **Action** — APIs, workflows, robotics, side-effecting tools (with permissions)  
- **Alignment & oversight** — policies, eval suites, human-in-the-loop  

Commercially, customers rarely buy “a brain”; they buy **reliability, latency, cost, and compliance** on a **narrow slice** of that stack—then you expand.

## What to build next in this product line (suggested)

Aligned with TinyModel’s current strengths and common demand:

- **Stronger baselines** — more datasets, metrics beyond accuracy, calibration, confusion tooling.  
- **Embedding-first products** — semantic search, dedup, clustering on top of encoder outputs (`tinymodel_runtime`-style).  
- **RAG templates** — document ingestion, chunking, evaluation (faithfulness, citation coverage).  
- **Governed assistants** — audit logs, red-teaming hooks, PII handling—often more valuable than raw model size.

That path moves you toward **general-purpose *systems*** (orchestration + data + eval) even when the **core weights** are commodity LLMs or modest encoders.

## See also (demo credibility and the Universal Brain Space)

When **buyer-facing demos** misbehave (near-uniform classifier scores, placeholder summarization, slow CPU decode, tiny FAQ corpus), triage with [`model-output-improvement-guide.md`](model-output-improvement-guide.md) before expanding model size or scope—it maps **symptoms** to **repo levers** (training, `horizon2_core`, RAG corpus, prompts).

---

*This document is planning guidance, not a commitment to any single architecture or timeline.*
