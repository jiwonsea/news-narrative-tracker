"""Theme dictionary loading and headline matching."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

import yaml


@dataclass
class Theme:
    key: str
    label: str
    gdelt_query: str
    keywords: List[str] = field(default_factory=list)


def load_themes(path: str) -> Dict[str, Theme]:
    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    themes: Dict[str, Theme] = {}
    for key, spec in raw["themes"].items():
        themes[key] = Theme(
            key=key,
            label=spec["label"],
            gdelt_query=spec["gdelt_query"],
            keywords=[k.lower() for k in spec.get("keywords", [])],
        )
    return themes


def match_headline(title: str, theme: Theme) -> bool:
    """Case-insensitive substring matching against the theme dictionary.

    Deliberately simple: auditable, no model dependency. A leading space in
    a keyword (e.g. " smr") is a cheap word-boundary guard.
    """
    haystack = f" {title.lower()} "
    return any(kw in haystack for kw in theme.keywords)


def count_matches(titles: List[str], theme: Theme) -> int:
    return sum(1 for t in titles if match_headline(t, theme))
