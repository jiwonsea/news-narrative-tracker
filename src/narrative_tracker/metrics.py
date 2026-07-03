"""Narrative intensity metrics.

Metric definitions (author's design decisions -- see README for rationale):

- share:       daily article count / total articles GDELT monitored that day.
               Normalizes away growth/shrinkage of the news universe itself.
- share_ma7:   7-day rolling mean of share (smooths day-of-week effects).
- freq_z:      rolling z-score of share_ma7 over a trailing 90-day window
               (min 30 observations). "How unusual is today's narrative
               intensity vs the last quarter?"
- chg_28d:     28-day change rate of share_ma7. "Is the narrative
               accelerating or fading?"
- momentum:    0.5 * freq_z + 0.5 * z-score of chg_28d (same 90d window).
               A single score combining level and acceleration.

Deliberately NOT included in the MVP: embeddings, sentiment, topic models.
Frequency first -- every number here can be traced back to a raw count.

NaN policy: missing days (source outages) stay NaN. Rolling stats use
min_periods so early values are NaN rather than unstable estimates.
"""

from __future__ import annotations

import pandas as pd

ZSCORE_WINDOW = 90
ZSCORE_MIN_PERIODS = 30
SMOOTH_WINDOW = 7
CHANGE_WINDOW = 28


def rolling_zscore(
    series: pd.Series,
    window: int = ZSCORE_WINDOW,
    min_periods: int = ZSCORE_MIN_PERIODS,
) -> pd.Series:
    """Trailing z-score: (x - rolling_mean) / rolling_std."""
    mean = series.rolling(window, min_periods=min_periods).mean()
    std = series.rolling(window, min_periods=min_periods).std()
    return (series - mean) / std


def compute_metrics(frame: pd.DataFrame) -> pd.DataFrame:
    """Compute narrative metrics from a daily count/norm frame.

    Input:  DataFrame indexed by date with columns count, norm.
    Output: copy with share, share_ma7, freq_z, chg_28d, momentum columns.
    """
    out = frame.copy()
    # Reindex to a full daily calendar so gaps are explicit NaN.
    full_index = pd.date_range(out.index.min(), out.index.max(), freq="D")
    out = out.reindex(full_index)
    out.index.name = "date"

    # Guard against pathological norm values (e.g. norm=494 on a GDELT
    # outage day would produce an absurd share); treat tiny norms as missing.
    valid = out["norm"] > 10_000
    out["share"] = (out["count"] / out["norm"]).where(valid)

    out["share_ma7"] = out["share"].rolling(SMOOTH_WINDOW, min_periods=4).mean()
    out["freq_z"] = rolling_zscore(out["share_ma7"])
    # explicit ratio instead of pct_change: no implicit NaN forward-fill
    out["chg_28d"] = out["share_ma7"] / out["share_ma7"].shift(CHANGE_WINDOW) - 1.0
    out["momentum"] = 0.5 * out["freq_z"] + 0.5 * rolling_zscore(out["chg_28d"])
    return out


def weekly_aggregate(frame: pd.DataFrame) -> pd.DataFrame:
    """Aggregate a daily count/norm frame to weekly (W-SUN) totals."""
    weekly = frame[["count", "norm"]].resample("W-SUN").sum(min_count=1)
    weekly["share"] = weekly["count"] / weekly["norm"]
    return weekly
