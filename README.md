# Applyra — AI Admission Route Service

LOCUS Hackathon 2026, Case 02. Full specification: [SPEC.md](SPEC.md).

## Task

High-school students in Kazakhstan (grades 10–12) who want to study at top universities abroad don't need another list of universities. They need a route: where to apply, why each option fits, and what to do next.

## Solution

A short profile leads to explained recommendations (Dream / Target / Safety), then a comparison, a personal roadmap and one clear next step. The route updates visibly whenever the profile or achievements change.

- **Deterministic engine.** Pure Python in `backend/app/engine` decides tiers, chance labels, deadlines and numbers. The LLM only rephrases what the engine produced.
- **Explanations everywhere.** Every recommendation has at least two reasons tied to profile fields. Excluded universities show their blockers under "Почему не рекомендованы". When there are fewer than 3 results, suggestions say what to change.
- **Living route.** Every change is stored as a snapshot and a diff. The UI shows a toast ("Маршрут обновлён: +2, ↕1") that links to an animated Changes screen.
- **No percentages.** Chance is a label (низкие / средние / высокие). Acceptance rates are shown as "≈1 из N".
- **No login.** The app uses Supabase anonymous sign-in, so the session lives in the browser.
- **Resilient.** The last results are cached in localStorage for offline use, and a banner says when the server is waking up. Template texts replace AI text when the LLM is down.

## Stack

| Layer | Choice |
| --- | --- |
| Frontend | React 18, Vite 6, TypeScript (strict), React Router 6 |
| UI | Tailwind CSS 3, shadcn/ui (Radix primitives), lucide-react, Framer Motion |
| State | TanStack Query 5 (+ localStorage persister), Zustand 5 |
| Forms | React Hook Form + Zod |
| Charts | Recharts |
| API types | openapi-typescript (generated from FastAPI OpenAPI) |
| Backend | FastAPI, Pydantic v2, SQLAlchemy 2 async + asyncpg, PyJWT |
| DB / Auth | Supabase Postgres, Supabase anonymous auth |
| LLM | Google Gemini (`gemini-2.5-flash`) via `google-genai` |
| Tests | pytest (engine + API), Vitest (frontend utils) |
| Deploy | Vercel (frontend), Render (backend), Supabase (DB) |

## Architecture

```
React (Vite)  ──HTTPS + Supabase JWT──▶  FastAPI
   │  supabase-js (anon session only)        ├── engine/   pure, deterministic scoring + roadmap + diff
   │                                          ├── services/ profiles, snapshots, compute flow, ics
   └── TanStack Query cache (localStorage)    ├── llm/      prompts, template fallbacks, cache
                                              └── db ─────▶ Supabase Postgres (RLS on user tables)
pipeline/ (offline) ──▶ supabase/seed ──▶ Supabase (universities)
```

When a profile or achievement changes, the backend runs these steps: load the previous snapshot, save the change, run `recommend()` and `build_roadmap()`, compute `diff(prev, new)`, save the new snapshot, and return `ComputeResponse {result, roadmap, diff}`.
`POST /preview` is stateless. The Compare sliders use it, and it never writes anything.

```
backend/   FastAPI app, engine, tests, openapi.json
frontend/  React app
supabase/  migrations (SQL + RLS), seed JSON, migrate.py, seed.py
pipeline/  crawl → extract → verify (offline data collection)
```

## Run locally

### 1. Supabase

1. Create a project at supabase.com.
2. **Authentication → Sign In / Providers → enable "Allow anonymous sign-ins".**
3. Copy the values you need:
   - Project URL and anon key go to the frontend.
   - Database connection string goes to the backend. Use the **Session pooler** URI and prefix it with `postgresql+asyncpg://`.
   - JWT secret goes to the backend. Leave it empty if the project uses the new asymmetric signing keys; the backend then verifies tokens through JWKS.

### 2. Backend (Python 3.11+)

```bash
cd backend
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"        # macOS/Linux: .venv/bin/pip
cp .env.example .env                         # fill DATABASE_URL, SUPABASE_URL, SUPABASE_JWT_SECRET, LLM_API_KEY, CORS_ORIGINS
.venv/Scripts/python ../supabase/migrate.py  # applies supabase/migrations/*.sql (or paste them into the SQL editor)
.venv/Scripts/python ../supabase/seed.py     # validates seed JSON with Pydantic and upserts it
.venv/Scripts/uvicorn app.main:app --reload --port 8000
.venv/Scripts/pytest                         # 29 tests
```

Without a Postgres URL (`DATABASE_URL=sqlite+aiosqlite:///./local.db`), the backend creates tables and loads the seed on startup. Supabase is still needed for anonymous auth.

### 3. Frontend (Node 20+)

```bash
cd frontend
npm install
cp .env.example .env        # VITE_API_URL, VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY
npm run dev                 # http://localhost:5173
npm test                    # Vitest
npm run build
```

After changing backend schemas, regenerate the API types:

