"""Forward (live) collection: append daily counts from RSS-style sources.

This is what turns the retrospective tool into a monitor. Run
`scripts/collect_forward.py` on a schedule (daily cron); it fetches current
headlines per theme, dedupes against previously seen links, and appends
per-day match counts to a small CSV store.

Store layout (per theme, under data/forward/):
    <theme_key>.csv        date,count  (UTC dates, one row per day, summed)
    <theme_key>_seen.txt   one URL per line (dedup memory)

Design notes:
- Unlike GDELT, RSS feeds cannot backfill history. Counts start accumulating
  from the day you start running the collector. Mixing this store with GDELT
  series is NOT meaningful without normalization; keep them separate.
- Dedup is by exact link. Google News links are stable per article.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, Set

import pandas as pd

from .sources.google_news import Headline
from .themes import Theme, match_headline


@dataclass
class CollectResult:
    theme_key: str
    new_headlines: int
    matched: int
    per_day: Dict[str, int]


def _seen_path(store_dir: Path, theme_key: str) -> Path:
    return store_dir / f"{theme_key}_seen.txt"


def _counts_path(store_dir: Path, theme_key: str) -> Path:
    return store_dir / f"{theme_key}.csv"


def load_seen(store_dir: Path, theme_key: str) -> Set[str]:
    path = _seen_path(store_dir, theme_key)
    if not path.exists():
        return set()
    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


def headline_day(headline: Headline) -> str:
    """UTC date (YYYY-MM-DD) for a headline; falls back to today."""
    if headline.published is not None:
        return headline.published.astimezone(timezone.utc).strftime("%Y-%m-%d")
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def count_new_matches(
    headlines: Iterable[Headline],
    theme: Theme,
    seen: Set[str],
) -> CollectResult:
    """Count theme-matching headlines not seen before, grouped by UTC day.

    Pure function (no I/O) so it is unit-testable.
    """
    per_day: Dict[str, int] = {}
    new_count = 0
    matched = 0
    for h in headlines:
        if not h.link or h.link in seen:
            continue
        seen.add(h.link)
        new_count += 1
        if match_headline(h.title, theme):
            matched += 1
            day = headline_day(h)
            per_day[day] = per_day.get(day, 0) + 1
    return CollectResult(
        theme_key=theme.key, new_headlines=new_count, matched=matched, per_day=per_day
    )


def append_counts(store_dir: Path, theme_key: str, per_day: Dict[str, int]) -> pd.DataFrame:
    """Merge per-day counts into the theme's CSV store (summing same days)."""
    store_dir.mkdir(parents=True, exist_ok=True)
    path = _counts_path(store_dir, theme_key)
    if path.exists():
        frame = pd.read_csv(path, dtype={"date": str})
    else:
        frame = pd.DataFrame(columns=["date", "count"])
    merged = dict(zip(frame["date"], frame["count"].astype(int)))
    for day, n in per_day.items():
        merged[day] = int(merged.get(day, 0)) + int(n)
    out = (
        pd.DataFrame({"date": list(merged.keys()), "count": list(merged.values())})
        .sort_values("date")
        .reset_index(drop=True)
    )
    out.to_csv(path, index=False)
    return out


def save_seen(store_dir: Path, theme_key: str, seen: Set[str]) -> None:
    store_dir.mkdir(parents=True, exist_ok=True)
    _seen_path(store_dir, theme_key).write_text(
        "\n".join(sorted(seen)) + "\n", encoding="utf-8"
    )
