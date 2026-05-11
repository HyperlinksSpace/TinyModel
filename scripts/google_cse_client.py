"""Google Programmable Search Engine (Custom Search JSON API) — minimal stdlib client.

Env (see also `universal_brain_chat` / Space README):
  GOOGLE_CSE_API_KEY — required
  GOOGLE_CSE_CX — Programmable Search Engine id (required)
  GOOGLE_CSE_NUM — optional, 1–10 (default 5)
  GOOGLE_CSE_SAFE — optional, e.g. ``off`` or ``active`` (see Google ``cse.list`` reference)
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

_CSE_ENDPOINT = "https://www.googleapis.com/customsearch/v1"
_DEFAULT_UA = "TinyModel-UniversalBrain/1.0 (+https://github.com/HyperlinksSpace/TinyModel)"


@dataclass(frozen=True)
class CSEHit:
    title: str
    link: str
    snippet: str


def read_google_cse_settings() -> tuple[str | None, str | None, int, str | None]:
    key = (os.environ.get("GOOGLE_CSE_API_KEY") or "").strip() or None
    cx = (os.environ.get("GOOGLE_CSE_CX") or "").strip() or None
    raw_n = (os.environ.get("GOOGLE_CSE_NUM") or "5").strip()
    try:
        num = max(1, min(10, int(raw_n)))
    except ValueError:
        num = 5
    safe_raw = (os.environ.get("GOOGLE_CSE_SAFE") or "").strip()
    safe = safe_raw or None
    return key, cx, num, safe


def google_cse_search(
    query: str,
    *,
    api_key: str,
    cx: str,
    num: int = 5,
    safe: str | None = None,
    timeout_sec: float = 20.0,
) -> list[CSEHit]:
    q = (query or "").strip()
    if not q:
        return []
    n = max(1, min(10, num))
    params: dict[str, str] = {"key": api_key, "cx": cx, "q": q, "num": str(n)}
    if safe:
        params["safe"] = safe
    url = f"{_CSE_ENDPOINT}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": _DEFAULT_UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        try:
            err = json.loads(body).get("error", {})
            msg = err.get("message", body[:500])
        except json.JSONDecodeError:
            msg = body[:500] or str(e)
        raise RuntimeError(f"Google CSE HTTP {e.code}: {msg}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Google CSE network error: {e}") from e

    data = json.loads(raw)
    if isinstance(data, dict) and "error" in data:
        err = data.get("error") or {}
        msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
        raise RuntimeError(f"Google CSE API error: {msg}")

    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return []

    out: list[CSEHit] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        title = str(it.get("title") or "").strip()
        link = str(it.get("link") or "").strip()
        snippet = str(it.get("snippet") or "").strip()
        if link:
            out.append(CSEHit(title=title or "(no title)", link=link, snippet=snippet))
    return out


def format_cse_hits_markdown(hits: list[CSEHit], *, for_chat: bool) -> str:
    """Markdown block: either standalone (/web) or system-context injection."""
    if not hits:
        return "(No web results.)"
    lines: list[str] = []
    if for_chat:
        lines.append(
            "### Web search snippets (Google Programmable Search)\n"
            "Ground factual claims that depend on current or external information in these excerpts when they "
            "apply. Cite sources as **[Web n]** and include the page URL. If snippets are insufficient, say so."
        )
    else:
        lines.append("### Google web search results\n")
    for i, h in enumerate(hits, 1):
        lines.append(
            f"**[Web {i}]** {h.title}\n"
            f"- **URL:** {h.link}\n"
            f"- **Snippet:** {h.snippet}\n"
        )
    return "\n".join(lines).strip()
