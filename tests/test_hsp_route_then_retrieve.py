"""Tests for hsp_route_then_retrieve.py (help stdlib-only; verify needs torch)."""

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


class TestHspRouteThenRetrieveHelp(unittest.TestCase):
    def test_help(self) -> None:
        r = subprocess.run(
            [sys.executable, str(_SCRIPTS / "hsp_route_then_retrieve.py"), "-h"],
            capture_output=True,
            text=True,
            cwd=_REPO,
            timeout=30,
        )
        self.assertEqual(r.returncode, 0)
        self.assertIn("hsp_route_then_retrieve", r.stdout)


@unittest.skipUnless(_TORCH, "torch not installed")
class TestHspRouteThenRetrieveVerify(unittest.TestCase):
    def test_verify(self) -> None:
        r = subprocess.run(
            [sys.executable, str(_SCRIPTS / "hsp_route_then_retrieve.py"), "--verify"],
            capture_output=True,
            text=True,
            cwd=_REPO,
            timeout=600,
        )
        self.assertEqual(r.returncode, 0, f"stdout={r.stdout}\nstderr={r.stderr}")
        self.assertIn("hsp_route_then_retrieve verify: OK", r.stdout)


if __name__ == "__main__":
    unittest.main()
