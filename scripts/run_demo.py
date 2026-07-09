"""Retrospective demo: SMR/Oklo narrative frequency vs OKLO share price.

Reconstructs (after the fact) how often the "SMR / advanced nuclear" theme
appeared in news coverage during 2025-01 ~ 2026-06 and overlays the OKLO
share price, to study the timing relationship between narrative intensity
and price. This is a retrospective reconstruction, NOT a prediction test.

Usage:
    python scripts/run_demo.py            # offline, uses data/ snapshots
    python scripts/run_demo.py --fetch    # refresh from the GDELT API
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from narrative_tracker.pipeline import load_price_csv, run_gdelt_pipeline  # noqa: E402
from narrative_tracker.report import ReportStat, build_report, momentum_status  # noqa: E402
from narrative_tracker.themes import load_themes  # noqa: E402

DATA = ROOT / "data"
REPORTS = ROOT / "reports"
GDELT_CACHE = DATA / "gdelt_smr_oklo_20250101_20260630.csv"
GDELT_CACHE_DC = DATA / "gdelt_datacenter_nuclear_20250101_20260630.csv"
PRICE_CACHE = DATA / "oklo_close_20250101_20260630.csv"
CHART_PNG = REPORTS / "oklo_smr_narrative_vs_price.png"
REPORT_HTML = REPORTS / "demo_report.html"

# Verified against Yahoo Finance chart API on 2026-07-02:
# OKLO all-time intraday high 193.84 occurred on 2025-10-15
# (2025-10-13 high was 175.90 / close 171.01; peak CLOSE was 174.14 on 2025-10-14).
INTRADAY_HIGH = 193.84
INTRADAY_HIGH_DATE = "2025-10-15"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fetch", action="store_true", help="hit the GDELT API instead of the cache"
    )
    args = parser.parse_args()

    themes = load_themes(str(ROOT / "config" / "themes.yaml"))
    theme = themes["smr_nuclear"]
    theme_dc = themes["ai_datacenter_power"]

    scored = run_gdelt_pipeline(
        theme,
        start="20250101",
        end="20260630",
        cache_csv=None if args.fetch else str(GDELT_CACHE),
    )
    scored_dc = run_gdelt_pipeline(
        theme_dc,
        start="20250101",
        end="20260630",
        cache_csv=None if args.fetch else str(GDELT_CACHE_DC),
    )
    price = load_price_csv(str(PRICE_CACHE))

    # --- computed facts (all derived from the data, nothing hardcoded) ---
    narrative_peak_day = scored["share_ma7"].idxmax()
    narrative_z_peak_day = scored["freq_z"].idxmax()
    price_peak_day = price.idxmax()
    latest = scored.dropna(subset=["momentum"]).iloc[-1]
    lead_days = (price_peak_day - narrative_peak_day).days

    # --- chart ---
    REPORTS.mkdir(exist_ok=True)
    fig, ax1 = plt.subplots(figsize=(12, 5.5))

    share_scaled = scored["share_ma7"] * 100_000  # articles per 100k monitored
    ax1.plot(scored.index, share_scaled, color="#1f6fb2", lw=1.6,
             label=f"Narrative frequency: {theme.label}\n(7d MA, articles per 100k monitored)")
    ax1.fill_between(scored.index, 0, share_scaled, color="#1f6fb2", alpha=0.12)
    share_dc_scaled = scored_dc["share_ma7"] * 100_000
    ax1.plot(scored_dc.index, share_dc_scaled, color="#3a9d6e", lw=1.2, alpha=0.9,
             label=f"Narrative frequency: {theme_dc.label}\n(7d MA, articles per 100k monitored)")
    ax1.set_ylabel("Matching articles per 100k monitored (7d MA)", color="#1f6fb2")
    ax1.tick_params(axis="y", labelcolor="#1f6fb2")
    ax1.set_ylim(bottom=0)

    ax2 = ax1.twinx()
    ax2.plot(price.index, price, color="#d1495b", lw=1.4, label="OKLO close (USD)")
    ax2.set_ylabel("OKLO close (USD)", color="#d1495b")
    ax2.tick_params(axis="y", labelcolor="#d1495b")
    ax2.set_ylim(bottom=0)

    ax1.axvline(narrative_peak_day, color="#1f6fb2", ls="--", lw=1, alpha=0.8)
    ax1.annotate(f"narrative peak\n{narrative_peak_day.date()}",
                 xy=(narrative_peak_day, ax1.get_ylim()[1] * 0.60),
                 fontsize=8, color="#1f6fb2", ha="right", va="top")
    ax1.axvline(price_peak_day, color="#d1495b", ls="--", lw=1, alpha=0.8)
    ax1.annotate(f"price close peak\n{price_peak_day.date()} (${price.max():.2f})\n"
                 f"intraday high ${INTRADAY_HIGH} on {INTRADAY_HIGH_DATE}",
                 xy=(price_peak_day, ax1.get_ylim()[1] * 0.78),
                 fontsize=8, color="#d1495b", ha="left", va="top")

    # mark the GDELT data gap honestly
    gap = scored[scored["count"].isna()]
    if not gap.empty:
        ax1.axvspan(gap.index.min(), gap.index.max(), color="#999", alpha=0.15)
        ax1.annotate("GDELT\ndata gap", xy=(gap.index.min(), ax1.get_ylim()[1] * 0.5),
                     fontsize=7, color="#666")

    ax1.set_title("Retrospective: SMR/advanced-nuclear narrative frequency vs OKLO price "
                  "(2025-01 ~ 2026-06)", fontsize=11)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=7)
    fig.tight_layout()
    fig.savefig(CHART_PNG, dpi=150)
    plt.close(fig)

    # --- report ---
    status, color = momentum_status(float(latest["momentum"]))
    stats = [
        ReportStat("Narrative peak (7d MA share)", str(narrative_peak_day.date()),
                   "max of 7-day MA of article share"),
        ReportStat("Narrative z-score peak", str(narrative_z_peak_day.date()),
                   "max of 90d rolling z-score"),
        ReportStat("OKLO close peak", f"{price_peak_day.date()} (${price.max():.2f})",
                   f"intraday high ${INTRADAY_HIGH} on {INTRADAY_HIGH_DATE} (Yahoo)"),
        ReportStat("Peak gap", f"{lead_days:+d} days",
                   "price close peak minus narrative peak (+ = narrative first)"),
        ReportStat("Latest momentum score", f"{latest['momentum']:.2f}",
                   f"as of {scored.dropna(subset=['momentum']).index[-1].date()}"),
    ]
    notes = [
        f"The 7d-MA narrative frequency peaked on {narrative_peak_day.date()}; "
        f"the OKLO closing-price peak was {price_peak_day.date()} "
        f"(${price.max():.2f} close; intraday high ${INTRADAY_HIGH} on {INTRADAY_HIGH_DATE}). "
        f"Gap between the two peaks: {abs(lead_days)} days.",
        f"The companion theme '{theme_dc.label}' peaked (7d MA) on "
        f"{scored_dc['share_ma7'].idxmax().date()}, showing that related "
        "narratives can peak at very different times.",
        "Frequency spikes cluster around company/sector events (e.g. 2025-09 and "
        "2025-10 spikes coincide with the run-up phase; the largest single-day "
        "count in the SMR series, 115 articles on 2026-01-09, occurred well after "
        "the price peak).",
        "This overlay describes the timing relationship in ONE episode. One case "
        "proves nothing about repeatability; it motivates building a live, "
        "forward-collected version.",
    ]
    limitations = [
        "Retrospective reconstruction: queries were written in 2026 with full "
        "knowledge of the episode. No out-of-sample claim is made.",
        "GDELT counts English-language articles matching the query anywhere in "
        "the text; counts include syndicated duplicates.",
        "GDELT has a data gap 2025-06-15 ~ 2025-07-01 (shaded in the chart) and "
        "two days with collapsed totals, treated as missing.",
        "Prices are unadjusted daily closes (Yahoo Finance); the intraday high "
        "is annotated separately because close data cannot show it.",
        "Correlation of one narrative with one stock in one period is anecdotal "
        "evidence by construction.",
    ]

    html = build_report(
        title="SMR / Advanced-Nuclear Narrative vs OKLO — Retrospective Demo",
        subtitle=f"Theme: {theme.label} · GDELT query: {theme.gdelt_query} · "
                 "2025-01-01 ~ 2026-06-30",
        status=status,
        status_color=color,
        chart_png_path=str(CHART_PNG),
        stats=stats,
        narrative_notes=notes,
        limitations=limitations,
        generated_on=str(date.today()),
    )
    REPORT_HTML.write_text(html, encoding="utf-8")

    print(f"chart  -> {CHART_PNG}")
    print(f"report -> {REPORT_HTML}")
    print(f"narrative peak {narrative_peak_day.date()} | z peak {narrative_z_peak_day.date()} "
          f"| price close peak {price_peak_day.date()} | gap {lead_days:+d}d "
          f"| latest momentum {latest['momentum']:.2f} ({status})")


if __name__ == "__main__":
    main()
