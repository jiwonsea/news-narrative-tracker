"""HTML report generation (signal-light style, single self-contained file)."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ReportStat:
    label: str
    value: str
    note: str = ""


def momentum_status(momentum: float) -> tuple:
    """Map a momentum score to a (status, color) pair.

    Thresholds are arbitrary presentation buckets, not trading signals:
    >= 1.0 elevated / 0 ~ 1 neutral / < 0 fading.
    """
    if momentum >= 1.0:
        return ("ELEVATED", "#e05d44")
    if momentum >= 0.0:
        return ("NEUTRAL", "#d9a413")
    return ("FADING", "#4a9e5c")


def build_report(
    title: str,
    subtitle: str,
    status: str,
    status_color: str,
    chart_png_path: Optional[str],
    stats: List[ReportStat],
    narrative_notes: List[str],
    limitations: List[str],
    generated_on: str,
) -> str:
    """Assemble a self-contained HTML report (chart embedded as base64)."""
    chart_html = ""
    if chart_png_path:
        with open(chart_png_path, "rb") as fh:
            b64 = base64.b64encode(fh.read()).decode("ascii")
        chart_html = (
            f'<img src="data:image/png;base64,{b64}" '
            'style="width:100%;border:1px solid #ddd;border-radius:8px;"/>'
        )

    stat_cells = "".join(
        f'<div class="stat"><div class="stat-label">{s.label}</div>'
        f'<div class="stat-value">{s.value}</div>'
        f'<div class="stat-note">{s.note}</div></div>'
        for s in stats
    )
    notes_html = "".join(f"<li>{n}</li>" for n in narrative_notes)
    limits_html = "".join(f"<li>{n}</li>" for n in limitations)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>{title}</title>
<style>
  body {{ font-family: 'Segoe UI', -apple-system, sans-serif; max-width: 960px;
         margin: 2rem auto; padding: 0 1rem; color: #222; }}
  header {{ border-bottom: 3px solid #222; padding-bottom: .8rem; margin-bottom: 1.2rem; }}
  h1 {{ margin: 0; font-size: 1.5rem; }}
  .subtitle {{ color: #666; margin-top: .3rem; }}
  .badge {{ display: inline-block; padding: .35rem .9rem; border-radius: 999px;
           color: #fff; font-weight: 700; letter-spacing: .05em;
           background: {status_color}; margin: .6rem 0; }}
  .stats {{ display: flex; gap: 1rem; flex-wrap: wrap; margin: 1.2rem 0; }}
  .stat {{ flex: 1 1 180px; background: #f6f6f6; border-radius: 8px; padding: .8rem 1rem; }}
  .stat-label {{ font-size: .78rem; color: #777; text-transform: uppercase; }}
  .stat-value {{ font-size: 1.35rem; font-weight: 700; margin: .15rem 0; }}
  .stat-note {{ font-size: .75rem; color: #999; }}
  section {{ margin: 1.4rem 0; }}
  h2 {{ font-size: 1.05rem; border-left: 4px solid #222; padding-left: .5rem; }}
  li {{ margin: .35rem 0; line-height: 1.5; }}
  .disclaimer {{ background: #fff6e5; border: 1px solid #eed9a0; border-radius: 8px;
                padding: .9rem 1.1rem; font-size: .88rem; line-height: 1.55; }}
  footer {{ color: #999; font-size: .8rem; margin-top: 2rem;
           border-top: 1px solid #eee; padding-top: .8rem; }}
</style>
</head>
<body>
<header>
  <h1>{title}</h1>
  <div class="subtitle">{subtitle}</div>
  <div class="badge">NARRATIVE: {status}</div>
</header>

<div class="disclaimer"><b>Retrospective demo — not a prediction.</b>
This report reconstructs, after the fact, how often a theme appeared in news
coverage. It does not claim the tool predicted, or could have predicted, any
price move. Narrative frequency and prices are shown together only to study
their timing relationship.</div>

<section>{chart_html}</section>

<div class="stats">{stat_cells}</div>

<section>
  <h2>Observations (descriptive, not causal)</h2>
  <ul>{notes_html}</ul>
</section>

<section>
  <h2>Limitations</h2>
  <ul>{limits_html}</ul>
</section>

<footer>news-narrative-tracker v0.1 · generated {generated_on} ·
data: GDELT DOC 2.0 API (article counts), Yahoo Finance (OKLO daily close).
Not investment advice.</footer>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# v0.3: multi-theme signal-light dashboard
# ---------------------------------------------------------------------------

NO_DATA_COLOR = "#9aa0a6"


@dataclass
class ThemeCard:
    """One theme's latest state for the dashboard grid."""

    key: str
    label: str
    status: str          # ELEVATED / NEUTRAL / FADING / NO DATA
    color: str
    momentum: Optional[float]
    freq_z: Optional[float]
    chg_28d: Optional[float]
    as_of: str           # date of the latest valid momentum value
    source_note: str = ""


