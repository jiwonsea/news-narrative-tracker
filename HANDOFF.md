# HANDOFF — news-narrative-tracker

Handoff + evaluation brief for a coding agent (e.g. Codex) or human reviewer
picking this project up cold. It states what the project is, what is done, the
non-negotiable design rules, the decisions already made, what is still open,
and an explicit rubric for **evaluating** the work.

- **Version:** 0.4.0 · **Language:** Python ≥3.9 · **Tests:** 36 passing (pytest)
- **Lint:** `ruff check .` clean (E/F/W/I, line-length 100)
- **CI:** GitHub Actions — lint + tests on 3.10/3.12 + offline demo + dashboard build
- **Entry points:** `scripts/run_demo.py`, `scripts/build_dashboard.py`,
  `scripts/collect_forward.py`, `scripts/fetch_gdelt_snapshot.py`

---

## 1. One-paragraph summary

Quantify how loudly the market is talking about a theme by **counting news
articles**, not by feel. The pipeline collects daily article-frequency data
(GDELT DOC 2.0 API), matches it against explicit keyword **theme dictionaries**,
normalizes counts into a share of all articles monitored, and turns the daily
series into a **narrative momentum score** (trailing z-score of level +
acceleration). The flagship artifact is one retrospective demo: the
"SMR / advanced nuclear" narrative overlaid on Oklo (OKLO) share price,
2025-01 → 2026-06. It is explicitly a **retrospective reconstruction, not a
prediction engine** — the whole codebase is built to make that claim honestly.

Origin: a real OKLO trade where the author tracked the narrative qualitatively
and failed to realize gains near the 2025-10 top. The project's thesis is that
narrative *intensity* can be given units and therefore compared and backtested.

## 2. Architecture & module map

```
collect (GDELT / RSS / Naver)  ->  match (theme dicts)  ->  normalize (share)
                                                         ->  score (momentum)
                                                         ->  report (HTML)
```

| path | LOC | responsibility |
|---|---|---|
| `src/narrative_tracker/sources/gdelt.py` | 135 | GDELT DOC 2.0 client: build URL, fetch w/ rate-limit retry, parse timeline, cache CSV I/O. **Primary source** (only one that backfills history). |
| `src/narrative_tracker/sources/google_news.py` | 55 | Google News RSS client (forward collection only). |
| `src/narrative_tracker/sources/naver.py` | 190 | Naver News API v0.3 client (KR market, forward): env-var creds, retry/backoff on 429/5xx, originallink dedupe, optional pagination. |
| `src/narrative_tracker/themes.py` | 94 | Theme dataclass + YAML loader; auditable headline matching (left word boundary for ASCII, substring for CJK). Now also loads `proxy`/`rationale`. |
| `src/narrative_tracker/metrics.py` | 73 | share, share_ma7, freq_z (90d rolling z), chg_28d, momentum. **The core IP — every number traces to a raw count.** |
| `src/narrative_tracker/pipeline.py` | 36 | collect → score orchestration; price CSV loader. |
| `src/narrative_tracker/forward.py` | 112 | Live-collection store: dedupe against seen links, append per-day match counts. |
| `src/narrative_tracker/report.py` | 231 | Self-contained HTML: single-theme report + multi-theme signal-light dashboard. |
| `scripts/run_demo.py` | 194 | The OKLO/SMR retrospective demo (chart + HTML). Offline from `data/` snapshots; `--fetch` hits GDELT. |
| `scripts/build_dashboard.py` | 91 | Multi-theme dashboard from cached snapshots. |
| `scripts/collect_forward.py` | 91 | Daily forward collector (`--source google|naver`). |
| `scripts/fetch_gdelt_snapshot.py` | 65 | Cache a theme's GDELT timeline into `data/`. |

Tests (36) live in `tests/`: `test_metrics`, `test_themes`, `test_gdelt`,
`test_forward`, `test_naver`, `test_dashboard` (+ `tests/fixtures/`).

## 3. Metric definitions (the part that matters)

From `metrics.py` — memorize these; they are the product:

- `share` = daily count / total articles GDELT monitored that day (`norm`).
  Normalizes away growth/shrinkage of the news universe. `norm ≤ 10,000`
  treated as missing (guards outage days with collapsed totals).
