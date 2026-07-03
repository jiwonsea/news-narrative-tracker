import numpy as np
import pandas as pd
import pytest

from narrative_tracker.metrics import compute_metrics, rolling_zscore, weekly_aggregate


def make_frame(n=120, count=5, norm=100_000):
    idx = pd.date_range("2025-01-01", periods=n, freq="D")
    return pd.DataFrame({"count": count, "norm": norm}, index=idx)


def test_rolling_zscore_flat_series_is_nan_or_zero():
    s = pd.Series(np.ones(100))
    z = rolling_zscore(s)
    # std of a flat series is 0 -> z is NaN (0/0), never a fake signal
    assert z.dropna().empty or (z.dropna() == 0).all()


def test_rolling_zscore_detects_spike():
    values = np.ones(100)
    values[-1] = 10.0
    z = rolling_zscore(pd.Series(values))
    assert z.iloc[-1] > 3


def test_compute_metrics_share_normalization():
    frame = make_frame(count=10, norm=100_000)
    out = compute_metrics(frame)
    assert out["share"].dropna().iloc[0] == pytest.approx(10 / 100_000)


def test_compute_metrics_tiny_norm_treated_as_missing():
    frame = make_frame(n=60)
    # simulate a GDELT outage day (norm collapses, like 2025-12-06 norm=494)
    frame.iloc[30, frame.columns.get_loc("norm")] = 494
    out = compute_metrics(frame)
    assert pd.isna(out["share"].iloc[30])


def test_compute_metrics_reindexes_gaps_as_nan():
    frame = make_frame(n=30)
    frame = frame.drop(frame.index[10:15])  # 5-day hole
    out = compute_metrics(frame)
    assert len(out) == 30  # full calendar restored
    assert out["count"].isna().sum() == 5


def test_weekly_aggregate_sums_counts():
    frame = make_frame(n=14, count=3)
    weekly = weekly_aggregate(frame)
    assert weekly["count"].sum() == 42
