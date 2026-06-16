"""Tests for hsp_integration_smoke.py."""

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


class TestHspIntegrationSmokeHelp(unittest.TestCase):
    def test_help(self) -> None:
        r = subprocess.run(
            [sys.executable, str(_SCRIPTS / "hsp_integration_smoke.py"), "-h"],
            capture_output=True,
            text=True,
            cwd=_REPO,
            timeout=30,
        )
        self.assertEqual(r.returncode, 0)
        self.assertIn("hsp_integration_smoke", r.stdout)


class TestHspIntegrationSmokeStdlib(unittest.TestCase):
    def test_verify_stdlib(self) -> None:
        r = subprocess.run(
            [sys.executable, str(_SCRIPTS / "hsp_integration_smoke.py"), "--verify"],
            capture_output=True,
            text=True,
            cwd=_REPO,
            timeout=300,
        )
        self.assertEqual(r.returncode, 0, f"stdout={r.stdout}\nstderr={r.stderr}")
        self.assertIn("hsp_integration_smoke verify: OK", r.stdout)
        self.assertIn("mode=stdlib", r.stdout)


@unittest.skipUnless(_TORCH, "torch not installed")
class TestHspIntegrationSmokeFull(unittest.TestCase):
    def test_verify_full(self) -> None:
        r = subprocess.run(
            [sys.executable, str(_SCRIPTS / "hsp_integration_smoke.py"), "--verify", "--full"],
            capture_output=True,
            text=True,
            cwd=_REPO,
            timeout=900,
        )
        self.assertEqual(r.returncode, 0, f"stdout={r.stdout}\nstderr={r.stderr}")
        self.assertIn("mode=full", r.stdout)


if __name__ == "__main__":
    unittest.main()
