# What is deep learning, and how does it show up in this project?

## What deep learning is (short)

**Deep learning** is a branch of machine learning that uses **neural networks with many layers** (“deep” = stacked transformations) to learn representations from data. Instead of hand-designing every feature, the network **learns features** through **optimization**:

1. **Forward pass** — inputs flow through layers; the model produces predictions (e.g. class scores).  
2. **Loss** — a number that says how wrong the predictions are compared to targets.  
3. **Backward pass (backpropagation)** — compute how each parameter should change to reduce the loss.  
4. **Optimizer step** (e.g. AdamW) — update weights; repeat over many examples and epochs.

When the dataset and model are large enough, learned representations can capture **complex patterns** (syntax, semantics, visual edges, etc.). **GPUs/TPUs** accelerate the heavy linear algebra; **frameworks** like PyTorch implement autograd and efficient kernels.

Deep learning is **not** magic: quality depends on **data**, **architecture**, **training recipe**, and **evaluation**.

## How this project uses deep learning

**TinyModel** trains a **small BERT-style encoder** for **text classification** from scratch (not loading a pretrained BERT checkpoint). Concretely:

- **Architecture**: `BertForSequenceClassification` from Hugging Face Transformers — a **Transformer encoder** stack (self-attention + feed-forward blocks) plus a **classification head** (linear layer on top of a pooled representation, typically tied to `[CLS]`).  
- **Tokenizer**: WordPiece vocabulary **fit on your training texts** — turns raw strings into token IDs the embedding layer understands.  
- **Training loop**: For each batch, the model runs a forward pass, computes **cross-entropy loss** between logits and true labels, backpropagates, and **AdamW** updates weights — standard **supervised deep learning**.  
- **Inference**: After saving `config.json`, tokenizer files, and `model.safetensors`, you load the checkpoint and run forward passes for new text.

Relevant scripts:

- **`scripts/train_tinymodel1_classifier.py`** — dataset loading, tokenizer training, model construction, training loop, export of Hub-ready artifacts (`README.md`, `artifact.json`).  
- **`scripts/tinymodel_runtime.py`** — loads a saved checkpoint and exposes **classification probabilities** and **encoder embeddings** (via `model.bert(...)`) for similarity and retrieval.

## How you could extend “deep learning in this repo”

Without changing the philosophy of the repo, natural extensions include:

- **Train longer / more data** — same architecture, better empirical performance.  
- **Change hyperparameters** — hidden size, layers, sequence length (trade accuracy vs speed).  
- **Fine-tune a pretrained model** instead of training from scratch — different script, but same PyTorch + Transformers stack.  
- **Add metrics** — F1 per class, calibration, confusion matrix logging.  
- **Export** — ONNX or quantized models for deployment after you validate numerics.

Those steps stay firmly inside **deep learning practice**; they differ in **scale and recipe**, not in the core idea of learned representations via differentiable networks.

---

*For installation and deployment specifics, see the main repository `README.md` and internal Hugging Face notes under `texts/`.*