```bash
cd backend && .venv/Scripts/python scripts/dump_openapi.py
cd ../frontend && npm run gen:api
```

### Deploy

- **Backend → Render.** `render.yaml` is a blueprint with root `backend`, a uvicorn start command and health check `/health`. Set the env vars in the dashboard. `CORS_ORIGINS` must include the Vercel domain.
- **Frontend → Vercel.** Set the root directory to `frontend` (the SPA rewrite is in `vercel.json`) and set the three `VITE_*` variables.
- Free Render instances sleep. Before a demo, open `<backend>/health`. The frontend shows "Пробуждаем сервер…" for requests slower than 3 s.

## Test scenario for the jury

1. Open the site on a phone and press **"Попробовать демо-профиль"**. You land on the passport without logging in.
2. Press **"Показать варианты"**. You see recommendations in 3 tiers, each with reason chips. Expand "Почему не рекомендованы".
3. Press **"Изменить профиль"** and lower the budget from $50,000 to $20,000. A toast says "Маршрут обновлён: −N". Open **"Что изменилось"** to see which universities dropped out, with the cause ("Бюджет $50 000 → $20 000").
4. Change the major or add a country. The recommendation set changes, and the diff explains why.
5. Tap **"+ Достижение" → SAT → 1520 → Сохранить**. The demo student has SAT 1150, so Purdue moves from «Мечта» to «Надёжный», SAT gaps close for about 10 universities in the diff, and the roadmap drops the SAT retake step. The chance-history chart gets a new point.
6. Open **Сравнение** and move the "Цена" and "Престиж" sliders. Columns re-rank live, and the saved profile does not change.
7. Star a university ("В план"). **План** rebuilds around it with deadlines, dependencies and conflicts. Press "В календарь (.ics)".
8. Open **Сегодня** to see one next step, a progress ring and the chance-history chart with achievement markers.
9. Reload the page and the state is kept. **Настройки → Сбросить профиль** clears everything.
10. Stop the backend. The app keeps the cached data, shows an offline banner and disables edits.

## Scoring (backend/app/engine/config.py)

**Hard filters**, which put a university in "why not":
- none of the student's majors is offered
- over budget without a need-based aid option
- IELTS below the minimum with no retake planned before the deadline

A country that isn't selected is filtered out silently. Missing data never blocks a university; it adds a `DATA_NOT_PUBLISHED`, `COST_UNKNOWN` or `AID_UNKNOWN` risk instead.

**Fit:**
- SAT: ≥ p75 is *above*, ≥ p25 is *within*, otherwise *below* (the gap is p25 − SAT).
- GPA (converted to the 4.0 scale): ≥ avg is *above*, ≥ avg − 0.2 is *within*, otherwise *below*.
- IELTS (TOEFL converted with the ETS table): *ok*, *missing* or *below*.

**Score** (0–100, used only for ordering) is a weighted sum of factors in the 0..1 range:

| Factor | Weight | Value |
| --- | --- | --- |
| Academic (SAT, GPA) | 0.35 | above 1.0 · within 0.7 · missing 0.4 · below 0.3 |
| Language | 0.15 | ok 1.0 · missing 0.5 · below (retake planned) 0.3 |
| Affordability | 0.20 | within budget 1.0 · full-need aid 0.7 · partial 0.4 |
| Priorities (cost, prestige by world rank, aid, first country) | 0.15 | weighted by the student's sliders |
| Major match | 0.10 | main major 1.0 · other major 0.7 |
| Achievements | 0.05 | school 0.1 · city 0.2 · national 0.5 · international 1.0 (capped at 1) |

**Tier and chance** (the first matching rule wins):