def _fmt(value: Optional[float], pct: bool = False) -> str:
    if value is None:
        return "–"
    return f"{value:+.0%}" if pct else f"{value:+.2f}"


def build_dashboard(
    title: str,
    subtitle: str,
    cards: List[ThemeCard],
    generated_on: str,
) -> str:
    """Assemble a self-contained one-page dashboard (no external assets).

    Reuses the signal-light tone of the single-theme report: one card per
    theme with an ELEVATED/NEUTRAL/FADING badge. The thresholds are
    presentation buckets, not trading signals (see momentum_status).
    """
    card_html = ""
    for c in cards:
        card_html += f"""
  <div class="card">
    <div class="card-head">
      <div class="card-title">{c.label}</div>
      <div class="badge" style="background:{c.color}">{c.status}</div>
    </div>
    <div class="metrics">
      <div class="metric"><div class="m-label">momentum</div>
        <div class="m-value">{_fmt(c.momentum)}</div></div>
      <div class="metric"><div class="m-label">freq z-score (90d)</div>
        <div class="m-value">{_fmt(c.freq_z)}</div></div>
      <div class="metric"><div class="m-label">28d change</div>
        <div class="m-value">{_fmt(c.chg_28d, pct=True)}</div></div>
    </div>
    <div class="card-foot">as of {c.as_of}{(" · " + c.source_note) if c.source_note else ""}</div>
  </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>{title}</title>
<style>
  body {{ font-family: 'Segoe UI', -apple-system, sans-serif; max-width: 1080px;
         margin: 2rem auto; padding: 0 1rem; color: #222; }}
  header {{ border-bottom: 3px solid #222; padding-bottom: .8rem; margin-bottom: 1.2rem; }}
  h1 {{ margin: 0; font-size: 1.5rem; }}
  .subtitle {{ color: #666; margin-top: .3rem; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
          gap: 1rem; margin: 1.4rem 0; }}
  .card {{ background: #f6f6f6; border-radius: 10px; padding: 1rem 1.1rem; }}
  .card-head {{ display: flex; justify-content: space-between; align-items: center; gap: .6rem; }}
  .card-title {{ font-weight: 700; line-height: 1.3; }}
  .badge {{ padding: .25rem .7rem; border-radius: 999px; color: #fff; font-weight: 700;
           font-size: .72rem; letter-spacing: .05em; white-space: nowrap; }}
  .metrics {{ display: flex; gap: .8rem; margin-top: .8rem; }}
  .metric {{ flex: 1; background: #fff; border-radius: 8px; padding: .5rem .6rem; }}
  .m-label {{ font-size: .68rem; color: #888; text-transform: uppercase; }}
  .m-value {{ font-size: 1.1rem; font-weight: 700; margin-top: .1rem; }}
  .card-foot {{ font-size: .74rem; color: #999; margin-top: .7rem; }}
  .disclaimer {{ background: #fff6e5; border: 1px solid #eed9a0; border-radius: 8px;
                padding: .9rem 1.1rem; font-size: .88rem; line-height: 1.55; }}
  footer {{ color: #999; font-size: .8rem; margin-top: 2rem;
           border-top: 1px solid #eee; padding-top: .8rem; }}
</style>
</head>
<body>
<header>
  <h1>{title}</h1>
  <div class="subtitle">{subtitle}</div>
</header>

<div class="disclaimer"><b>Retrospective reconstruction — not a prediction.</b>
Statuses reflect how often each theme appeared in past news coverage.
The ELEVATED (momentum &ge; +1.0) / NEUTRAL / FADING (&lt; 0) thresholds are
arbitrary presentation buckets, not trading signals. Forward stores
(Google News RSS / Naver API) are kept separate from GDELT series and are
not directly comparable (no backfill, different normalization).</div>

<div class="grid">{card_html}
</div>

<footer>news-narrative-tracker v0.3 · generated {generated_on} ·
data: GDELT DOC 2.0 API cached snapshots. Not investment advice.</footer>
</body>
</html>
"""
