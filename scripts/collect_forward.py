"""Forward collector: fetch current headlines and append daily counts.

Run this on a schedule (e.g. daily cron) to build a live narrative
frequency store under data/forward/. RSS cannot backfill, so the series
starts the day you start collecting.

Usage:
    python scripts/collect_forward.py               # all themes
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
from narrative_tracker.sources.google_news import fetch_headlines  # noqa: E402
from narrative_tracker.themes import load_themes  # noqa: E402

STORE = ROOT / "data" / "forward"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--theme", help="collect a single theme key only")
    args = parser.parse_args()

    themes = load_themes(str(ROOT / "config" / "themes.yaml"))
    if args.theme:
        themes = {args.theme: themes[args.theme]}

    for key, theme in themes.items():
        # RSS query: reuse the first (most specific) keyword per theme
        query = theme.keywords[0].strip() if theme.keywords else theme.label
        headlines = fetch_headlines(query)
        seen = load_seen(STORE, key)
        result = count_new_matches(headlines, theme, seen)
        append_counts(STORE, key, result.per_day)
        save_seen(STORE, key, seen)
        print(
            f"{key}: fetched={len(headlines)} new={result.new_headlines} "
            f"matched={result.matched} days={sorted(result.per_day)}"
        )


if __name__ == "__main__":
    main()
