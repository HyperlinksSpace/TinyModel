# Labeling and data hygiene (lightweight)

Use this when you move beyond public Hub benchmarks and add **custom** or **weakly supervised** labels.

## 1) One-page label guide (template)

Before scaling annotation, write down:

- **Task** — One sentence: what each example is labeled *for* (e.g. “intent for support routing”).
- **Classes** — Closed set of labels; definitions with **one positive and one negative** example each.
- **Edge cases** — What to do with mixed language, empty text, URLs-only, PII — even if the answer is “discard” or “mark `unknown`”.
- **Who decides ties** — Single owner or majority vote; revision process when definitions change.

Keep the guide **versioned** (date + semver in the filename or git tag) when definitions change.

## 2) Versioned snapshots

Treat datasets like code:

- **Frozen splits** — Export train/validation/test to dated files (JSONL, Parquet, or a pinned Hub dataset revision) when you report metrics.
- **Reproducibility** — Record script version, `--seed`, and row counts (see `eval_report.json` from training scripts).
- **Changelog** — Short note when labels are relabeled, merged, or dropped.

## 3) Avoid train / validation / test leakage

- **Document-level** — Do not put the same document (or near-duplicate) in more than one split. Shuffling lines is not enough if chunks came from one doc.
- **User or session** — If data is per-user, keep all rows for a user in one split so the model is not evaluated on seen users’ other messages.
- **Time** — For streams, prefer **time-based** splits (train on older, test on newer) when the product cares about future behavior.
- **Synthetic augmentation** — If you duplicate or paraphrase, keep derived rows in the **same** split as the source.

## 4) Weak supervision and LLM labels

If you use rules, LLMs, or distant supervision:

- **Spot-check** a random sample and track **error rate by class**.
- **Monitor drift** when upstream rules or models change.

---

*This is operational guidance, not legal advice; align retention and PII handling with your policies.*
