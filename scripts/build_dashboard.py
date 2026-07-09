"""Build the multi-theme signal-light dashboard (reports/dashboard.html).

For every theme in config/themes.yaml, load its cached GDELT snapshot (if
one exists under data/), compute narrative metrics, and render the latest
momentum as an ELEVATED/NEUTRAL/FADING card. Themes without a snapshot get
a NO DATA card instead of being silently dropped.

Offline by design: only reads cached CSVs, so it runs in CI.

Usage:
    python scripts/build_dashboard.py
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from narrative_tracker.pipeline import run_gdelt_pipeline  # noqa: E402
from narrative_tracker.report import (  # noqa: E402
    NO_DATA_COLOR,
    ThemeCard,
    build_dashboard,
    momentum_status,
)
from narrative_tracker.themes import Theme, load_themes  # noqa: E402

DATA = ROOT / "data"
OUT_HTML = ROOT / "reports" / "dashboard.html"

# Cached GDELT snapshots per theme key (filenames predate the dashboard).
GDELT_CACHES = {
    "smr_nuclear": "gdelt_smr_oklo_20250101_20260630.csv",
    "ai_datacenter_power": "gdelt_datacenter_nuclear_20250101_20260630.csv",
    # Pending retrieval (see scripts/fetch_gdelt_snapshot.py); NO DATA until
    # the CSV exists under data/.
    "hbm_memory": "gdelt_hbm_20250101_20260630.csv",
    "defense_exports": "gdelt_kdefense_20250101_20260630.csv",
}


def build_card(key: str, theme: Theme) -> ThemeCard:
    cache_name = GDELT_CACHES.get(key)
    cache = DATA / cache_name if cache_name else None
    if cache is None or not cache.exists():
        return ThemeCard(
            key=key, label=theme.label, status="NO DATA", color=NO_DATA_COLOR,
            momentum=None, freq_z=None, chg_28d=None, as_of="–",
            source_note="no cached GDELT snapshot yet",
        )
    scored = run_gdelt_pipeline(theme, start="", end="", cache_csv=str(cache))
    valid = scored.dropna(subset=["momentum"])
    if valid.empty:
        return ThemeCard(
            key=key, label=theme.label, status="NO DATA", color=NO_DATA_COLOR,
            momentum=None, freq_z=None, chg_28d=None, as_of="–",
            source_note="not enough history for momentum",
        )
    last = valid.iloc[-1]
    as_of = valid.index[-1].strftime("%Y-%m-%d")
    status, color = momentum_status(float(last["momentum"]))
    return ThemeCard(
        key=key, label=theme.label, status=status, color=color,
        momentum=float(last["momentum"]), freq_z=float(last["freq_z"]),
        chg_28d=float(last["chg_28d"]), as_of=as_of,
        source_note=f"GDELT snapshot {cache_name}",
    )


def main() -> None:
    themes = load_themes(str(ROOT / "config" / "themes.yaml"))
    cards = [build_card(key, theme) for key, theme in themes.items()]
    html = build_dashboard(
        title="Narrative momentum dashboard",
        subtitle=(
            "Theme-level news narrative intensity — retrospective, "
            "from cached GDELT snapshots"
        ),
        cards=cards,
        generated_on=str(date.today()),
    )
    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(html, encoding="utf-8")
    for c in cards:
        print(f"{c.key}: {c.status} momentum={c.momentum} as_of={c.as_of}")
    print(f"wrote {OUT_HTML}")