- `share_ma7` = 7-day rolling mean of `share` (smooths day-of-week effects).
- `freq_z` = trailing **90-day** rolling z-score of `share_ma7` (min 30 obs):
  "how unusual is today vs the last quarter?"
- `chg_28d` = 28-day change rate of `share_ma7`: "accelerating or fading?"
- `momentum` = `0.5 * freq_z + 0.5 * z(chg_28d)` over the same 90d window:
  level + acceleration in one number.
- **NaN policy:** missing days stay NaN (never interpolated). Rolling stats use
  `min_periods` so early values are NaN rather than unstable.

Dashboard status buckets (ELEVATED ≥ +1.0 / NEUTRAL / FADING < 0) are
**presentation buckets, not trading signals** — stated everywhere they appear.

## 4. Non-negotiable design policies (do NOT violate)

These are the project's spine. A change that breaks one of these is wrong even
if it "improves" a number:

1. **No prediction language.** Retrospective demos are labeled as such in the
   README and in every generated report. No "would have caught the top."
2. **No accuracy-sounding number without a printed definition** next to it
   (denominator, window, success criterion).
3. **Disclose data quirks, don't smooth them.** The GDELT gap and collapsed-norm
   days are shown/handled as missing, never interpolated.
4. **Auditability over cleverness.** Themes are explicit keyword dictionaries,
   not learned topics, so every count is explainable. Frequency first; NLP
   (sentiment/embeddings) only if a frequency baseline proves insufficient (v2).
5. **Forward ≠ retrospective.** RSS/Naver forward stores cannot backfill and are
   NOT directly comparable to GDELT shares without normalization; kept separate.

## 5. Theme-selection inclusion rule (decision made 2026-07-09)

Previously implicit. Now a stated, author-independent rule (full text in
`config/themes.yaml` header; summary in README). A theme is admitted only if it
satisfies **all three**:

1. **Auditable** — expressible as an explicit EN+KR keyword dictionary.
2. **Tradeable proxy** — maps to ≥1 liquid instrument / small named basket,
   recorded per theme in the new `proxy:` field.
3. **Active** — a currently-live narrative (non-trivial trailing-90d GDELT
   frequency), not dormant/structural.

Governs **scope, not conviction**. Current four themes each carry a `proxy:`
and one-line `rationale:` documenting how they pass:
`smr_nuclear` (OKLO), `ai_datacenter_power` (VST/CEG/OKLO basket),
`hbm_memory` (SK Hynix/Samsung/Micron), `defense_exports` (Hanwha Aero/KAI).

## 6. Known issues & open decisions

- **GDELT data gap 2025-06-15 → 07-01 — RESOLVED as genuine.** Verified
  2026-07-09: all four theme snapshots miss the *identical* 17-day window with
  *identical* boundary `norm` values → platform-wide GDELT outage, not a
  per-query miss. Decision: keep the shaded gap, do not interpolate. Re-check
  for GDELT backfill from a networked machine (see `data/README.md`). Not
  collectable from the sandbox (no route to `api.gdeltproject.org`).
- **Keyword drift / hindsight vocabulary.** 2026 queries benefit from hindsight
  terms; "SMR" collides with other meanings. Matching hardened (left word
  boundary) but dictionary curation remains a judgment call.
- **Syndication inflates counts.** GDELT counts syndicated duplicates; no
  dedupe on the GDELT side (only forward RSS/Naver dedupe by link).
- **Single episode.** One narrative, one stock, one period — anecdotal by
  construction and stated as such.
- **`ai_datacenter_power` proxy is a basket**, not a single clean ticker —
  weaker overlay than the other three.

## 7. Run & verify

```bash
pip install -r requirements.txt
ruff check .                       # lint (must be clean)
pytest -q                          # 36 tests
python scripts/run_demo.py         # offline demo -> reports/ (chart + HTML)
python scripts/build_dashboard.py  # offline dashboard -> reports/dashboard.html
python scripts/run_demo.py --fetch # refresh from GDELT (needs network)
```

Expected demo stdout (reproducible from cached snapshots):
`narrative peak 2025-05-28 | z peak 2025-05-24 | price close peak 2025-10-14 | gap +139d`.
If these numbers change without a data refresh, something regressed.

