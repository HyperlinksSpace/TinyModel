"""Unit tests for scripts/parity_check_hub_vs_local.py (no model downloads)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_REPO = Path(__file__).resolve().parent.parent
_SCRIPTS = _REPO / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import parity_check_hub_vs_local as parity  # noqa: E402


class _FakeRuntime:
    _responses = [
        [
            {"World": 0.6, "Sports": 0.2, "Business": 0.1, "Sci/Tech": 0.1},
            {"World": 0.1, "Sports": 0.7, "Business": 0.1, "Sci/Tech": 0.1},
        ],
        [
            {"World": 0.5, "Sports": 0.3, "Business": 0.1, "Sci/Tech": 0.1},
            {"World": 0.2, "Sports": 0.6, "Business": 0.1, "Sci/Tech": 0.1},
        ],
    ]
    _idx = 0

    def __init__(self, model_id_or_path: str, device: str | None = None) -> None:
        self.model_id_or_path = model_id_or_path
        self.device = device

    def classify(self, queries: list[str]) -> list[dict[str, float]]:
        out = _FakeRuntime._responses[_FakeRuntime._idx]
        _FakeRuntime._idx += 1
        return out


class _MismatchRuntime:
    def __init__(self, model_id_or_path: str, device: str | None = None) -> None:
        self.model_id_or_path = model_id_or_path
        self.device = device

    def classify(self, queries: list[str]) -> list[dict[str, float]]:
        return [{"World": 1.0}]


class TestParityHelpers(unittest.TestCase):
    def test_top_label_margin(self) -> None:
        label, conf, margin = parity._top_label({"a": 0.6, "b": 0.3, "c": 0.1})
        self.assertEqual(label, "a")
        self.assertAlmostEqual(conf, 0.6)
        self.assertAlmostEqual(margin, 0.3)

    def test_l1_distance_union_keys(self) -> None:
        d = parity._l1_distance({"a": 0.8, "b": 0.2}, {"a": 0.1, "c": 0.9})
        self.assertAlmostEqual(d, 1.8)


class TestParityMain(unittest.TestCase):
    def test_main_writes_report(self) -> None:
        _FakeRuntime._idx = 0
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "report.json"
            argv = [
                "parity_check_hub_vs_local.py",
                "--local-model",
                "local/path",
                "--hub-model",
                "HyperlinksSpace/TinyModel1",
                "--query",
                "q1",
                "--query",
                "q2",
                "--output",
                str(out),
                "--device",
                "cpu",
            ]
            with patch.object(sys, "argv", argv), patch.object(parity, "TinyModelRuntime", _FakeRuntime):
                parity.main()
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema"], "tinymodel_hub_local_parity/1.0")
            self.assertEqual(payload["summary"]["n_queries"], 2)
            self.assertAlmostEqual(payload["summary"]["top_label_match_rate"], 1.0)
            self.assertEqual(len(payload["comparisons"]), 2)

    def test_main_raises_on_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "report.json"
            argv = [
                "parity_check_hub_vs_local.py",
                "--query",
                "q1",
                "--query",
                "q2",
                "--output",
                str(out),
            ]
            with patch.object(sys, "argv", argv), patch.object(parity, "TinyModelRuntime", _MismatchRuntime):
                with self.assertRaises(RuntimeError):
                    parity.main()


if __name__ == "__main__":
    unittest.main()
