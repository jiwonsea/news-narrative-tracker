from narrative_tracker.report import (
    NO_DATA_COLOR,
    ThemeCard,
    build_dashboard,
    momentum_status,
)


def make_card(**overrides):
    base = dict(
        key="smr_nuclear",
        label="SMR / advanced nuclear",
        status="ELEVATED",
        color="#e05d44",
        momentum=1.23,
        freq_z=1.5,
        chg_28d=0.42,
        as_of="2026-06-30",
        source_note="GDELT snapshot",
    )
    base.update(overrides)
    return ThemeCard(**base)


def test_build_dashboard_renders_all_cards():
    cards = [
        make_card(),
        make_card(key="hbm_memory", label="HBM / AI memory", status="NO DATA",
                  color=NO_DATA_COLOR, momentum=None, freq_z=None, chg_28d=None,
                  as_of="–", source_note="no cached GDELT snapshot yet"),
    ]
    html = build_dashboard("Dash", "sub", cards, generated_on="2026-07-03")
    assert "SMR / advanced nuclear" in html
    assert "HBM / AI memory" in html
    assert "ELEVATED" in html and "NO DATA" in html
    # missing metrics render as a dash, not "None"
    assert "None" not in html


def test_build_dashboard_keeps_bucket_disclaimer():
    html = build_dashboard("Dash", "sub", [make_card()], generated_on="2026-07-03")
    assert "presentation buckets, not trading signals" in html
    assert "not a prediction" in html


def test_momentum_status_buckets():
    assert momentum_status(1.0)[0] == "ELEVATED"
    assert momentum_status(0.0)[0] == "NEUTRAL"
    assert momentum_status(-0.1)[0] == "FADING"
