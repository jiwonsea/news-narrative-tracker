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


def make_hbm_theme():
    return Theme(
        key="hbm_memory",
        label="HBM",
        gdelt_query="q",
        keywords=[" hbm", "hbm3", "고대역폭메모리"],
    )


def test_punctuation_adjacent_matches():
    """The left-boundary matcher fixes the old leading-space blind spot."""
    t = make_theme()
    assert match_headline("(SMR) rollout approved", t)
    assert match_headline("New reactor: SMR, at last", t)
    assert match_headline("grid-SMR pilot launches", t)
    assert match_headline("Deploy an SMR.", t)


def test_does_not_match_acronym_inside_word():
    t = make_theme()
    assert not match_headline("ASMR audio goes viral", t)
    assert not match_headline("Plasmr protein study published", t)


def test_open_right_side_matches_prefix_forms():
    """Short acronym keywords act as prefixes: plurals/suffixes still count."""
    t = make_theme()
    assert match_headline("Two new SMRs cleared for construction", t)
    hbm = make_hbm_theme()
    assert match_headline("SK hynix ships HBM3E samples", hbm)


def test_acronym_glued_to_hangul_still_matches():
    """Left boundary uses [a-z0-9], so Hangul adjacency does not block."""
    hbm = make_hbm_theme()
    assert match_headline("삼성HBM 전략 공개", hbm)


def test_cjk_keyword_is_substring_matched():
    hbm = make_hbm_theme()
    assert match_headline("SK하이닉스 고대역폭메모리 신제품", hbm)
