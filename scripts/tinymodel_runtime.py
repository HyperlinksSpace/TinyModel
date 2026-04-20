#!/usr/bin/env python3
"""General-purpose TinyModel runtime utilities.

This module extends usage beyond plain classification by exposing:
- class probabilities
- sentence embeddings from the encoder
- semantic similarity scoring
- nearest-neighbor retrieval over a candidate set
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import torch
import torch.nn.functional as F
from transformers import AutoModelForSequenceClassification, AutoTokenizer


@dataclass
class RetrievalHit:
    text: str
    score: float
    index: int


class TinyModelRuntime:
    """Inference helper around TinyModel classification checkpoints."""

    def __init__(
        self,
        model_id_or_path: str,
        *,
        device: str | None = None,
        max_length: int = 128,
    ) -> None:
        self.tokenizer = AutoTokenizer.from_pretrained(model_id_or_path)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_id_or_path)
        self.model.eval()
        self.max_length = max_length

        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = torch.device(device)
        self.model.to(self.device)

    def _encoder_backbone(self):
        """Return the base encoder (BERT, DistilBERT, RoBERTa, etc.)."""
        m = self.model
        for name in ("bert", "distilbert", "roberta", "electra", "camembert", "xlm_roberta"):
            if hasattr(m, name):
                return getattr(m, name)
        raise AttributeError(
            "Could not find a supported encoder backbone on this model; "
            "embeddings need BERT/DistilBERT/RoBERTa-style checkpoints."
        )

    def classify(self, texts: Sequence[str]) -> list[dict[str, float]]:
        """Return per-label probabilities for each input text."""
        encoded = self.tokenizer(
            list(texts),
            truncation=True,
            padding=True,
            max_length=self.max_length,
            return_tensors="pt",
        )
        encoded = {k: v.to(self.device) for k, v in encoded.items()}
        with torch.inference_mode():
            logits = self.model(**encoded).logits
            probs = F.softmax(logits, dim=-1).cpu()

        id2label = self.model.config.id2label
        out: list[dict[str, float]] = []
        for row in probs:
            item = {id2label[i]: float(row[i]) for i in range(row.shape[0])}
            out.append(item)
        return out

    def embed(self, texts: Sequence[str], *, normalize: bool = True) -> torch.Tensor:
        """Generate pooled sentence embeddings from the transformer encoder ([CLS] / first token)."""
        encoded = self.tokenizer(
            list(texts),
            truncation=True,
            padding=True,
            max_length=self.max_length,
            return_tensors="pt",
        )
        encoded = {k: v.to(self.device) for k, v in encoded.items()}

        with torch.inference_mode():
            backbone = self._encoder_backbone()
            # Only pass ids/mask so DistilBERT and BERT both accept the call.
            hidden = backbone(
                input_ids=encoded["input_ids"],
                attention_mask=encoded["attention_mask"],
                return_dict=True,
            ).last_hidden_state
            cls = hidden[:, 0, :]

        if normalize:
            cls = F.normalize(cls, p=2, dim=1)
        return cls.cpu()

    def similarity(self, text_a: str, text_b: str) -> float:
        """Cosine similarity between two texts using encoder embeddings."""
        embs = self.embed([text_a, text_b], normalize=True)
        score = F.cosine_similarity(embs[0].unsqueeze(0), embs[1].unsqueeze(0))
        return float(score.item())

    def retrieve(
        self,
        query: str,
        candidates: Sequence[str],
        *,
        top_k: int = 3,
    ) -> list[RetrievalHit]:
        """Return top-k semantically closest candidates to query."""
        if not candidates:
            return []

        texts = [query, *candidates]
        embs = self.embed(texts, normalize=True)
        query_emb = embs[0:1]
        cand_embs = embs[1:]
        scores = (query_emb @ cand_embs.T).squeeze(0)
        top_k = max(1, min(top_k, scores.shape[0]))
        vals, idxs = torch.topk(scores, k=top_k)

        hits: list[RetrievalHit] = []
        for score, idx in zip(vals.tolist(), idxs.tolist()):
            hits.append(RetrievalHit(text=candidates[idx], score=float(score), index=idx))
        return hits
