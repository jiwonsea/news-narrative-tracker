"""Google News RSS collector.

Secondary source. Unlike GDELT it has no historical backfill (the feed only
returns recent items), so it is used for *forward* daily collection, not for
retrospective demos. Run it on a schedule and append to a local store.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import List, Optional
from urllib.parse import quote

import requests

RSS_URL = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"


@dataclass
class Headline:
    title: str
    published: Optional[datetime]
    link: str


def build_rss_url(query: str) -> str:
    return RSS_URL.format(query=quote(query))


def parse_rss(xml_text: str) -> List[Headline]:
    """Parse an RSS payload into a list of headlines."""
    root = ET.fromstring(xml_text)
    headlines: List[Headline] = []
    for item in root.iter("item"):
        title = item.findtext("title") or ""
        link = item.findtext("link") or ""
        pub_raw = item.findtext("pubDate")
        published = None
        if pub_raw:
            try:
                published = parsedate_to_datetime(pub_raw)
            except (TypeError, ValueError):
                published = None
        headlines.append(Headline(title=title, published=published, link=link))
    return headlines


def fetch_headlines(query: str, session: Optional[requests.Session] = None) -> List[Headline]:
    sess = session or requests.Session()
    resp = sess.get(build_rss_url(query), timeout=30)
    resp.raise_for_status()
    return parse_rss(resp.text)
