# Universal Brain model profiles

Optional **generative model tiers** for Universal Brain and Horizon 2 scripts. Set via environment variables (Space secrets or local shell).

| Profile | Env var | Purpose |
| ------- | ------- | ------- |
| **Balanced (default)** | `HORIZON2_MODEL` | Current default instruct LM (`HuggingFaceTB/SmolLM2-360M-Instruct` if unset) |
| **Fast** | `HORIZON2_MODEL_FAST` | Lower latency / smaller model for smoke and high-volume routes |
| **Quality** | `HORIZON2_MODEL_QUALITY` | Larger instruct model when GPU memory allows |

Select profile with **`HORIZON2_PROFILE`**: `balanced` (default), `fast`, or `quality`.

Example (local):

```bash
export HORIZON2_MODEL_FAST=HuggingFaceTB/SmolLM2-360M-Instruct
export HORIZON2_MODEL_QUALITY=Qwen/Qwen2.5-1.5B-Instruct
export HORIZON2_PROFILE=quality
python scripts/universal_brain_chat.py
```

Resolver: `resolve_instruction_model()` in [`scripts/horizon2_core.py`](../scripts/horizon2_core.py).

Golden-prompt regression (stdlib): `python scripts/ub_eval_runner.py --verify`
