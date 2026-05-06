"""Top-level --help for ``scripts/horizon3_memory_api.py`` (stdlib store only at import)."""

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

import horizon3_memory_api as h3api  # noqa: E402


class TestHorizon3MemoryApiHelp(unittest.TestCase):
    def test_help_lists_db_port_and_swagger(self) -> None:
        out = io.StringIO()
        err = io.StringIO()
        with patch.object(sys, "argv", ["horizon3_memory_api.py", "-h"]):
            with patch.object(sys, "stdout", out), patch.object(sys, "stderr", err):
                with self.assertRaises(SystemExit) as ctx:
                    h3api.parse_args()
        self.assertEqual(ctx.exception.code, 0)
        combined = out.getvalue() + err.getvalue()
        self.assertIn("--db", combined)
        self.assertIn("--port", combined)
        self.assertIn("8767", combined)
        self.assertIn("optional-requirements-phase3.txt", combined)


if __name__ == "__main__":
    unittest.main()
