"""Tests for hsp_rag_hybrid_smoke.py (help stdlib-only; verify needs torch)."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_SCRIPTS = _REPO / "scripts"

try:
    import torch  # noqa: F401

    _TORCH = True
except ImportError:
    _TORCH = False


class TestHspRagHybridSmokeHelp(unittest.TestCase):
    def test_help(self) -> None:
        r = subprocess.run(
            [sys.executable, str(_SCRIPTS / "hsp_rag_hybrid_smoke.py"), "-h"],
            capture_output=True,
            text=True,
            cwd=_REPO,
            timeout=30,
        )
        self.assertEqual(r.returncode, 0)
        self.assertIn("hsp_rag_hybrid_smoke", r.stdout)


@unittest.skipUnless(_TORCH, "torch not installed")
class TestHspRagHybridSmokeVerify(unittest.TestCase):
    def test_verify_hybrid(self) -> None:
        r = subprocess.run(
            [sys.executable, str(_SCRIPTS / "hsp_rag_hybrid_smoke.py"), "--verify"],
            capture_output=True,
            text=True,
            cwd=_REPO,
            timeout=600,
        )
        self.assertEqual(r.returncode, 0, f"stdout={r.stdout}\nstderr={r.stderr}")
        self.assertIn("hsp_rag_hybrid_smoke verify: OK", r.stdout)


if __name__ == "__main__":
    unittest.main()
