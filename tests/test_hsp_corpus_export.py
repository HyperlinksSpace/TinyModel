"""Stdlib tests for hsp_corpus_export.py."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_SCRIPTS = _REPO / "scripts"


class TestHspCorpusExport(unittest.TestCase):
    def test_help(self) -> None:
        r = subprocess.run(
            [sys.executable, str(_SCRIPTS / "hsp_corpus_export.py"), "-h"],
            capture_output=True,
            text=True,
            cwd=_REPO,
            timeout=30,
        )
        self.assertEqual(r.returncode, 0)
        self.assertIn("hsp_corpus_export", r.stdout)

    def test_verify(self) -> None:
        r = subprocess.run(
            [
                sys.executable,
                str(_SCRIPTS / "hsp_corpus_export.py"),
                "--verify",
                "--output",
                ".tmp/hsp-corpus-export-test.json",
            ],
            capture_output=True,
            text=True,
            cwd=_REPO,
            timeout=30,
        )
        self.assertEqual(r.returncode, 0, f"stdout={r.stdout}\nstderr={r.stderr}")
        self.assertIn("hsp_corpus_export verify: OK", r.stdout)


if __name__ == "__main__":
    unittest.main()
