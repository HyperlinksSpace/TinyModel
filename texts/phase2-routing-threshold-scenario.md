# Phase 2: Example routing scenario (threshold + fallback)

This document closes the **“document one routing scenario with a chosen threshold policy and fallback action”** exit from `texts/further-development-plan.md`. Thresholds are **not** learned by training; they are a product decision tuned on a validation split.

## Scenario: news-topic triage (AG News–style)

**Goal:** Assign each incoming headline to one of four topic labels for internal routing (search indexing, section placement, or alerts).

**Policy:**

| Item | Chosen value | Rationale |
| ---- | ------------ | ---------- |
| **Winner score** | `max_prob` = largest softmax probability from `TinyModelRuntime.classify` / the classifier head | Same quantity as `calibration.max_prob_histogram` in `eval_report.json`. |
| **Minimum confidence** | `min_confidence = 0.60` | Starting point in the 0.5–0.7 range suggested in `eval_report.json` → `routing`. Tune up if too many false routes; tune down if too much traffic goes to fallback. |
| **If** `max_prob < min_confidence` | **Fallback:** do not trust the label; send the item to a **human review queue** (or a “general / unknown” bucket). | Avoids high-impact mistakes when the model is unsure. |
| **If** `max_prob >= min_confidence` | Use the **predicted class** for routing. | Normal automated path. |

**Optional stricter line:** for legally or safety-sensitive feeds, set `min_confidence = 0.70` and keep the same fallback.

## How this ties to repo artifacts

- After training, open **`eval_report.json`** and inspect:
  - **`calibration.max_prob_histogram`** — see how many eval examples land below your chosen `min_confidence`.
  - **`error_analysis.top_confusions`** — which class pairs are confused; if those pairs are costly, prefer **higher** `min_confidence` or more training data for those classes.
- **`misclassified_sample.jsonl`** — spot-check real errors; if many errors have high `max_prob`, a threshold cannot fix that (model is confidently wrong) and you need data or model changes.

## Product wiring (sketch)

```text
probs = runtime.classify([text])[0]           # label -> probability
label, max_prob = max(probs.items(), key=lambda x: x[1])
if max_prob < 0.60:
    route_to_human_review(text, probs)
else:
    route_to_topic(label, text)
```

Adjust `0.60` only after measuring precision/recall for the **automated** path on a **held-out** set.
