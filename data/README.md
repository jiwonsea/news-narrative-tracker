# Cached demo data

These snapshots make the demo reproducible offline. Retrieved **2026-07-02**.

| file | source | query / symbol | period |
|---|---|---|---|
| `gdelt_smr_oklo_20250101_20260630.csv` | GDELT DOC 2.0 API, `mode=timelinevolraw` | `(Oklo OR "small modular reactor") sourcelang:eng` | 2025-01-01 ~ 2026-06-30, daily |
| `gdelt_datacenter_nuclear_20250101_20260630.csv` | GDELT DOC 2.0 API, `mode=timelinevolraw` | `"data center" (nuclear OR reactor) sourcelang:eng` | 2025-01-01 ~ 2026-06-30, daily |
| `oklo_close_20250101_20260630.csv` | Yahoo Finance chart API | OKLO (NYSE), daily close, unadjusted | 2025-01-02 ~ 2026-06-30 |

Columns:
- `article_count` — number of matching articles that day (GDELT `value`)
- `total_articles_norm` — total articles GDELT monitored that day (GDELT `norm`); used to normalize counts into a share

Known data quirks (kept as-is, handled in code):
- GDELT gap: 2025-06-15 ~ 2025-07-01 has no rows (GDELT-side); the pipeline reindexes and keeps these days as NaN.
- 2025-12-06 and 2026-02-28 have collapsed `norm` values (494 / 1,949) — treated as missing by the `norm > 10,000` validity guard.
