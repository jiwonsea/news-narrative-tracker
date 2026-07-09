"""Naver News API collector (forward collection only).

v0.3: implemented (was a documented stub since v0.1).
v0.4: retry/backoff, rate-limit handling, and optional pagination.

- Endpoint: https://openapi.naver.com/v1/search/news.json
  Requires X-Naver-Client-Id / X-Naver-Client-Secret headers. Credentials
  are read from the NAVER_CLIENT_ID / NAVER_CLIENT_SECRET environment
  variables (never hard-coded; register them as GitHub Secrets for CI).
  Locally they can be placed in a `.env` file at the repo root, which is
  loaded automatically at import time via python-dotenv (see below).
- Like Google News RSS, the search API has NO historical backfill: results
  are current items only, so this source feeds the *forward* store. Do not
  mix its counts with GDELT share series (different universe, no
  normalization denominator).
- Dedup: Naver returns both `originallink` (publisher URL) and `link`
  (Naver mirror). We prefer originallink so the same article syndicated
  through Naver dedupes against itself; fall back to `link` when
  originallink is empty.
- Titles arrive with <b>...</b> highlight tags and HTML entities; they are
  stripped/unescaped before theme matching.
- Robustness: transient failures (network errors, HTTP 429/5xx) are retried
  with exponential backoff. The search API caps paging at start<=1000, so
  fetch_headlines can page up to 1000 items per query when asked.
"""

from __future__ import annotations

import html
import os
import re
import time
from email.utils import parsedate_to_datetime
from typing import Any, Callable, Dict, List, Optional

import requests

try:
    # Load credentials from a local .env file when present. In CI the vars
    # come from GitHub Secrets and no .env exists, so this is a harmless no-op.
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    # python-dotenv is optional; env vars can still be set by the shell/CI.
    pass

from .google_news import Headline

API_URL = "https://openapi.naver.com/v1/search/news.json"
ENV_CLIENT_ID = "NAVER_CLIENT_ID"
ENV_CLIENT_SECRET = "NAVER_CLIENT_SECRET"

# Naver Search API hard limits: display<=100 per call, start (1-based) <=1000.
MAX_DISPLAY = 100
MAX_START = 1000
# Statuses worth retrying: throttling and transient server errors.
RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})

_TAG_RE = re.compile(r"</?b>", re.IGNORECASE)


class NaverCredentialsError(RuntimeError):
    """Raised when API credentials are not configured."""


class NaverAPIError(RuntimeError):
    """Raised when the API keeps failing after all retries."""


def _credentials(
    client_id: Optional[str], client_secret: Optional[str]
) -> tuple:
    cid = client_id or os.environ.get(ENV_CLIENT_ID, "")
    secret = client_secret or os.environ.get(ENV_CLIENT_SECRET, "")
    if not cid or not secret:
        raise NaverCredentialsError(
            f"Naver API credentials missing: set {ENV_CLIENT_ID} and "
            f"{ENV_CLIENT_SECRET} environment variables (issue keys at "
            "https://developers.naver.com/apps/, Search API)."
        )
    return cid, secret


def clean_title(raw: str) -> str:
    """Strip Naver's <b> highlight tags and unescape HTML entities."""
    return html.unescape(_TAG_RE.sub("", raw or "")).strip()


def dedupe_link(item: Dict[str, Any]) -> str:
    """Canonical link for dedup: originallink first, fallback to link."""
    return (item.get("originallink") or "").strip() or (item.get("link") or "").strip()


def parse_items(items: List[Dict[str, Any]]) -> List[Headline]:
    """Convert Naver API items to Headline objects (pure, unit-testable)."""
    headlines: List[Headline] = []
    for item in items:
        link = dedupe_link(item)
        if not link:
            continue
        published = None
        pub_raw = item.get("pubDate")
        if pub_raw:
            try:
                published = parsedate_to_datetime(pub_raw)
            except (TypeError, ValueError):
                published = None
        headlines.append(
            Headline(title=clean_title(item.get("title", "")), published=published, link=link)
        )
    return headlines


def _get_page(
    sess: requests.Session,
    params: Dict[str, Any],
    headers: Dict[str, str],
    *,
    max_retries: int,
    backoff: float,
    sleep: Callable[[float], None],
) -> Dict[str, Any]:
    """One API page with retry/backoff on throttling and transient errors."""
    last_exc: Optional[BaseException] = None
    for attempt in range(max_retries + 1):
        try:
            resp = sess.get(API_URL, params=params, headers=headers, timeout=30)
        except requests.RequestException as exc:  # network/timeout
            last_exc = exc
        else:
            status = getattr(resp, "status_code", 200)
            if status in RETRY_STATUSES and attempt < max_retries:
                sleep(backoff * (2 ** attempt))
                continue
            resp.raise_for_status()
            return resp.json()
        if attempt < max_retries:
            sleep(backoff * (2 ** attempt))
    raise NaverAPIError(
        f"Naver API request failed after {max_retries + 1} attempts"
    ) from last_exc


def fetch_headlines(
    query: str,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    session: Optional[requests.Session] = None,
    display: int = 100,
    sort: str = "date",
    max_results: int = 100,
    max_retries: int = 3,
    backoff: float = 1.0,
    pause: float = 0.0,
    sleep: Callable[[float], None] = time.sleep,
) -> List[Headline]:
    """Fetch current news items for a query, paging up to ``max_results``.

    Defaults to a single page of 100 (the API max per call). Set
    ``max_results`` up to 1000 to page further; the API rejects start>1000.
    Transient failures are retried with exponential backoff. ``pause`` adds a
    politeness delay between pages. ``sleep`` is injectable for tests.
    """
    cid, secret = _credentials(client_id, client_secret)
    sess = session or requests.Session()
    headers = {"X-Naver-Client-Id": cid, "X-Naver-Client-Secret": secret}
    per_call = max(1, min(display, MAX_DISPLAY))

    headlines: List[Headline] = []
    start = 1
    while len(headlines) < max_results and start <= MAX_START:
        want = min(per_call, max_results - len(headlines), MAX_START - start + 1)
        page = _get_page(
            sess,
            {"query": query, "display": want, "start": start, "sort": sort},
            headers,
            max_retries=max_retries,
            backoff=backoff,
            sleep=sleep,
        )
        items = page.get("items", [])
        headlines.extend(parse_items(items))
        if len(items) < want:
            break  # last page: fewer items than requested
        start += want
        if pause and start <= MAX_START and len(headlines) < max_results:
            sleep(pause)

    return headlines[:max_results]
