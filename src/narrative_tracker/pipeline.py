"""Collection -> frequency -> score pipeline."""

from __future__ import annotations

from typing import Optional

import pandas as pd

from .metrics import compute_metrics
from .sources import gdelt
from .themes import Theme


def run_gdelt_pipeline(
    theme: Theme,
    start: str,
    end: str,
    cache_csv: Optional[str] = None,
) -> pd.DataFrame:
    """Produce a scored daily narrative timeseries for one theme.

    If cache_csv is given, load from it (offline / reproducible mode);
    otherwise hit the GDELT API.
    """
    if cache_csv:
        raw = gdelt.load_cached_timeline(cache_csv)
    else:
        raw = gdelt.fetch_timeline(theme.gdelt_query, start, end).frame
    return compute_metrics(raw)


def load_price_csv(csv_path: str) -> pd.Series:
    """Load a date,close CSV (dates as YYYYMMDD) into a Series."""
    frame = pd.read_csv(csv_path, dtype={"date": str})
    frame["date"] = pd.to_datetime(frame["date"], format="%Y%m%d")
    return frame.set_index("date").sort_index()["close"]
