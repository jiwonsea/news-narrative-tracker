"""Forward collector: fetch current headlines and append daily counts.

Run this on a schedule (e.g. daily cron / GitHub Actions) to build a live
narrative frequency store under data/forward/. Neither Google News RSS nor
the Naver News API can backfill, so each series starts the day you start
collecting. Forward stores are NOT comparable with GDELT share series.

Sources write to separate stores (different universes, do not mix):
    google -> data/forward/
    naver  -> data/forward/naver/   (needs NAVER_CLIENT_ID/_SECRET env vars)

Usage:
    python scripts/collect_forward.py                    # google, all themes
    python scripts/collect_forward.py --source naver
    python scripts/collect_forward.py --theme smr_nuclear
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from narrative_tracker.forward import (  # noqa: E402
    append_counts,
    count_new_matches,
    load_seen,
    save_seen,
)
from narrative_tracker.sources import google_news, naver  # noqa: E402
from narrative_tracker.themes import Theme, load_themes  # noqa: E402

STORES = {
    "google": ROOT / "data" / "forward",
    "naver": ROOT / "data" / "forward" / "naver",
}


def _has_hangul(text: str) -> bool:
    return any("가" <= ch <= "힣" for ch in text)


def theme_query(theme: Theme, source: str) -> str:
    """Pick the search query for a theme.

    Google: first (most specific) keyword. Naver: first Korean keyword if
    the theme has one, else fall back to the first keyword.
    """
    if not theme.keywords:
        return theme.label
    if source == "naver":
        for kw in theme.keywords:
            if _has_hangul(kw):
                return kw.strip()
    return theme.keywords[0].strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--theme", help="collect a single theme key only")
    parser.add_argument(
        "--source", choices=sorted(STORES), default="google", help="headline source"
    )
    args = parser.parse_args()

    themes = load_themes(str(ROOT / "config" / "themes.yaml"))
    if args.theme:
        themes = {args.theme: themes[args.theme]}

    fetch = google_news.fetch_headlines if args.source == "google" else naver.fetch_headlines
    store = STORES[args.source]

    for key, theme in themes.items():
        query = theme_query(theme, args.source)
        headlines = fetch(query)
        seen = load_seen(store, key)
        result = count_new_matches(headlines, theme, seen)
        append_counts(store, key, result.per_day)
        save_seen(store, key, seen)
        print(
            f"[{args.source}] {key}: query={query!r} fetched={len(headlines)} "
            f"new={result.new_headlines} matched={result.matched} "
            f"days={sorted(result.per_day)}"
        )


if __name__ == "__main__":
    main()
