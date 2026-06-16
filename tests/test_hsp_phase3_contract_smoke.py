"""Stdlib tests for hsp_phase3_contract_smoke.py."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_SCRIPTS = _REPO / "scripts"


class TestHspPhase3ContractSmoke(unittest.TestCase):
    def test_verify(self) -> None:
        r = subprocess.run(
            [sys.executable, str(_SCRIPTS / "hsp_phase3_contract_smoke.py"), "--verify"],
            capture_output=True,
            text=True,
            cwd=_REPO,
            timeout=30,
        )
        self.assertEqual(r.returncode, 0, f"stdout={r.stdout}\nstderr={r.stderr}")
        self.assertIn("hsp_phase3_contract_smoke verify: OK", r.stdout)

    def test_help(self) -> None:
        r = subprocess.run(
            [sys.executable, str(_SCRIPTS / "hsp_phase3_contract_smoke.py"), "-h"],
            capture_output=True,
            text=True,
            cwd=_REPO,
            timeout=30,
        )
        self.assertEqual(r.returncode, 0)
        self.assertIn("hsp_phase3_contract_smoke", r.stdout)


if __name__ == "__main__":
    unittest.main()
