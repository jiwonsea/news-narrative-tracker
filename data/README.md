# Cached demo data

These snapshots make the demo reproducible offline. Retrieved **2026-07-02**.

| file | source | query / symbol | period |
|---|---|---|---|
| `gdelt_smr_oklo_20250101_20260630.csv` | GDELT DOC 2.0 API, `mode=timelinevolraw` | `(Oklo OR "small modular reactor") sourcelang:eng` | 2025-01-01 ~ 2026-06-30, daily |
| `gdelt_datacenter_nuclear_20250101_20260630.csv` | GDELT DOC 2.0 API, `mode=timelinevolraw` | `"data center" (nuclear OR reactor) sourcelang:eng` | 2025-01-01 ~ 2026-06-30, daily |
| `gdelt_hbm_20250101_20260630.csv` | GDELT DOC 2.0 API, `mode=timelinevolraw` | `("high bandwidth memory" OR HBM3 OR HBM4) sourcelang:eng` | 2025-01-01 ~ 2026-06-30, daily |
| `gdelt_kdefense_20250101_20260630.csv` | GDELT DOC 2.0 API, `mode=timelinevolraw` | `("defense export" OR "arms export") ("South Korea" OR Korean) sourcelang:eng` | 2025-01-01 ~ 2026-06-30, daily |
| `oklo_close_20250101_20260630.csv` | Yahoo Finance chart API | OKLO (NYSE), daily close, unadjusted | 2025-01-02 ~ 2026-06-30 |

The two GDELT snapshots above (`gdelt_hbm_*`, `gdelt_kdefense_*`) were retrieved **2026-07-06** via `scripts/fetch_gdelt_snapshot.py` (529 daily rows each; same window and `date,article_count,total_articles_norm` format as the others). They share the identical `norm` series as the other GDELT files, so the same GDELT-side quirks apply (see below): the 2025-06-15~07-01 gap and the collapsed `norm` days (2025-12-06, 2026-02-28). Note: the `hbm_memory` GDELT query was corrected to wrap its OR'd terms in parentheses (`("high bandwidth memory" OR HBM3 OR HBM4) ...`); GDELT's DOC API rejects OR groups that are not parenthesized.

Columns:
- `article_count` — number of matching articles that day (GDELT `value`)
- `total_articles_norm` — total articles GDELT monitored that day (GDELT `norm`); used to normalize counts into a share

Known data quirks (kept as-is, handled in code):
- GDELT gap: 2025-06-15 ~ 2025-07-01 has no rows (GDELT-side); the pipeline reindexes and keeps these days as NaN.
- 2025-12-06 and 2026-02-28 have collapsed `norm` values (494 / 1,949) — treated as missing by the `norm > 10,000` validity guard.

## Snapshot backfill (was: dashboard NO DATA)

The `hbm_memory` and `defense_exports` themes were previously **NO DATA** —
defined in `config/themes.yaml` and wired into `scripts/build_dashboard.py` but
without a cached GDELT snapshot. Both were backfilled **2026-07-06** and now
render real momentum on the dashboard:

| theme key | file | query |
|---|---|---|
| `hbm_memory` | `gdelt_hbm_20250101_20260630.csv` | `("high bandwidth memory" OR HBM3 OR HBM4) sourcelang:eng` |
| `defense_exports` | `gdelt_kdefense_20250101_20260630.csv` | `("defense export" OR "arms export") ("South Korea" OR Korean) sourcelang:eng` |

To regenerate them (needs network access to `api.gdeltproject.org`):

```bash
python scripts/fetch_gdelt_snapshot.py hbm_memory
python scripts/fetch_gdelt_snapshot.py defense_exports
```

The script writes the same `date,article_count,total_articles_norm` format as
the files above. GDELT rate-limits to ~1 request / 5 seconds and returns a
plaintext "limit requests to one every 5 seconds" notice when throttled; the
client's retry logic handles this. After any refresh, update the retrieval date
here and re-run `python scripts/build_dashboard.py`; the cards fill in
automatically.
