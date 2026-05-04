"""Regression tests for ``scripts/eval_report_routing`` (stdlib only; no torch).

Covers tip-path helpers, ``load_routing_from_eval_report``, ``print_routing_policy_from_checkpoint_tip``,
``maybe_print_routing_section`` (stdout/stderr behaviour), stale ``eval_report.json`` shapes
(no dict top-level ``routing``), path-is-file (not a checkpoint dir), and empty ``routing`` dict ``{}``.
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_SCRIPTS = _REPO / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from eval_report_routing import (  # noqa: E402
    format_checkpoint_tip_path,
    format_routing_policy_from_checkpoint_command,
    load_routing_from_eval_report,
    maybe_print_routing_section,
    print_routing_policy_from_checkpoint_tip,
)


class TestFormatCheckpointTipPath(unittest.TestCase):
    def test_relative_under_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            sub = root / "out" / "ckpt"
            sub.mkdir(parents=True)
            rel = format_checkpoint_tip_path(sub, cwd=root)
            self.assertEqual(rel, "out/ckpt")

    def test_absolute_when_not_under_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as td_a, tempfile.TemporaryDirectory() as td_b:
            a = Path(td_a).resolve()
            b = (Path(td_b).resolve() / "x")
            b.mkdir()
            self.assertEqual(
                format_checkpoint_tip_path(b, cwd=a),
                b.resolve().as_posix(),
            )


class TestFormatRoutingPolicyCommand(unittest.TestCase):
    def test_contains_subpath(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            ckpt = root / "m"
            ckpt.mkdir()
            cmd = format_routing_policy_from_checkpoint_command(ckpt, cwd=root)
            self.assertIn("python scripts/routing_policy.py --from-checkpoint m", cmd)


class TestLoadRoutingFromEvalReport(unittest.TestCase):
    def test_file_path_not_directory_returns_none(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
            f.write(b"{}")
            path = f.name
        try:
            self.assertIsNone(load_routing_from_eval_report(path))
        finally:
            Path(path).unlink(missing_ok=True)

    def test_missing_dir_returns_none(self) -> None:
        self.assertIsNone(load_routing_from_eval_report("/nonexistent/path/xyz"))

    def test_no_eval_report_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            self.assertIsNone(load_routing_from_eval_report(d))

    def test_invalid_json_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "eval_report.json").write_text("{not json", encoding="utf-8")
            self.assertIsNone(load_routing_from_eval_report(d))

    def test_non_dict_routing_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "eval_report.json").write_text(
                json.dumps({"routing": "bad"}),
                encoding="utf-8",
            )
            self.assertIsNone(load_routing_from_eval_report(d))

    def test_no_routing_key_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "eval_report.json").write_text(
                json.dumps({"eval_accuracy": 0.9}),
                encoding="utf-8",
            )
            self.assertIsNone(load_routing_from_eval_report(d))

    def test_routing_null_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "eval_report.json").write_text(
                json.dumps({"routing": None}),
                encoding="utf-8",
            )
            self.assertIsNone(load_routing_from_eval_report(d))

    def test_returns_routing_dict(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            want = {"min_confidence": 0.5}
            (d / "eval_report.json").write_text(
                json.dumps({"routing": want}),
                encoding="utf-8",
            )
            got = load_routing_from_eval_report(d)
            self.assertEqual(got, want)

    def test_empty_routing_dict_returned(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "eval_report.json").write_text(
                json.dumps({"routing": {}}),
                encoding="utf-8",
            )
            got = load_routing_from_eval_report(d)
            self.assertEqual(got, {})


class TestMaybePrintRoutingSection(unittest.TestCase):
    def test_disabled_emits_nothing(self) -> None:
        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            maybe_print_routing_section("/nonexistent/x", enabled=False, prog="t")
        self.assertEqual(out.getvalue(), "")
        self.assertEqual(err.getvalue(), "")

    def test_enabled_missing_report_stderr(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            out = io.StringIO()
            err = io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                maybe_print_routing_section(str(d), enabled=True, prog="smoke_test")
            self.assertEqual(out.getvalue(), "")
            self.assertIn("smoke_test", err.getvalue())
            self.assertIn("no eval_report.json", err.getvalue())

    def test_enabled_prints_routing_banner(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "eval_report.json").write_text(
                json.dumps({"routing": {"min_confidence": 0.4}}),
                encoding="utf-8",
            )
            out = io.StringIO()
            err = io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                maybe_print_routing_section(str(d), enabled=True, prog="p")
            self.assertEqual(err.getvalue(), "")
            self.assertIn("eval_report.json routing", out.getvalue())
            self.assertIn("min_confidence", out.getvalue())

    def test_enabled_stale_report_no_dict_routing_stderr(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "eval_report.json").write_text(
                json.dumps({"eval_accuracy": 0.99, "routing": None}),
                encoding="utf-8",
            )
            out = io.StringIO()
            err = io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                maybe_print_routing_section(str(d), enabled=True, prog="stale")
            self.assertEqual(out.getvalue(), "")
            self.assertIn("stale", err.getvalue())
            self.assertIn("no eval_report.json", err.getvalue())

    def test_enabled_empty_routing_dict_prints_json(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "eval_report.json").write_text(
                json.dumps({"routing": {}}),
                encoding="utf-8",
            )
            out = io.StringIO()
            err = io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                maybe_print_routing_section(str(d), enabled=True, prog="p")
            self.assertEqual(err.getvalue(), "")
            self.assertIn("eval_report.json routing", out.getvalue())
            self.assertIn("{}", out.getvalue())


class TestPrintRoutingTip(unittest.TestCase):
    def test_prints_command(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            ckpt = root / "z"
            ckpt.mkdir()
            buf = io.StringIO()
            with redirect_stdout(buf):
                print_routing_policy_from_checkpoint_tip(ckpt, cwd=root, headline="H:")
            out = buf.getvalue()
            self.assertIn("H:", out)
            self.assertIn("routing_policy.py --from-checkpoint z", out)


if __name__ == "__main__":
    unittest.main()
