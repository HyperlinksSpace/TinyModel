"""Tests for hsp_railway_deploy_smoke.py (-h only; live verify is manual/CI)."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_SCRIPTS = _REPO / "scripts"


class TestHspRailwayDeploySmokeHelp(unittest.TestCase):
    def test_help(self) -> None:
        r = subprocess.run(
            [sys.executable, str(_SCRIPTS / "hsp_railway_deploy_smoke.py"), "-h"],
            capture_output=True,
            text=True,
            cwd=_REPO,
            timeout=30,
        )
        self.assertEqual(r.returncode, 0)
        self.assertIn("hsp_railway_deploy_smoke", r.stdout)


if __name__ == "__main__":
    unittest.main()
