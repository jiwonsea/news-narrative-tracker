import pandas as pd
import pytest

from narrative_tracker.sources.gdelt import build_timeline_url, parse_timeline_json

SAMPLE = {
    "query_details": {"title": "(Oklo OR \"small modular reactor\")"},
    "timeline": [
        {
            "series": "Article Count",
            "data": [
                {"date": "20250101T000000Z", "value": 1, "norm": 110544},
                {"date": "20250102T000000Z", "value": 4, "norm": 166479},
            ],
        }
    ],
}


def test_parse_timeline_json_shapes_frame():
    tl = parse_timeline_json(SAMPLE, query="q")
    assert list(tl.frame.columns) == ["count", "norm"]
    assert len(tl.frame) == 2
    assert tl.frame.index[0] == pd.Timestamp("2025-01-01")
    assert tl.frame["count"].iloc[1] == 4
    assert tl.frame["norm"].iloc[0] == 110544


def test_parse_timeline_json_empty_raises():
    with pytest.raises(ValueError):
        parse_timeline_json({"timeline": []})


def test_build_timeline_url_contains_params():
    url = build_timeline_url("Oklo sourcelang:eng", "20250101", "20260630")
    assert "STARTDATETIME=20250101000000" in url
    assert "ENDDATETIME=20260630235959" in url
    assert "format=json" in url
    assert "timelinevolraw" in url