Credentials (Naver, optional): copy `.env.example` → `.env`, set
`NAVER_CLIENT_ID`/`NAVER_CLIENT_SECRET` (loaded via python-dotenv; gitignored).

## 8. Recent session changelog (2026-07-09)

- Fixed a corrupted working tree that broke the build: stray code + null bytes
  in `gdelt.py` (and truncation in `run_demo.py`) — test collection failed
  before, now 36 pass.
- Code-quality pass: removed unused import, consolidated test imports, wrapped
  long lines, added final newlines. Added ruff config to `pyproject.toml`
  (line-length 100, E/F/W/I) + `ruff check .` step in CI + ruff in requirements.
- Bumped version 0.2.0 → 0.4.0 (matches README); added `python-dotenv` runtime dep.
- Committed the previously-uncommitted v0.3/v0.4 work in two logical commits
  (feature work; tooling). Local only — not pushed.
- Made the theme-selection rule explicit (this doc §5); added `proxy`/`rationale`
  fields to `Theme` + `config/themes.yaml`; README section.
- Verified & documented the GDELT gap as a true platform outage (§6).

## 9. Suggested next steps (priority order)

1. **Backfill re-check** for the GDELT gap from a networked host; if GDELT has
   backfilled, re-pull snapshots (the chart shading is data-driven and will
   close on its own).
2. **Forward-vs-GDELT normalization** so the live Naver/RSS stores become
   comparable to historical GDELT shares (currently intentionally separate).
3. **Theme lifecycle**: implement the "retire to archive when inactive" half of
   the inclusion rule (currently only admission is enforced).
4. **v2 NLP question**: only if frequency proves insufficient, add sentiment/
   embedding enrichment — must keep §4 policies intact.
5. Widen test coverage on `pipeline.py` and `report.py` (currently lighter).

## 10. Evaluation rubric (how to assess this project)

Score each dimension; the project's *identity* is rigor + honesty, so weight
those heaviest.

| dimension | what to check | evidence in repo |
|---|---|---|
| **Intellectual honesty** (highest weight) | Are all §4 policies actually upheld end-to-end? Any prediction language? Any undefined accuracy number? Any smoothed-over gap? | READMEs, report/dashboard disclaimers, NaN handling in `metrics.py`, `data/README.md` gap verification |
| **Reproducibility** | Does the offline demo reproduce the stated numbers byte-for-byte? Are data snapshots provenance-stamped? | `python scripts/run_demo.py`, `data/README.md` retrieval dates |
| **Metric soundness** | Are the metric definitions coherent, and is every number traceable to a raw count? Is the z-score window/min_periods defensible? | `metrics.py` |
| **Auditability of matching** | Can you always answer "why did this article match"? Do boundary rules behave (`(SMR)` matches, `asmr` doesn't, CJK adjacency works)? | `themes.py`, `tests/test_themes.py` |
| **Scope discipline** | Is theme inclusion a stated rule, applied consistently? Do all themes carry proxy + rationale? | `config/themes.yaml`, §5 |
| **Code quality** | Lint clean? Tests meaningful (not just smoke)? Clear module boundaries? | `ruff check .`, `pytest`, `tests/` |
| **CI / automation** | Does CI guard the invariants (lint + tests + offline demo + dashboard)? | `.github/workflows/ci.yml`, `collect.yml` |
| **Design judgment** | Are out-of-scope temptations (NLP, multi-stock claims) correctly deferred with reasons? | README roadmap, §4 |

**Fast evaluation path (≈5 min):** `pip install -r requirements.txt && ruff check . && pytest -q && python scripts/run_demo.py` — then read the generated `reports/demo_report.html` and confirm no forward-looking/prediction language and that every headline stat has a printed definition.

## 11. Handoff checklist for the next agent

- [ ] Read this file, then `config/themes.yaml` header (the policy) and `metrics.py` (the product).
- [ ] Run the fast evaluation path above; confirm the demo numbers match §7.
- [ ] Before changing any metric or theme, re-read §4 — those rules override "nicer numbers".
- [ ] Local commits are unpushed; coordinate with the author before `git push`.
- [ ] Environment note: this repo showed a file-sync quirk between editors; after any edit, verify with `python -m py_compile` + `ruff` + `pytest` before committing.
