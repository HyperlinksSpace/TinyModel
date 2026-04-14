---
license: apache-2.0
library_name: transformers
datasets:
  - ag_news
tags:
  - tiny
  - text-classification
  - ag-news
---

# TinyModel1

TinyModel1 is a lightweight news-topic classifier trained from scratch on `ag_news`.

## Task

Input: short news text  
Output labels: World, Sports, Business, Sci/Tech

## Training setup

- Base model: tiny BERT from scratch
- Train samples: 3000
- Eval samples: 600
- Epochs: 2
- Batch size: 16
- Learning rate: 0.0001

## Quick metrics

- Eval accuracy: 0.5183
- Final train loss: 1.1592

## Intended use

- Fast baseline for category routing/classification
- Starter model for domain adaptation and production experiments
