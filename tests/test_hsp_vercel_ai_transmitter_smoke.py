"""Tests for hsp_vercel_ai_transmitter_smoke.py."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


class TestHspVercelAiTransmitterSmoke(unittest.TestCase):
    def test_help(self) -> None:
        r = subprocess.run(
            [sys.executable, str(_SCRIPTS / "hsp_vercel_ai_transmitter_smoke.py"), "-h"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(r.returncode, 0)
        self.assertIn("hsp_vercel_ai_transmitter_smoke", r.stdout)


if __name__ == "__main__":
    unittest.main()
