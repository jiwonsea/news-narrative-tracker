"""GDELT DOC 2.0 API client.

GDELT is the primary source for this project because it is free and,
critically, supports retrospective queries (STARTDATETIME/ENDDATETIME back
to 2017), which makes historical narrative reconstruction possible.

API reference: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/

Notes discovered during development:
- Rate limit: max ~1 request / 5 seconds per IP. We sleep between calls
  and retry on the rate-limit message.
- Quoted phrases must be multi-word; a quoted single short word
  (e.g. "Oklo") returns "The specified phrase is too short."
- `value` is the daily article count matching the query;
  `norm` is the total number of articles GDELT monitored that day,
  which lets us compute a normalized share (count / norm).
- The timeline occasionally has gaps of missing days (GDELT-side outages,
  e.g. mid-June 2025). We keep gaps as NaN rather than interpolating.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlencode

import pandas as pd
import requests

BASE_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
RATE_LIMIT_MARKER = "limit requests to one every"
MIN_SECONDS_BETWEEN_CALLS = 6.0


@dataclass
class GdeltTimeline:
    """Parsed result of a timelinevolraw query."""

    query: str
    frame: pd.DataFrame  # columns: date (datetime64), count (int), norm (int)


def build_timeline_url(
    query: str,
    start: str,
    end: str,
    mode: str = "timelinevolraw",
) -> str:
    """Build a GDELT DOC API timeline URL.

    start/end: 'YYYYMMDD' strings (day resolution is enough here).
    """
    params = {
        "query": query,
        "mode": mode,
        "STARTDATETIME": f"{start}000000",
        "ENDDATETIME": f"{end}235959",
        "format": "json",
    }
    return f"{BASE_URL}?{urlencode(params)}"


def parse_timeline_json(payload: dict, query: str = "") -> GdeltTimeline:
    """Parse the JSON body of a timelinevolraw response into a DataFrame."""
    if "timeline" not in payload or not payload["timeline"]:
        raise ValueError("GDELT response has no 'timeline' series")
    data = payload["timeline"][0]["data"]
    rows = [
        {
            "date": pd.to_datetime(item["date"][:8], format="%Y%m%d"),
            "count": int(item["value"]),
            "norm": int(item.get("norm", 0)),
        }
        for item in data
    ]
    frame = pd.DataFrame(rows).set_index("date").sort_index()
    return GdeltTimeline(query=query, frame=frame)


def fetch_timeline(
    query: str,
    start: str,
    end: str,
    session: Optional[requests.Session] = None,
    max_retries: int = 3,
) -> GdeltTimeline:
    """Fetch a daily article-count timeline from GDELT.

    Retries (with a pause) when the rate-limit message is returned.
    """
    sess = session or requests.Session()
    url = build_timeline_url(query, start, end)
    last_text = ""
    for _ in range(max_retries):
        resp = sess.get(url, timeout=30)
        last_text = resp.text
        if RATE_LIMIT_MARKER in last_text:
            time.sleep(MIN_SECONDS_BETWEEN_CALLS * 2)
            continue
        resp.raise_for_status()
        return parse_timeline_json(resp.json(), query=query)
    raise RuntimeError(f"GDELT rate limit persisted; last response: {last_text[:200]}")


def load_cached_timeline(csv_path: str) -> pd.DataFrame:
    """Load a cached timeline CSV (date,article_count,total_articles_norm).

    Used by the demo so it runs offline and reproducibly.
    """
    frame = pd.read_csv(csv_path, dtype={"date": str})
    frame["date"] = pd.to_datetime(frame["date"], format="%Y%m%d")
    frame = frame.rename(
        columns={"article_count": "count", "total_articles_norm": "norm"}
    )
    return frame.set_index("date").sort_index()
