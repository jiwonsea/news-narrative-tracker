from narrative_tracker.themes import Theme, count_matches, match_headline


def make_theme():
    return Theme(
        key="smr_nuclear",
        label="SMR",
        gdelt_query="q",
        keywords=["oklo", "small modular reactor", " smr", "소형모듈원전"],
    )


def test_match_is_case_insensitive():
    t = make_theme()
    assert match_headline("Oklo shares jump after DOE announcement", t)
    assert match_headline("OKLO INC reports quarterly results", t)


def test_word_boundary_guard_for_short_keywords():
    t = make_theme()
    assert match_headline("SMR deployment accelerates", t)
    # ' smr' must not match inside another word
    assert not match_headline("Plasmr protein study published", t)


def test_korean_keyword_matches():
    t = make_theme()
    assert match_headline("두산에너빌리티, 소형모듈원전 수주 기대", t)


def test_count_matches():
    t = make_theme()
    titles = ["Oklo up 10%", "Weather today", "New SMR design approved"]
    assert count_matches(titles, t) == 2
