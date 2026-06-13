"""Stdlib tests for hsp_program_corpus.md and hsp_corpus_smoke.py -h."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_SCRIPTS = _REPO / "scripts"
_CORPUS = _REPO / "texts" / "hsp_program_corpus.md"


class TestHspCorpusSmoke(unittest.TestCase):
    def test_corpus_exists_and_has_sections(self) -> None:
        self.assertTrue(_CORPUS.is_file())
        text = _CORPUS.read_text(encoding="utf-8")
        self.assertIn("## AI and Search", text)
        self.assertGreaterEqual(text.count("\n## "), 8)

    def test_verify_script(self) -> None:
        r = subprocess.run(
            [sys.executable, str(_SCRIPTS / "hsp_corpus_smoke.py"), "--verify"],
            capture_output=True,
            text=True,
            cwd=_REPO,
            timeout=30,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("hsp_corpus verify: OK", r.stdout)

    def test_help(self) -> None:
        r = subprocess.run(
            [sys.executable, str(_SCRIPTS / "hsp_corpus_smoke.py"), "-h"],
            capture_output=True,
            text=True,
            cwd=_REPO,
            timeout=30,
        )
        self.assertEqual(r.returncode, 0)
        self.assertIn("hsp_corpus_smoke", r.stdout)


if __name__ == "__main__":
    unittest.main()
