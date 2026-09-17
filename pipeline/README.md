# Data pipeline

Offline scripts that turn official university pages into `Sourced` facts for `supabase/seed/universities.json`.

```
crawl.py  →  out/pages/<id>/*.json        (official pages only, robots.txt, 1 req/s)
extract.py → out/extracted/<id>.json      (Gemini; every field has a verbatim evidence quote or is null)
verify.py  → out/verified/<id>.json       (fields whose evidence is not in the page text are dropped)
           → out/report.json              (pages processed, % of fields verified)
embed.py   → doc_chunks (M5, not implemented)
```

## Run

```bash
python -m venv .venv && .venv/Scripts/pip install -r pipeline/requirements.txt   # (bin/pip on macOS/Linux)
python pipeline/crawl.py --ids mit,purdue,tudelft
LLM_API_KEY=... python pipeline/extract.py --ids mit,purdue,tudelft
python pipeline/verify.py            # add --merge to write verified facts into the seed file
python supabase/seed.py              # upsert into the database
```

## Rules

- Only official university / UCAS / Common Data Set pages. QS, THE, Mastersportal and Niche are never crawled.
- `verify.py --merge` keeps `is_demo: true`: a value is shown without the "Demo data" badge only after a person checks it against `source_url` and sets `is_demo: false`.
- Missing facts stay `null`; the app shows "не опубликовано" and never blocks a university because of missing data.

## Metrics

The current seed is hand-compiled demo data (all facts `is_demo: true`). Pipeline metrics from `out/report.json` go into the main README after a run.