| Rule | Tier | Chance |
| --- | --- | --- |
| acceptance < 15% | dream | low (medium only if all fits are *above*) |
| any fit *below* (SAT gap ≤ 150 and GPA gap ≤ 0.3 with ≥ 60 days left counts as closable) | dream | low |
| all fits *above*/*within* and acceptance ≥ 30% | safety | high |
| otherwise | target | medium |

The spec only names the closable-gap case. Unclosable gaps are also classified as dream, never target, and get a separate "hard to close" reason.

**Roadmap.**
- Steps come from favorites. Without favorites, the roadmap uses the best university in each tier.
- Due dates are counted back from the earliest deadline that hasn't passed, using result delays in `backend/app/data/exams.json`.
- Step ids are deterministic (`exam:SAT`, `doc:essay`, `apply:mit:EA`), so progress survives recomputation.
- A conflict is flagged when a dependency can't be finished before its dependant is due.

## AI

- **Model:** Google Gemini `gemini-2.5-flash`. It is fast and cheap, has a JSON response mode, and handles Russian well.
- **Routes:**
  - `/ai/passport` turns the template passport into natural language.
  - `/ai/explain` writes a summary of at most 2 sentences, using only the engine's reasons.
  - `/ai/roadmap-text` describes the roadmap steps.
- **Guardrails.** The prompts forbid new facts, numbers and percentages. Output is validated with Pydantic and checked for `%`, allowed `profile_field` values and matching step ids. If a check fails, the template is used. Calls time out after 8 s, and results are cached in `llm_cache` by a hash of the input.
- Every AI response includes `generated: true|false`. The UI marks template text as "Шаблонный текст".
- The app works fully with `LLM_API_KEY` empty.

## Data sources

`supabase/seed/universities.json` has **42 universities** (US 19, UK 10, NL 4, CA 4, KR 2, SG 2, DE 1) and 10 majors. Of 312 facts, **72 are real** (source link and check date in the UI), and the rest are demo values with a "Демо-данные" badge. Missing values are `null` and shown as "не опубликовано".

**Real data (US, collected 2026-09-17):**
- **[College Scorecard API](https://collegescorecard.ed.gov/data/api-documentation/)** (U.S. Department of Education, IPEDS, "latest" data) supplies these for all 19 US universities:
  - acceptance rate
  - SAT 25th/75th percentile (reading + math); ASU and UCLA don't publish SAT
  - cost for international students (cost of attendance − in-state tuition + out-of-state tuition)

  The script is `pipeline/scorecard.py`, and the IPEDS ids in `pipeline/us_unitids.json` were checked by hand.
- **Official Common Data Sets** (2025–26; Columbia 2024–25) come from each university's own institutional-research site (`pipeline/cds_sources.json`, `pipeline/cds.py`). From them we took average high-school GPA (C12), application closing / early deadlines (C14, C21, C22) and aid policy for nonresidents (H6), wherever the value was printed next to its label. Each fact stores a verbatim quote, and `pipeline/verify.py` rejects any quote that isn't in the document text.
  - Covered: Harvard, Princeton, Georgia Tech, Boston University, NYU, Michigan, Purdue, Columbia.
  - Files were also downloaded for Cornell, UChicago and ASU, but no value was quoted.
  - The MIT, Yale, Penn, UCLA and Minnesota sites block automated downloads, and Stanford requires a login. We skip those rather than work around them.
  - H6 only says whether need-based aid exists, so a need-based "yes" is stored as `partial`. `full_need` stays demo unless an official page says so.
- **Verification rule.** A value from the Scorecard API, or a CDS value whose quote is found in the official document, gets `is_demo: false`. This is automatic verification, which goes further than the spec's "human-verified" wording, and was agreed for the hackathon.
- **Why commondatasets.com was not used.** Its Terms & Conditions forbid scraping or bulk-harvesting its compiled database for republication. We went to the same public primary sources instead.

**Demo data:**
- The remaining US fields and all universities outside the US are approximate figures compiled by hand (`supabase/seed/build_seed.py`). The build script keeps rows that already have verified facts.
- `world_rank` is taken approximately from QS World University Rankings 2025. It is used only for the prestige priority and is not scraped.
- Deadlines come from a single admission cycle. The engine shifts them to the student's intake year (Aug–Dec deadlines belong to the next year's intake).

**Pipeline metrics** (`pipeline/out/report.json`):
- Scorecard: 19 universities, 55 of 57 fields published.
- CDS: 12 documents from 11 universities; 17 facts extracted, 17 verified (100%).
- Seed: 72 real facts, 240 demo facts.

## Ready-made components and libraries

shadcn/ui (Button, Sheet, Slider, Switch, Collapsible patterns), Radix UI primitives, Tailwind CSS, tailwindcss-animate, class-variance-authority, clsx, tailwind-merge, lucide-react icons, Framer Motion, Recharts, TanStack Query (+ persist client, sync storage persister), Zustand, React Hook Form, Zod, @hookform/resolvers, sonner (toasts), React Router, @supabase/supabase-js, openapi-typescript. Fonts: Manrope and Unbounded (Google Fonts).
Backend: FastAPI, Pydantic, pydantic-settings, SQLAlchemy, asyncpg, aiosqlite, PyJWT, httpx, google-genai, pytest. Pipeline: trafilatura, httpx, pypdf.

## Limitations

- GPA conversion from the 5-point scale to the 4.0 scale is **approximate**, and the UI says so.
- Acceptance rates are **overall**, not specific to international applicants.
- Only US universities have real data (Scorecard + CDS), and verification is automatic (the quote must match the source), not done by a person. Other countries are demo data. Deadlines are projected to the intake year.
- Anonymous sessions are **per browser**. Clearing site data or switching devices starts a new profile.
- The "requirement unreachable" filter currently covers the IELTS minimum only. Other requirements (A-levels, Studienkolleg, interviews) are shown as information.
- RAG `/ai/ask` and the voice guide (M5) are not implemented.

## Team

| Role | Name |
| --- | --- |
| Product / full-stack | _add name_ |
| Design | _add name_ |
| Data | _add name_ |

## Deployed URLs

- Frontend: _add Vercel URL_
- Backend: _add Render URL_ (`/health`, `/docs`)
