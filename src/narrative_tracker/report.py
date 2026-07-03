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
