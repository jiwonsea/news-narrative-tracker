from datetime import datetime, timezone

import pandas as pd

from narrative_tracker.forward import append_counts, count_new_matches
from narrative_tracker.sources.google_news import Headline
from narrative_tracker.themes import Theme


def make_theme():
    return Theme(key="smr", label="SMR", gdelt_query="q", keywords=["oklo", " smr"])


def h(title, link, day=None):
    published = datetime(2026, 7, day, 12, 0, tzinfo=timezone.utc) if day else None
    return Headline(title=title, published=published, link=link)


def test_count_new_matches_dedupes_by_link():
    theme = make_theme()
    seen = {"http://a"}
    headlines = [h("Oklo rises", "http://a", 1), h("Oklo falls", "http://b", 1)]
    result = count_new_matches(headlines, theme, seen)
    assert result.new_headlines == 1
    assert result.matched == 1
    assert result.per_day == {"2026-07-01": 1}
    assert "http://b" in seen  # seen set is updated in place


def test_count_new_matches_only_counts_matching_titles():
    theme = make_theme()
    result = count_new_matches(
        [h("Weather update", "http://c", 2), h("New SMR design", "http://d", 2)],
        theme,
        set(),
    )
    assert result.new_headlines == 2
    assert result.matched == 1


def test_append_counts_sums_same_day(tmp_path):
    append_counts(tmp_path, "smr", {"2026-07-01": 2})
    out = append_counts(tmp_path, "smr", {"2026-07-01": 3, "2026-07-02": 1})
    frame = pd.read_csv(tmp_path / "smr.csv", dtype={"date": str})
    assert frame.set_index("date")["count"].to_dict() == {
        "2026-07-01": 5,
        "2026-07-02": 1,
    }
    assert list(out["date"]) == ["2026-07-01", "2026-07-02"]
