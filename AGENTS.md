# AGENTS.md

Instructions for coding agents (Codex, etc.) working in this repo. For the full
picture — architecture, metric definitions, evaluation rubric — read
[`HANDOFF.md`](./HANDOFF.md) first. This file is the short, binding version.

## What this project is

A retrospective news-narrative frequency tracker: count news articles per theme
(GDELT), normalize to a share, turn the daily series into a momentum score, and
report it. It is a **retrospective reconstruction, not a prediction engine** —
keep every claim consistent with that.

## Non-negotiable rules (do not violate, even to "improve" a number)

1. **No prediction language.** Retrospective demos are labeled as such in the
   README and in every generated report. No "would have caught the top."
2. **No accuracy-sounding number without a printed definition** (denominator,
   window, success criterion) next to it.
3. **Disclose data quirks, don't smooth them.** The GDELT gap and collapsed-norm
   days stay as missing; never interpolate.
4. **Auditability over cleverness.** Themes are explicit keyword dictionaries,
   not learned topics. Frequency first; sentiment/embeddings are a v2 question.
5. **Forward ≠ retrospective.** RSS/Naver forward stores can't backfill and are
   not directly comparable to GDELT shares; keep them separate.

Theme scope is governed by the inclusion rule in `config/themes.yaml`
(auditable / tradeable proxy / active) — apply it, don't freelance new themes.

## Verify before you commit (required)

This repo has shown a file-sync quirk between editors and git; a save can land
truncated or with stray bytes. After ANY edit, before committing, run:

```bash
python -m py_compile <changed .py files>
ruff check .
pytest -q            # expect: 36 passed
python scripts/run_demo.py
```

The demo must reproduce:
`narrative peak 2025-05-28 | z peak 2025-05-24 | price close peak 2025-10-14 | gap +139d`.
If a number moves without a data refresh, you broke something — stop and diff.

Also sanity-check that `requirements.txt` lists every tool the CI workflow calls
(currently: `pytest`, `ruff`), or CI will fail on a missing binary.

## Environment notes

- Python ≥3.9. `pip install -r requirements.txt`.
- Naver collector needs `NAVER_CLIENT_ID`/`NAVER_CLIENT_SECRET` (copy
  `.env.example` → `.env`; gitignored). Everything else runs offline from `data/`.
- Terminals may render the Korean strings in `config/themes.yaml` as mojibake;
  that is a console encoding artifact only — the files are UTF-8 and correct.
