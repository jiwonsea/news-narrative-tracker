import json
from pathlib import Path

import pytest
import requests

from narrative_tracker.forward import count_new_matches
from narrative_tracker.sources.naver import (
    NaverAPIError,
    NaverCredentialsError,
    clean_title,
    dedupe_link,
    fetch_headlines,
    parse_items,
)
from narrative_tracker.sources.naver import (
    fetch_headlines as _fetch,
)
from narrative_tracker.themes import Theme

FIXTURE = Path(__file__).parent / "fixtures" / "naver_news_sample.json"


def load_fixture_items():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["items"]


def test_clean_title_strips_tags_and_entities():
    raw = "<b>소형모듈원전</b> 수출 계약 체결&hellip; &quot;역대 최대&quot;"
    assert clean_title(raw) == '소형모듈원전 수출 계약 체결… "역대 최대"'


def test_dedupe_link_prefers_originallink():
    items = load_fixture_items()
    assert dedupe_link(items[0]) == "https://example-press.co.kr/news/1001"
    # empty originallink falls back to the naver link
    assert dedupe_link(items[3]) == "https://n.news.naver.com/mnews/article/004/0004"


def test_parse_items_from_fixture():
    headlines = parse_items(load_fixture_items())
    assert len(headlines) == 5
    # KST pubDate converts to a timezone-aware datetime
    assert headlines[0].published is not None
    assert headlines[0].published.utcoffset().total_seconds() == 9 * 3600
    # unparseable pubDate becomes None instead of raising
    assert headlines[4].published is None
    # titles are cleaned before matching
    assert "<b>" not in headlines[0].title


def test_originallink_dedupe_via_forward_pipeline():
    theme = Theme(key="smr_kr", label="SMR KR", gdelt_query="q", keywords=["소형모듈원전"])
    headlines = parse_items(load_fixture_items())
    result = count_new_matches(headlines, theme, set())
    # items 0 and 1 share an originallink -> second one is deduped
    assert result.new_headlines == 4
    assert result.matched == 1
    # 2026-07-03 08:30 KST == 2026-07-02 23:30 UTC (store uses UTC days)
    assert result.per_day == {"2026-07-02": 1}


def test_fetch_headlines_requires_credentials(monkeypatch):
    monkeypatch.delenv("NAVER_CLIENT_ID", raising=False)
    monkeypatch.delenv("NAVER_CLIENT_SECRET", raising=False)
    with pytest.raises(NaverCredentialsError):
        fetch_headlines("소형모듈원전")


def test_fetch_headlines_uses_header_credentials(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return json.loads(FIXTURE.read_text(encoding="utf-8"))

    class FakeSession:
        def get(self, url, params=None, headers=None, timeout=None):
            captured["url"] = url
            captured["params"] = params
            captured["headers"] = headers
            return FakeResponse()

    headlines = fetch_headlines(
        "소형모듈원전", client_id="cid", client_secret="sec", session=FakeSession()
    )
    assert captured["headers"]["X-Naver-Client-Id"] == "cid"
    assert captured["headers"]["X-Naver-Client-Secret"] == "sec"
    assert captured["params"]["query"] == "소형모듈원전"
    assert len(headlines) == 5


def _item(i):
    return {"originallink": f"https://ex.co/{i}", "link": "", "title": f"t{i}", "pubDate": ""}


class _Resp:
    def __init__(self, items, status=200):
        self._items = items
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"status {self.status_code}")

    def json(self):
        return {"items": self._items}


def test_retry_on_network_error_then_succeeds():
    sleeps = []
    calls = {"n": 0}

    class Sess:
        def get(self, url, params=None, headers=None, timeout=None):
            calls["n"] += 1
            if calls["n"] <= 2:
                raise requests.ConnectionError("boom")
            return _Resp([_item(1)])

    out = _fetch("q", client_id="c", client_secret="s", session=Sess(),
                 backoff=0.01, sleep=lambda s: sleeps.append(s))
    assert len(out) == 1
    assert calls["n"] == 3
    assert len(sleeps) == 2  # two failed attempts -> two backoffs


def test_retry_on_429_then_succeeds():
    calls = {"n": 0}

    class Sess:
        def get(self, url, params=None, headers=None, timeout=None):
            calls["n"] += 1
            if calls["n"] == 1:
                return _Resp([], status=429)
            return _Resp([_item(1)])

    out = _fetch("q", client_id="c", client_secret="s", session=Sess(),
                 backoff=0.0, sleep=lambda s: None)
    assert len(out) == 1
    assert calls["n"] == 2


def test_raises_after_exhausting_retries():
    class Sess:
        def get(self, url, params=None, headers=None, timeout=None):
            raise requests.ConnectionError("always down")

    with pytest.raises(NaverAPIError):
        _fetch("q", client_id="c", client_secret="s", session=Sess(),
               max_retries=2, backoff=0.0, sleep=lambda s: None)


def test_pagination_across_pages():
    """max_results>100 pages through the API; start increments; pause honored."""
    pool = [_item(i) for i in range(250)]
    seen_starts = []
    pauses = []

    class Sess:
        def get(self, url, params=None, headers=None, timeout=None):
            start = params["start"]
            want = params["display"]
            seen_starts.append(start)
            chunk = pool[start - 1: start - 1 + want]
            return _Resp(chunk)

    out = _fetch("q", client_id="c", client_secret="s", session=Sess(),
                 max_results=250, pause=0.5, sleep=lambda s: pauses.append(s))
    assert len(out) == 250
    assert seen_starts == [1, 101, 201]
    assert pauses == [0.5, 0.5]  # a pause between each of the 3 pages except last


def test_short_page_stops_paging():
    pool = [_item(i) for i in range(150)]

    class Sess:
        def get(self, url, params=None, headers=None, timeout=None):
            start = params["start"]
            want = params["display"]
            return _Resp(pool[start - 1: start - 1 + want])

    out = _fetch("q", client_id="c", client_secret="s", session=Sess(),
                 max_results=1000, sleep=lambda s: None)
    assert len(out) == 150  # stopped when a page returned fewer than requested
