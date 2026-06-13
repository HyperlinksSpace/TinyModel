"""Tests for ub_eval_runner.py (stdlib paths)."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_SCRIPTS = _REPO / "scripts"
_GOLDEN = _REPO / "texts" / "golden-prompts"


class TestUbEvalRunnerHelp(unittest.TestCase):
    def test_help_exits_zero(self) -> None:
        r = subprocess.run(
            [sys.executable, str(_SCRIPTS / "ub_eval_runner.py"), "-h"],
            capture_output=True,
            text=True,
            cwd=_REPO,
            timeout=30,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("ub_eval_runner", r.stdout)
        self.assertIn("--verify", r.stdout)


class TestUbEvalRunnerVerify(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not (_GOLDEN / "nl_signals.jsonl").is_file():
            subprocess.run(
                [sys.executable, str(_SCRIPTS / "seed_golden_prompts.py")],
                cwd=_REPO,
                check=True,
                timeout=60,
            )

    def test_verify_passes(self) -> None:
        r = subprocess.run(
            [
                sys.executable,
                str(_SCRIPTS / "ub_eval_runner.py"),
                "--verify",
                "--output-json",
                str(_REPO / ".tmp" / "ub-eval-test" / "run.json"),
            ],
            capture_output=True,
            text=True,
            cwd=_REPO,
            timeout=120,
        )
        self.assertEqual(r.returncode, 0, f"stdout={r.stdout}\nstderr={r.stderr}")
        self.assertIn("ub_eval verify: OK", r.stdout)
        out = _REPO / ".tmp" / "ub-eval-test" / "run.json"
        data = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(data["schema"], "ub_eval_run/1.0")
        self.assertGreaterEqual(data["summary"]["pass_rate"], 0.95)


class TestGoldenPromptManifest(unittest.TestCase):
    def test_manifest_counts(self) -> None:
        manifest = json.loads((_GOLDEN / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["counts"]["nl_signals"], 100)
        self.assertEqual(manifest["counts"]["routing"], 100)
        self.assertEqual(manifest["counts"]["e2e"], 100)


if __name__ == "__main__":
    unittest.main()
