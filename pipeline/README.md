# Data pipeline

Offline scripts that turn official university pages into `Sourced` facts for `supabase/seed/universities.json`.

```
scorecard.py → out/scorecard/<id>.json    (College Scorecard API: acceptance rate, SAT 25/75, intl cost)
cds.py     → out/pages/<id>/cds-*.json    (official Common Data Set PDF/XLSX → text; ids in cds_sources.json)
crawl.py  →  out/pages/<id>/*.json        (official pages only, robots.txt, 1 req/s)
extract.py → out/extracted/<id>.json      (Gemini; every field has a verbatim evidence quote or is null)
cds_manual.json                          (hand extraction from CDS text, same shape, also verified)
verify.py  → out/verified/<id>.json       (malformed values and fields whose evidence is not in the page text are dropped)
           → out/report.json              (pages processed, % of fields verified)
embed.py   → doc_chunks (M5, not implemented)
```

## Run

```bash
python -m venv .venv && .venv/Scripts/pip install -r pipeline/requirements.txt   # (bin/pip on macOS/Linux)
python pipeline/scorecard.py          # SCORECARD_API_KEY optional (DEMO_KEY is enough for one request)
python pipeline/cds.py
python pipeline/crawl.py --ids mit,purdue,tudelft
LLM_API_KEY=... python pipeline/extract.py --ids mit,purdue,tudelft
python pipeline/verify.py --merge    # Scorecard + verified facts → seed with is_demo=false
python supabase/seed.py              # upsert into the database
.venv/Scripts/python -m pytest pipeline/tests -q   # pipeline tests (pip install pytest)
```

## Rules

- Only official university / UCAS / Common Data Set pages. QS, THE, Mastersportal and Niche are never crawled.
- `verify.py --merge` sets `is_demo: false` only for Scorecard API values and for facts whose quote is found in the official document. Everything else keeps its demo flag.
- Sites that block automated downloads (HTTP 403) or need a login are skipped, never worked around.
- Aggregators such as commondatasets.com are not used: their terms forbid harvesting their compiled data for republication.
- `checked_at` is the date the source document was downloaded, so re-running `verify.py --merge` doesn't change the seed.
- The crawler stays on the university's own site (`ox.ac.uk`, not the whole `ac.uk` zone) and crawls nothing when robots.txt answers 401/403.
- Missing facts stay `null`; the app shows "не опубликовано" and never blocks a university because of missing data.

## Metrics (2026-09-17)

- **Scorecard:** 19 US universities, 55/57 fields published (ASU and UCLA don't publish SAT).
- **CDS:** 12 official documents from 11 universities; 18 facts extracted, 18 verified.
- **Seed after merge:** 73 real facts, 484 demo facts (557 facts in 77 universities).
