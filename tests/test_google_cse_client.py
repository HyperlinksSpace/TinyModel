"""Tests for ``scripts/google_cse_client.py`` (mocked HTTP)."""

from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock, patch

import sys
from pathlib import Path

_scripts = Path(__file__).resolve().parent.parent / "scripts"
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))

from google_cse_client import (  # noqa: E402
    format_cse_hits_markdown,
    google_cse_search,
    read_google_cse_settings,
)
class TestGoogleCseClient(unittest.TestCase):
    def test_read_settings_defaults(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            k, cx, num, safe = read_google_cse_settings()
            self.assertIsNone(k)
            self.assertIsNone(cx)
            self.assertEqual(num, 5)
            self.assertIsNone(safe)

    def test_google_cse_search_parses_items(self) -> None:
        payload = {
            "items": [
                {"title": "T1", "link": "https://a.example", "snippet": "S1"},
                {"title": "", "link": "https://b.example", "snippet": ""},
            ]
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(payload).encode()
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_resp
        mock_cm.__exit__.return_value = None

        with patch("google_cse_client.urllib.request.urlopen", return_value=mock_cm):
            hits = google_cse_search(
                "q test",
                api_key="k",
                cx="cx1",
                num=2,
                safe=None,
            )
        self.assertEqual(len(hits), 2)
        self.assertEqual(hits[0].link, "https://a.example")
        md = format_cse_hits_markdown(hits, for_chat=True)
        self.assertIn("[Web 1]", md)
        self.assertIn("https://a.example", md)

    def test_format_empty(self) -> None:
        s = format_cse_hits_markdown([], for_chat=False)
        self.assertIn("No web results", s)


if __name__ == "__main__":
    unittest.main()
