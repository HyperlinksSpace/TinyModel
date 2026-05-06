"""Top-level --help for ``scripts/rag_faq_smoke.py`` (no torch until ``main()``)."""

from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_REPO = Path(__file__).resolve().parent.parent
_SCRIPTS = _REPO / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import rag_faq_smoke as rfs  # noqa: E402


class TestRagFaqSmokeHelp(unittest.TestCase):
    def test_help_lists_query_and_model_defaults(self) -> None:
        out = io.StringIO()
        err = io.StringIO()
        with patch.object(sys, "argv", ["rag_faq_smoke.py", "-h"]):
            with patch.object(sys, "stdout", out), patch.object(sys, "stderr", err):
                with self.assertRaises(SystemExit) as ctx:
                    rfs.parse_args()
        self.assertEqual(ctx.exception.code, 0)
        combined = out.getvalue() + err.getvalue()
        self.assertIn("--query", combined)
        self.assertIn("--show-train-routing", combined)
        self.assertIn("rag_faq_smoke.py", combined)


if __name__ == "__main__":
    unittest.main()
