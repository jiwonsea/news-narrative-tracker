"""Naver News API collector -- DESIGN ONLY (not implemented in MVP).

Planned for the Korean-market extension (v2). Kept as a documented stub so
the source interface stays visible in the codebase.

Design notes:
- Endpoint: https://openapi.naver.com/v1/search/news.json
  (requires X-Naver-Client-Id / X-Naver-Client-Secret headers; free tier
  allows 25,000 calls/day).
- Limitation vs GDELT: the search API returns *current* results ordered by
  date/relevance -- there is no historical backfill parameter. Like Google
  News RSS, it only supports forward collection.
- Matching: reuse `themes.match_headline` with the Korean keyword entries
  in config/themes.yaml (e.g. 소형모듈원전).
- Dedup: Naver returns both `originallink` and `link`; dedup on
  originallink first.
"""

from __future__ import annotations


def fetch_headlines(*args, **kwargs):
    raise NotImplementedError(
        "Naver News collection is a planned v2 feature (forward collection "
        "only; see module docstring for the design)."
    )
