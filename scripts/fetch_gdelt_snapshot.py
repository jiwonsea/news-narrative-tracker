"""Fetch a theme's GDELT timeline and write it to the on-disk cache.

Fills the dashboard's NO DATA gap for themes that don't yet have a cached
GDELT snapshot (currently hbm_memory and defense_exports). GDELT is the
retrospective source; run this from an environment with network access to
api.gdeltproject.org, then commit the resulting CSV under data/.

Usage:
    python scripts/fetch_gdelt_snapshot.py hbm_memory
    python scripts/fetch_gdelt_snapshot.py defense_exports --start 20250101 --end 20260630
    python scripts/fetch_gdelt_snapshot.py smr_nuclear --out data/custom.csv

The default window (2025-01-01 ~ 2026-06-30) matches the existing demo
snapshots so the dashboard's series are comparable. Provenance (query +
retrieval date) should be recorded in data/README.md after fetching.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from narrative_tracker.sources import gdelt  # noqa: E402
from narrative_tracker.themes import load_themes  # noqa: E402

DEFAULT_START = "20250101"
DEFAULT_END = "20260630"

# Canonical cache filename per theme key; mirrors build_dashboard.GDELT_CACHES.
DEFAULT_OUT = {
    "smr_nuclear": "gdelt_smr_oklo_20250101_20260630.csv",
    "ai_datacenter_power": "gdelt_datacenter_nuclear_20250101_20260630.csv",
    "hbm_memory": "gdelt_hbm_20250101_20260630.csv",
    "defense_exports": "gdelt_kdefense_20250101_20260630.csv",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("theme", help="theme key from config/themes.yaml")
    parser.add_argument("--start", default=DEFAULT_START, help="YYYYMMDD")
    parser.add_argument("--end", default=DEFAULT_END, help="YYYYMMDD")
    parser.add_argument("--out", default=None, help="output CSV path")
    args = parser.parse_args()

    themes = load_themes(str(ROOT / "config" / "themes.yaml"))
    if args.theme not in themes:
        parser.error(f"unknown theme '{args.theme}'. known: {', '.join(themes)}")
    theme = themes[args.theme]

    out_name = args.out or DEFAULT_OUT.get(args.theme, f"gdelt_{args.theme}.csv")
    out_path = out_name if args.out else str(ROOT / "data" / out_name)

    print(f"[gdelt] {args.theme}: query={theme.gdelt_query!r} {args.start}..{args.end}")
    timeline = gdelt.fetch_timeline(theme.gdelt_query, args.start, args.end)
    gdelt.save_timeline_csv(timeline.frame, out_path)
    print(f"[gdelt] wrote {len(timeline.frame)} rows -> {out_path}")


if __name__ == "__main__":
    main()
