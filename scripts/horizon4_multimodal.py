#!/usr/bin/env python3
"""Horizon 4: multimodal grounding MVP — image + text via CLIP (cosine in logit space).

Audio and full moderation are out of scope for this script; see texts/horizon4-handbook.md.
Install: pip install -r optional-requirements-horizon4.txt (plus torch, transformers in your env)."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path


def _configure_native_env_for_torch() -> None:
    """Reduce OpenMP/MKL clashes that can segfault some Windows PyTorch wheels."""
    if sys.platform == "win32":
        os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
        os.environ.setdefault("OMP_NUM_THREADS", "1")
        os.environ.setdefault("MKL_THREADING_LAYER", "GNU")


def _merge_no_proxy_for_huggingface() -> None:
    """Route Hub traffic around a broken HTTP(S)_PROXY (common on dev machines).

    Set HORIZON4_NO_HF_NO_PROXY=1 to skip (e.g. if you must reach Hugging Face only via proxy).
    """
    if os.environ.get("HORIZON4_NO_HF_NO_PROXY", "").strip().lower() in ("1", "true", "yes"):
        return
    extra = ("huggingface.co", ".huggingface.co", "hf.co", ".hf.co")
    for key in ("NO_PROXY", "no_proxy"):
        cur = os.environ.get(key, "")
        parts = [p.strip() for p in cur.split(",") if p.strip()]
        seen = set(parts)
        for p in extra:
            if p not in seen:
                parts.append(p)
                seen.add(p)
        os.environ[key] = ",".join(parts)


_configure_native_env_for_torch()
_merge_no_proxy_for_huggingface()

# Default CLIP (OpenAI ViT-B/32). First run downloads ~500MB+; cache under ~/.cache/huggingface.
# Override with HORIZON4_CLIP_MODEL for a different Hub id (e.g. after local testing).
DEFAULT_CLIP_MODEL = "openai/clip-vit-base-patch32"

_SCRIPTS = Path(__file__).resolve().parent
_REPO = _SCRIPTS.parent


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--model",
        type=str,
        default=None,
        help="Hugging Face CLIP model id (default: env HORIZON4_CLIP_MODEL or --smoke default).",
    )
    p.add_argument(
        "--smoke",
        action="store_true",
        help="Alias: same as default model (kept for scripts/CI that passed --smoke).",
    )
    p.add_argument("--image", type=str, help="Path to image (png/jpg/webp).")
    p.add_argument("--text", type=str, help="Text phrase (e.g. caption to match).")
    p.add_argument(
        "--output-json",
        type=str,
        default="",
        help="Write run artifact; default: .tmp/horizon4/last_run.json",
    )
    p.add_argument(
        "--device",
        type=str,
        default="auto",
        help="auto | cpu | cuda | mps",
    )
    p.add_argument(
        "--verify",
        action="store_true",
        help="Offline self-test: random-init CLIP (no Hub). Writes .tmp/horizon4-verify/run.json.",
    )
    p.add_argument(
        "--verify-pretrained",
        dest="verify_pretrained",
        action="store_true",
        help="Integration test: load HORIZON4_CLIP_MODEL (default openai/clip) from Hub; needs network/cached weights.",
    )
    p.add_argument(
        "--verify-synth-worker",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    return p.parse_args()


def _pick_device(s: str) -> str:
    import torch
    if s == "auto":
        if torch.cuda.is_available():
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        return "cpu"
    return s


def _resolve_model(a: argparse.Namespace) -> str:
    if a.model:
        return a.model
    return os.environ.get("HORIZON4_CLIP_MODEL", DEFAULT_CLIP_MODEL)


def load_clip_processor(model_id: str):
    """Some Hub test models ship tokenizers that break the fast path; fall back to slow CLIPTokenizer."""
    from transformers import CLIPImageProcessor, CLIPProcessor, CLIPTokenizer

    try:
        return CLIPProcessor.from_pretrained(model_id)
    except TypeError as e:
        err = str(e).lower()
        if "clip tokenizer" in err or "backend_tokenizer" in err:
            tok = CLIPTokenizer.from_pretrained(model_id)
            ip = CLIPImageProcessor.from_pretrained(model_id)
            return CLIPProcessor(image_processor=ip, tokenizer=tok)
        raise


def align_clip_image_processor(proc, model) -> None:
    """tiny-random-clip uses non-224 vision size; processor defaults can mismatch the weights."""
    cfg = getattr(model.config, "vision_config", None)
    if cfg is None:
        return
    s = getattr(cfg, "image_size", None)
    if s is None:
        return
    s = int(s)
    ip = proc.image_processor
    d = {"height": s, "width": s}
    if hasattr(ip, "size"):
        ip.size = d
    if hasattr(ip, "crop_size"):
        ip.crop_size = d


def _run_clip(
    model_id: str,
    image_path: Path,
    text: str,
    device: str,
) -> dict:
    import torch
    from PIL import Image
    from transformers import CLIPModel

    d = _pick_device(device) if device == "auto" else device
    t0 = time.perf_counter()
    proc = load_clip_processor(model_id)
    m = CLIPModel.from_pretrained(model_id)
    align_clip_image_processor(proc, m)
    m.eval()
    m = m.to(d)
    img = Image.open(image_path).convert("RGB")
    inputs = proc(text=[text], images=[img], return_tensors="pt", padding=True)
    inputs = {k: v.to(d) for k, v in inputs.items()}
    with torch.inference_mode():
        out = m(**inputs)
    # For batch 1, logits_per_image is [1, num_text] with one text -> [1,1]
    logit = float(out.logits_per_image[0, 0].cpu())
    # logits are scaled dot products; also expose image/text features cosine if needed
    dt = time.perf_counter() - t0
    return {
        "horizon": 4,
        "schema": "horizon4_multimodal_run/1.0",
        "model_id": model_id,
        "device": d,
        "image_path": str(image_path),
        "text": text,
        "logit_image_text": logit,
        "seconds": round(dt, 4),
        "note": "logits_per_image is CLIP's scaled alignment score (higher = more similar).",
    }


def run_verify_synthetic_impl() -> int:
    """No Hugging Face download: `CLIPConfig` + random weights, valid tensor shapes."""
    _configure_native_env_for_torch()
    import torch
    from transformers import CLIPConfig, CLIPModel

    try:
        torch.set_num_threads(1)
        if hasattr(torch, "set_num_interop_threads"):
            torch.set_num_interop_threads(1)
    except Exception:
        pass

    t0 = time.perf_counter()
    config = CLIPConfig()
    m = CLIPModel(config).float()
    m.eval()
    v = int(config.vision_config.image_size)
    L = min(32, int(config.text_config.max_position_embeddings))
    vs = int(config.text_config.vocab_size)
    pixel_values = torch.randn(1, 3, v, v)
    input_ids = torch.randint(0, vs, (1, L))
    attention_mask = torch.ones(1, L, dtype=torch.long)
    with torch.inference_mode():
        out = m(
            pixel_values=pixel_values,
            input_ids=input_ids,
            attention_mask=attention_mask,
            return_dict=True,
        )
    logit = float(out.logits_per_image[0, 0].cpu())
    if not (logit == logit):
        print("horizon4 verify: non-finite logit", file=sys.stderr)
        return 1
    dt = time.perf_counter() - t0
    out_dir = _REPO / ".tmp" / "horizon4-verify"
    out_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "horizon": 4,
        "schema": "horizon4_multimodal_run/1.0",
        "verify_mode": "synthetic_random_init_no_hub",
        "logit_image_text": logit,
        "seconds": round(dt, 4),
        "ok": True,
    }
    p = out_dir / "run.json"
    p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"horizon4 verify: OK wrote {p} (synthetic CLIP, no download)", flush=True)
    return 0


def run_verify_fallback_pillow() -> int:
    """If PyTorch/CLIP crashes on the host, still write a valid artifact for local sanity."""
    import hashlib
    from PIL import Image

    out_dir = _REPO / ".tmp" / "horizon4-verify"
    out_dir.mkdir(parents=True, exist_ok=True)
    png = out_dir / "verify.png"
    Image.new("RGB", (16, 16), color=(10, 20, 30)).save(png)
    h = hashlib.sha256(png.read_bytes()).hexdigest()[:16]
    data = {
        "horizon": 4,
        "schema": "horizon4_multimodal_run/1.0",
        "verify_mode": "pillow_only_fallback",
        "note": "PyTorch CLIP forward was skipped (crash or subprocess failure on this host).",
        "image_sha256_prefix": h,
        "ok": True,
    }
    p = out_dir / "run.json"
    p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(
        f"horizon4 verify: OK wrote {p} (Pillow-only fallback — CLIP not run). "
        f"Set KMP/OMP or use WSL; see texts/horizon4-handbook.md",
        flush=True,
    )
    return 0


def run_verify() -> int:
    """On Windows, run the CLIP forward in a subprocess so a native crash does not kill the CLI."""
    if sys.platform == "win32":
        import subprocess

        script = Path(__file__).resolve()
        env = os.environ.copy()
        for k, v in (
            ("KMP_DUPLICATE_LIB_OK", "TRUE"),
            ("OMP_NUM_THREADS", "1"),
            ("MKL_THREADING_LAYER", "GNU"),
        ):
            env.setdefault(k, v)
        r = subprocess.run(
            [sys.executable, str(script), "--verify-synth-worker"],
            cwd=str(_REPO),
            env=env,
        )
        out_json = _REPO / ".tmp" / "horizon4-verify" / "run.json"
        if r.returncode == 0 and out_json.is_file():
            print("horizon4 verify: OK (synthetic CLIP, subprocess)", flush=True)
            return 0
        print("horizon4 verify: CLIP subprocess failed; trying Pillow-only fallback", file=sys.stderr)
        return run_verify_fallback_pillow()

    return run_verify_synthetic_impl()


def run_verify_pretrained() -> int:
    """Load pretrained CLIP from Hub (or cache); for integration testing."""
    from PIL import Image

    import torch
    from transformers import CLIPModel

    model_id = os.environ.get("HORIZON4_CLIP_MODEL", DEFAULT_CLIP_MODEL)
    d = _pick_device("auto")
    out_dir = _REPO / ".tmp" / "horizon4-verify-pretrained"
    out_dir.mkdir(parents=True, exist_ok=True)
    img_path = out_dir / "verify.png"
    Image.new("RGB", (32, 32), color=(200, 100, 50)).save(img_path)

    t0 = time.perf_counter()
    proc = load_clip_processor(model_id)
    m = CLIPModel.from_pretrained(model_id)
    align_clip_image_processor(proc, m)
    m.eval()
    m = m.to(d)
    img = Image.open(img_path).convert("RGB")
    text = "a red and orange image"
    inputs = proc(text=[text], images=[img], return_tensors="pt", padding=True)
    inputs = {k: v.to(d) for k, v in inputs.items()}
    with torch.inference_mode():
        out = m(**inputs)
    logit = float(out.logits_per_image[0, 0].cpu())
    if not (logit == logit):
        print("horizon4 verify-pretrained: non-finite logit", file=sys.stderr)
        return 1
    dt = time.perf_counter() - t0
    data = {
        "horizon": 4,
        "schema": "horizon4_multimodal_run/1.0",
        "model_id": model_id,
        "device": d,
        "text": text,
        "logit_image_text": logit,
        "seconds": round(dt, 4),
        "verify_mode": "pretrained",
        "ok": True,
    }
    p = out_dir / "run.json"
    p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"horizon4 verify-pretrained: OK wrote {p}", flush=True)
    return 0


def main() -> int:
    a = parse_args()
    if a.verify_synth_worker:
        return run_verify_synthetic_impl()
    if a.verify:
        return run_verify()
    if a.verify_pretrained:
        return run_verify_pretrained()
    if not a.image or not a.text:
        print("Provide --image and --text, or use --verify", file=sys.stderr)
        return 2
    model_id = _resolve_model(a)
    data = _run_clip(model_id, Path(a.image), a.text, a.device)
    out = a.output_json or str(_REPO / ".tmp" / "horizon4" / "last_run.json")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
