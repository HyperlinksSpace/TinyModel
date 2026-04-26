# Horizon 4: multimodal grounding (image + text) — MVP

Implements a **practical** slice of [`further-development-universe-brain.md`](further-development-universe-brain.md) **Horizon 4** — conditioning on **images and text** using a **single CLIP** model (contrastive image–text alignment). **Audio**, production **moderation**, and multimodal **benchmarks** are not automated here; treat those as product/R&D follow-ups.

| Piece | File | Role |
| ----- | ---- | ---- |
| **CLI** | `scripts/horizon4_multimodal.py` | `CLIP` image + caption → `logit_image_text`; JSON artifact `horizon4_multimodal_run/1.0`. |
| **Deps** | `optional-requirements-horizon4.txt` | `Pillow` (plus `torch` + `transformers` in your environment). |

## 1) Fast self-test (no Hugging Face download)

Uses **random-initialized** `CLIPModel(CLIPConfig())` to validate tensor shapes and a finite alignment logit. **Not** a quality or embedding benchmark.

```bash
python scripts/horizon4_multimodal.py --verify
```

**Expect:** exit **0** and `.tmp/horizon4-verify/run.json` with `"verify_mode": "synthetic_random_init_no_hub"`.

On **Windows**, the script may run the synthetic forward in a **subprocess** (mitigates some PyTorch / OpenMP native crashes). The parent prints `OK (synthetic CLIP, subprocess)` when that path succeeds. If the worker still fails, a **Pillow-only** check runs: `"verify_mode": "pillow_only_fallback"` in `run.json` (no CLIP forward on that host). The script also sets `KMP_DUPLICATE_LIB_OK`, `OMP_NUM_THREADS=1`, and `MKL_THREADING_LAYER=GNU` early; for a full CLIP run on Windows, **WSL** is often the most reliable option.

**CI:** `.github/workflows/horizon4-smoke.yml` runs this only (offline, seconds; Linux runs in-process, no subprocess).

## 2) Real CLIP (Hub or cache)

**First run** downloads weights (hundreds of MB) unless cached under `~/.cache/huggingface`.

```bash
pip install -r optional-requirements-horizon4.txt
python scripts/horizon4_multimodal.py --image path/to/photo.jpg --text "a photo of a dog on a beach"
# optional:
#   HORIZON4_CLIP_MODEL=openai/clip-vit-base-patch32
```

**Output:** `.tmp/horizon4/last_run.json` (or `--output-json`).

### Optional integration check (pretrained on disk / network)

```bash
python scripts/horizon4_multimodal.py --verify-pretrained
```

**Expect:** writes under `.tmp/horizon4-verify-pretrained/run.json` with `"verify_mode": "pretrained"`. Fails if the model is not available offline and the Hub is unreachable.

## 3) How this links to the rest of the stack

- **Horizon 1/2/3** stay **text- or memory-centric**; Horizon 4 adds a **grounding** score you can use for “does this **image** match this **caption** / support ticket text?” (triaging, not sole truth).
- **Abuse and bias review** before broad launch: still required; this script does not moderate content.
- **Torch `dtype` / processor quirks:** `align_clip_image_processor` in the script helps some non-224 vision configs; OpenAI’s default CLIP uses 224×224.

## 4) Exit criteria (from the vision doc) — status

| Criterion | In this MVP |
| --------- | ------------ |
| Benchmark slice per modality | **Not** shipped; you can log `logit_image_text` over an internal set and build a slice. |
| Abuse/bias review | **Manual** / policy; not automated. |
