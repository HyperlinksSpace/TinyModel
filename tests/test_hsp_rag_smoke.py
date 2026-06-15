"""Stdlib tests for hsp_rag_smoke.py."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_SCRIPTS = _REPO / "scripts"


class TestHspRagSmoke(unittest.TestCase):
    def test_verify_script(self) -> None:
        r = subprocess.run(
            [sys.executable, str(_SCRIPTS / "hsp_rag_smoke.py"), "--verify"],
            capture_output=True,
            text=True,
            cwd=_REPO,
            timeout=30,
        )
        self.assertEqual(r.returncode, 0, f"stdout={r.stdout}\nstderr={r.stderr}")
        self.assertIn("hsp_rag verify: OK", r.stdout)

    def test_help(self) -> None:
        r = subprocess.run(
            [sys.executable, str(_SCRIPTS / "hsp_rag_smoke.py"), "-h"],
            capture_output=True,
            text=True,
            cwd=_REPO,
            timeout=30,
        )
        self.assertEqual(r.returncode, 0)
        self.assertIn("hsp_rag_smoke", r.stdout)

    def test_ad_hoc_query(self) -> None:
        r = subprocess.run(
            [
                sys.executable,
                str(_SCRIPTS / "hsp_rag_smoke.py"),
                "--query",
                "connect telegram messages",
                "--top-k",
                "1",
            ],
            capture_output=True,
            text=True,
            cwd=_REPO,
            timeout=30,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Connect Telegram", r.stdout)


if __name__ == "__main__":
    unittest.main()
