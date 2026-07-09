"""Theme dictionary loading and headline matching."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Dict, List, Optional, Pattern, Union

import yaml

# Any CJK ideograph or Hangul syllable/jamo. Keywords containing these are
# matched as plain substrings: CJK scripts are written without inter-word
# spaces, so ASCII-style word boundaries do not apply.
_CJK_RE = re.compile(
    r"[　-〿㐀-䶿一-鿿가-힣ᄀ-ᇿ豈-﫿]"
)


@dataclass
class Theme:
    key: str
    label: str
    gdelt_query: str
    keywords: List[str] = field(default_factory=list)
    # Optional metadata backing the theme-selection inclusion rule
    # (see config/themes.yaml header). ``proxy`` names the liquid instrument
    # or basket the theme is studied against; ``rationale`` is a one-line note
    # on why the theme is in scope. Neither affects matching or scoring.
    proxy: str = ""
    rationale: str = ""


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
            proxy=spec.get("proxy", ""),
            rationale=spec.get("rationale", ""),
        )
    return themes


@lru_cache(maxsize=1024)
def _matcher(keyword: str) -> Optional[Union[str, Pattern]]:
    """Compile a keyword into a matcher (cached).

    - CJK keyword  -> the stripped string, used as a plain substring test.
    - ASCII/Latin  -> a regex with a LEFT word boundary against ASCII
      alphanumerics only, and an OPEN right side.

    The left boundary fixes the punctuation blind spot of the old
    leading-space hack: '(SMR)', '-SMR', 'SMR,' now match, while 'asmr' and
    'plasmr' still do not. The open right side preserves the author's intent
    that short acronym keywords (' smr', ' hbm') act as prefixes so that
    'SMRs', 'HBM3', 'HBM3E' are counted. Using [a-z0-9] rather than \\w for
    the boundary means a keyword glued to Hangul (e.g. '삼성HBM') still
    matches, which \\w would wrongly reject.
    """
    kw = keyword.strip().lower()
    if not kw:
        return None
    if _CJK_RE.search(kw):
        return kw
    return re.compile(r"(?<![a-z0-9])" + re.escape(kw))


def match_headline(title: str, theme: Theme) -> bool:
    """Case-insensitive keyword matching against a theme dictionary.

    Deliberately simple and auditable: no model dependency. See ``_matcher``
    for the boundary rules and their rationale.
    """
    hay = (title or "").lower()
    for kw in theme.keywords:
        m = _matcher(kw)
        if m is None:
            continue
        if isinstance(m, str):
            if m in hay:
                return True
        elif m.search(hay):
            return True
    return False


def count_matches(titles: List[str], theme: Theme) -> int:
    return sum(1 for t in titles if match_headline(t, theme))
