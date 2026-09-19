# Applyra — AI Admission Route Service

LOCUS Hackathon 2026, Case 02 (participation code `LOCUSCASE2`). Full product and engineering specification: [SPEC.md](SPEC.md).

## Submission

| Item | Link / value |
| --- | --- |
| Working product | https://locus-apex.vercel.app |
| Backend API | https://locus-apex.onrender.com (`/health`, `/docs`) |
| Test login | **Not needed.** The app signs every visitor in anonymously (Supabase anonymous auth). Press "Попробовать демо-профиль" on the landing page to get a filled profile. |
| GitHub | https://github.com/dracs9/locus_apex (full commit history) |
| Technical reference | [Technical reference](#technical-reference) section of this README |

> The backend runs on a free Render instance and sleeps when idle. Open `/health` about a minute before a demo. The frontend shows "Пробуждаем сервер…" for requests slower than 3 s and never shows a blank screen.

## Contents

[Task](#task) · [Solution](#solution) · [Stack](#stack) · [Architecture](#architecture) · [Run locally](#run-locally) · [Test scenario](#test-scenario-for-the-jury) · [Team](#team) · [Scoring](#scoring-backendappengineconfigpy) · [Plan](#plan-roadmap) · [AI](#ai) · [Data sources](#data-sources) · [Essays](#essays-essays) · [Ready-made components](#ready-made-components-and-libraries) · [Technical reference](#technical-reference) · [Limitations](#limitations)

## Task

High-school students in Kazakhstan (grades 9–12) who want to study at top universities abroad (US, UK, Europe, Asia) don't need another list of universities. They need a route: where to apply, why each option fits, and what to do next.

## Solution

A short profile leads to explained recommendations (Dream / Target / Safety), then a comparison, a personal plan and one clear next step. The route updates visibly whenever the profile or achievements change.

- **Deterministic engine.** Pure Python in `backend/app/engine` decides tiers, chance labels, deadlines and numbers. The LLM only rephrases what the engine produced and proposes plan changes that the student confirms.
- **Explanations everywhere.** Every recommendation has at least two reasons tied to profile fields. Excluded universities show their blockers under "Почему не рекомендованы". When there are fewer than 3 results, suggestions say what to change.
- **Living route.** Every change is stored as a snapshot and a diff. The UI shows a toast ("Маршрут обновлён: +2, ↕1") that links to an animated Changes screen with the cause.
- **Student-built plan.** The engine suggests steps (exams, documents, applications, activities), each with a reason. The student adds them or writes their own, then edits dates, marks steps done and exports them to a calendar (.ics). Conflicts such as an exam result arriving after a deadline are highlighted.
- **Profile that fits Kazakh schools.** Grades 9–12; GPA on a 5-point, 4-point, 100-point or IB MYP (/8) scale; a yearly family contribution in USD (0 means full aid is needed); an optional 30-question interest quiz based on Holland's RIASEC themes that suggests majors.
- **Countries as navigation.** The main menu lists countries. Recommendations are grouped by country, with filters by country and difficulty; `/recommendations?country=US` opens a filter without changing the profile.
- **AI mentor.** A chat that knows the profile, recommendations and plan. It answers with catalog facts and proposes plan changes as cards with "Применить / Отклонить".
- **Essays.** 144 essays by admitted students with explained reading recommendations.
- **No percentages.** Chance is a label (низкие / средние / высокие). Acceptance rates are shown as "≈1 из N".
- **No login.** Supabase anonymous sign-in; the session lives in the browser.
- **Resilient.** The last results are cached in localStorage for offline use, a banner says when the server is waking up or offline, and template texts replace AI text when the LLM is down.

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
| DB / Auth / Files | Supabase Postgres (RLS), Supabase anonymous auth, Supabase Storage |
| LLM | Google Gemini (`gemini-3.8-flash`, set by `LLM_MODEL`) via `google-genai` |
| Data pipeline | Python: httpx, trafilatura, pypdf; College Scorecard API |
| Tests | pytest (engine, API, pipeline), Vitest (frontend logic) |
| Deploy | Vercel (frontend), Render (backend), Supabase (DB, auth, storage) |

## Architecture

```
Browser: React (Vite)
   │  supabase-js — anonymous session only
   │  TanStack Query cache (localStorage, offline fallback)
   │
   └──HTTPS + Supabase JWT──▶ FastAPI (Render)
                               ├── routers/   catalog, profile, achievements, recommendations,
                               │              roadmap, history, essays, ai, mentor, demo
                               ├── engine/    pure, deterministic: normalize → filters → fit → score
                               │              → tier → recommend; diff, suggestions, roadmap, history
                               ├── services/  profiles, snapshots, compute flow, plan, ics, essays,
                               │              mentor context, attachment storage
                               ├── llm/       prompts, template fallbacks, cache, mentor tools ──▶ Gemini API
                               └── db ──────▶ Supabase Postgres (RLS on user tables) + Storage (photos)

pipeline/ (offline) ──▶ College Scorecard API, official Common Data Sets, openessays.org
                    ──▶ supabase/seed/*.json ──▶ supabase/seed.py ──▶ Postgres
```

- The frontend talks to Supabase only for anonymous auth. All data goes through FastAPI, which verifies the JWT (JWKS or legacy secret) and uses `sub` as `user_id` in every query.
- When a profile, achievement or favorite changes, the backend loads the previous snapshot, saves the change, runs `recommend()` and `suggest_actions()`, computes `diff(prev, new)`, saves a new snapshot and returns `ComputeResponse {result, roadmap, diff}`.
- `POST /preview` is stateless. The Compare sliders and the "other country" view use it, and it never writes anything.

```
backend/   FastAPI app, engine, services, llm, tests, openapi.json
frontend/  React app
supabase/  migrations 0001–0005 (SQL + RLS), seed JSON, migrate.py, seed.py
pipeline/  scorecard → cds → crawl → extract → verify, essays (offline data collection)
docs/      team notes (Russian)
```

## Run locally

Requirements: Python 3.11+, Node 20+, a Supabase project. Shortcut scripts `run-back.sh` and `run-front.sh` start both apps once they are installed.

### 1. Supabase

1. Create a project at supabase.com.
2. **Authentication → Sign In / Providers → enable "Allow anonymous sign-ins".**
3. Copy the values you need:
   - Project URL and anon key go to the frontend.
   - Database connection string goes to the backend. Use the **Session pooler** URI and prefix it with `postgresql+asyncpg://`.
   - JWT secret goes to the backend. Leave it empty if the project uses the new asymmetric signing keys; the backend then verifies tokens through JWKS.
   - Service key (`service_role` or `sb_secret_…`) goes to the backend as `SUPABASE_SERVICE_KEY`. It is used only to store achievement photos in the private `achievement-files` bucket, which migration `0002` creates. Without it, links still work and photo upload answers "загрузка фото не настроена".

### 2. Backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"        # macOS/Linux: .venv/bin/pip
cp .env.example .env                         # fill DATABASE_URL, SUPABASE_URL, SUPABASE_JWT_SECRET, SUPABASE_SERVICE_KEY, LLM_API_KEY, LLM_MODEL, CORS_ORIGINS
.venv/Scripts/python ../supabase/migrate.py  # applies supabase/migrations/*.sql (or paste them into the SQL editor)
.venv/Scripts/python ../supabase/seed.py     # validates seed JSON (universities, majors, essays) with Pydantic and upserts it
.venv/Scripts/uvicorn app.main:app --reload --port 8000
.venv/Scripts/pytest                         # 70 tests
```

Without a Postgres URL (`DATABASE_URL=sqlite+aiosqlite:///./local.db`), the backend creates tables and loads the seed on startup. Supabase is still needed for anonymous auth. With `LLM_API_KEY` empty, every AI feature falls back to template text.

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env        # VITE_API_URL, VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY
npm run dev                 # http://localhost:5173
npm test                    # Vitest, 25 tests
npm run build
```

After changing backend schemas, regenerate the API types:

```bash
cd backend && .venv/Scripts/python scripts/dump_openapi.py
cd ../frontend && npm run gen:api
```

### 4. Data pipeline (optional)

See [pipeline/README.md](pipeline/README.md). The seed in `supabase/seed/` is already built, so the app runs without it.

### Deploy

- **Backend → Render.** `render.yaml` is a blueprint with root `backend`, a uvicorn start command and health check `/health`. Set the env vars in the dashboard. `CORS_ORIGINS` must include the Vercel domain.
- **Frontend → Vercel.** Set the root directory to `frontend` (the SPA rewrite is in `vercel.json`) and set the three `VITE_*` variables.
- Secrets live only in the hosts' env settings. `.env` files are git-ignored; both apps ship `.env.example`.

## Test scenario for the jury

Takes about 5 minutes on a phone or a desktop.

1. Open https://locus-apex.vercel.app and press **"Попробовать демо-профиль"**. You land on the passport without logging in. (Or press "Построить маршрут" to go through the onboarding: one question per screen, about 2 minutes.)
2. Press **"Показать варианты"**. You see recommendations in 3 tiers, each with reason chips. Expand "Почему не рекомендованы".
3. Press **"Изменить профиль"** and lower the budget from $50,000 to $20,000. A toast says "Маршрут обновлён: −N". Open **"Что изменилось"** to see which universities dropped out, with the cause ("Бюджет $50 000 → $20 000").
4. Change the major or add a country. The recommendation set changes, and the diff explains why. Use the country filter to look at one country without changing the profile.
5. Tap **"+ Достижение" → SAT → 1520 → Сохранить**. The demo student has SAT 1150, so Purdue moves from «Мечта» to «Надёжный», SAT gaps close for about 10 universities in the diff, and the SAT retake disappears from the plan recommendations. The chance-history chart gets a new point.
6. Open **Сравнение** and move the "Цена" and "Престиж" sliders. Columns re-rank live, and the saved profile does not change.
7. Star a university ("В план"), then open **План**. Below the student's steps, **"Рекомендации для тебя"** lists activities matched to the majors and interests, plus exams, documents and the application deadline for the starred university, each with a reason. Tap "В план" on one, add your own step with "Свой шаг", change its date, mark it done. Press "В календарь (.ics)".
8. Open **Сегодня** to see one next step, a progress ring and the chance-history chart with achievement markers.
9. Open **Мои интересы** and take the RIASEC quiz. It suggests majors; confirm or change them and watch the recommendations update.
10. Open **Ментор** and ask «Какие активности добавить в план?». The mentor answers from the profile and proposes steps; press **Применить** on one and it appears in **План**. Ask «Сколько стоит год в Purdue?»: the answer quotes the catalog and warns when a figure is demo data.
11. Open **Эссе**: recommended essays come with reasons; open one to read it with author, license and source.
12. Open **Достижения**, edit an achievement and attach a photo of a diploma or a link to a project (up to 5 per achievement).
13. Open a university page: every fact has a source badge (link + check date) or a "Демо-данные" badge; unknown values say "не опубликовано".
14. Reload the page and the state is kept. **Настройки → Сбросить профиль** clears everything.
15. Stop the backend (or go offline). The app keeps the cached data, shows an offline banner and disables edits.

## Team

| Role | Name | Responsibilities |
| --- | --- | --- |
| Captain, full-stack | _add name_ | backend, scoring engine, deploy, submission |
| Frontend / UX | _add name_ | screens, design system, onboarding |
| Data | _add name_ | pipeline, university facts, essays |

## Scoring (backend/app/engine/config.py)

**Profile normalization:**
- GPA on the 5-point scale is converted to the 4.0 scale with a linear table (5.0→4.0, 4.5→3.5, 4.0→3.0, 3.5→2.5, 3.0→2.0). The UI says it is approximate. A 4-point GPA is used as is. 100-point and IB MYP /8 values are stored but not converted, because there is no official conversion; the engine then treats GPA as missing and says so.
- TOEFL is converted to the IELTS scale with the ETS table. Only `done` achievements count; `planned` ones never affect scoring.
- The budget is the family's yearly contribution (tuition + living). The onboarding always considers financial aid when the cost is above the contribution; this is not a promise of a grant.

**Hard filters**, which put a university in "why not":
- none of the student's majors is offered
- over budget without a need-based aid option
- IELTS below the minimum with no retake planned before the deadline

A country that isn't selected is filtered out silently. Missing data never blocks a university; it adds a `DATA_NOT_PUBLISHED`, `COST_UNKNOWN` or `AID_UNKNOWN` risk instead.

**Fit:**
- SAT: ≥ p75 is *above*, ≥ p25 is *within*, otherwise *below* (the gap is p25 − SAT).
- GPA (4.0 scale): ≥ avg is *above*, ≥ avg − 0.2 is *within*, otherwise *below*.
- IELTS: *ok*, *missing* or *below*.

**Score** (0–100, used only for ordering) is a weighted sum of factors in the 0..1 range:

| Factor | Weight | Value |
| --- | --- | --- |
| Academic (SAT, GPA) | 0.35 | above 1.0 · within 0.7 · missing 0.4 · below 0.3 |
| Language | 0.15 | ok 1.0 · missing 0.5 · below (retake planned) 0.3 |
| Affordability | 0.20 | within budget 1.0 · full-need aid 0.7 · partial 0.4 |
| Priorities (cost, prestige by world rank, aid, first country) | 0.15 | weighted by the student's sliders |
| Major match | 0.10 | main major 1.0 · other major 0.7; refined by RIASEC interest fit within the chosen majors |
| Achievements | 0.05 | school 0.1 · city 0.2 · national 0.5 · international 1.0 (capped at 1) |

**Tier and chance** (the first matching rule wins):

| Rule | Tier | Chance |
| --- | --- | --- |
| acceptance < 15% | dream | low (medium only if all fits are *above*) |
| any fit *below* (SAT gap ≤ 150 and GPA gap ≤ 0.3 with ≥ 60 days left counts as closable) | dream | low |
| all fits *above*/*within* and acceptance ≥ 30% | safety | high |
| otherwise | target | medium |

The spec only names the closable-gap case. Unclosable gaps are also classified as dream, never target, and get a separate "hard to close" reason. Results are sorted by tier, then score, then id, so the same input always gives the same output.

**Interests (RIASEC).** `backend/app/data/holland.json` holds 30 original questions over six themes (Realistic, Investigative, Artistic, Social, Enterprising, Conventional), five answer levels each. Each theme scores 0–20. The result suggests majors, which the student confirms. The engine uses interests only inside the major-match factor (weight 0.10) and only among majors the student chose. The quiz is based on Holland's model; it is not the Truity test and has not been psychometrically validated.

## Plan (roadmap)

The engine doesn't write the plan. It suggests steps, and the student builds the plan.
- `suggest_actions()` (pure) returns suggestions, each with a reason (`why`) tied to a profile field:
  - from the target universities (favorites, otherwise the best university of each tier): register for and take SAT/IELTS when the score is missing or below the requirement, the documents each university asks for, "raise grades" when the GPA is below average, and the application itself. Dates are counted back from the earliest deadline that hasn't passed, using result delays in `backend/app/data/exams.json`, and carry the deadline's source or demo flag.
  - from the activity catalog `backend/app/data/activities.json` (25 generic ideas: olympiads, research, hackathons, volunteering, debates, portfolio, summer school…). Ranked by major match (2), top Holland interest (1), general ideas (0.5); skipped when the student already has that achievement type at national level or higher. Up to 8, due no sooner than in 14 days and at least 30 days before the earliest deadline. The catalog names no specific competitions or dates.
- Suggestion ids are deterministic (`exam:SAT`, `doc:essay`, `apply:mit:EA`, `act:hackathon`); an added suggestion leaves the list.
- The plan is the `roadmap_items` table (migration `0003`): steps added from suggestions (with their `source_key`) or written by the student, all editable and deletable. `build_roadmap()` orders them, links an application step to the exam and document steps of the same university, and flags conflicts: overdue steps, and an exam whose result would arrive after that application's date. `next_step_id` is the earliest undone step whose dependencies are done.
- Loading the demo profile adds the first two suggestions of each kind so the plan isn't empty.

## Achievement attachments

- Photos (JPG, PNG, WebP, HEIC, up to 5 MB) and http(s) links, **up to 5 per achievement**. Photos are downscaled in the browser to about 1600 px before upload.
- The backend checks each file's real type by its magic bytes and stores it in a **private** Supabase Storage bucket at `{user_id}/{achievement_id}/…`. The frontend never talks to Storage directly: `GET /me/profile` returns signed URLs that live 1 hour.
- Deleting an achievement, resetting the profile or loading the demo profile removes the stored files.
- Attachments are evidence for the student only. They don't affect scoring and never trigger a recomputation.

## AI

- **Model:** Google Gemini `gemini-3.8-flash` through the official `google-genai` SDK, chosen by the `LLM_MODEL` env variable. Why Gemini Flash: fast and cheap, JSON response mode, function calling, good Russian.
- **Routes:**
  - `/ai/passport` turns the template passport (goal, 3 strengths, 2 constraints, main risk) into natural language.
  - `/ai/explain` writes a summary of at most 2 sentences, using only the engine's reasons.
  - `/ai/roadmap-text` describes plan steps and suggestions (what to do and why), using only the title, kind and reason.
- **Guardrails.** The prompts forbid new facts, numbers and percentages. Output is validated with Pydantic and checked for `%`, allowed `profile_field` values and matching step ids. If a check fails, the template is used. Calls time out after 8 s, and results are cached in `llm_cache` by a hash of the input.
- Every AI response includes `generated: true|false`. The UI marks template text as "Шаблонный текст".
- The app works fully with `LLM_API_KEY` empty.

### AI mentor (`/mentor`)

A chat with a mentor who knows the student and can suggest plan changes, which the student confirms.
- **Model:** the same Gemini model with function calling (`backend/app/llm/mentor_model.py`), temperature 0.3, 25 s per call, at most 4 tool rounds per reply.
- **Context:** built fresh for every message in `backend/app/services/mentor.py`: profile (grades, majors, countries, budget, best scores, achievements, Holland code), the top 10 recommendations with the engine's tier, chance and reasons, favorites, the student's plan with conflicts, and the plan suggestions with their reasons.
- **Retrieval tools:** `get_university` (every fact with its source and demo flag, projected deadlines, requirements, the student's tier for it) and `find_universities` (catalog search by country, major, cost). The catalog is small and structured, so tool lookups replace vector search.
- **Plan changes need confirmation.** `propose_add_suggestion`, `propose_add_step`, `propose_update_step` and `propose_delete_step` only validate and record a proposal: the step or suggestion must belong to the student, dates must fall between today and two years ahead, fields go through the same Pydantic models as the plan API. Applying runs the same code as the plan endpoints.
- **Rules in the prompt:** facts only from the context and tools, unknown values are "не опубликовано", demo data is called approximate, no admission chances in percent (a reply that pairs "шанс" with a percentage is sanitized server-side), no claims that the plan already changed, off-topic questions are steered back.
- **History** is stored in `mentor_messages` (migration `0004`, RLS), the last 100 per student; the last 12 go to the model. Reset clears it. Without `LLM_API_KEY` the mentor answers with a template that names the next plan step.

## Data sources

`supabase/seed/universities.json` has **77 universities** in 17 countries (US 19, UK 10, NL 4, CA 4, AU 4, and 3 each for DE, KR, SG, HK, CN, IT, JP, CH, FR, IE, SE and ES) and 10 majors. Of 557 facts, **73 are real** (source link and check date in the UI), and the rest are demo values with a "Демо-данные" badge. Missing values are `null` and shown as "не опубликовано".

**Real data (US, collected 2026-09-17):**
- **[College Scorecard API](https://collegescorecard.ed.gov/data/api-documentation/)** (U.S. Department of Education, IPEDS, "latest" data) supplies these for all 19 US universities:
  - acceptance rate
  - SAT 25th/75th percentile as the sum of the reading and math section percentiles (an approximation: Scorecard has no composite percentiles); ASU and UCLA don't publish SAT
  - cost for international students (cost of attendance − in-state tuition + out-of-state tuition)

  The script is `pipeline/scorecard.py`, and the IPEDS ids in `pipeline/us_unitids.json` were checked by hand.
- **Official Common Data Sets** (2025–26; Columbia 2024–25) come from each university's own institutional-research site (`pipeline/cds_sources.json`, `pipeline/cds.py`). From them we took average high-school GPA (C12), application closing / early deadlines (C14, C21, C22) and aid policy for nonresidents (H6), wherever the value was printed next to its label. Each fact stores a verbatim quote, and `pipeline/verify.py` rejects any quote that isn't in the document text.
  - Covered: Harvard, Princeton, Georgia Tech, Boston University, NYU, Michigan, Purdue, Columbia.
  - Files were also downloaded for Cornell, UChicago and ASU, but no value was quoted.
  - The MIT, Yale, Penn, UCLA and Minnesota sites block automated downloads, and Stanford requires a login. We skip those rather than work around them.
  - H6 only says whether need-based aid exists, so a need-based "yes" is stored as `partial`. `full_need` stays demo unless an official page says so.
- **Exam timings** (`backend/app/data/exams.json`): SAT, IELTS and TOEFL result delays from the official College Board, IELTS and ETS pages (checked 2026-09-17, with quotes).
- **Essays:** [openessays.org](https://openessays.org), collected 2026-09-18 (see [Essays](#essays-essays)).
- **RIASEC model:** [Holland Code Career Test, Truity](https://www.truity.com/test/holland-code-career-test) and [O*NET Interest Profiler](https://www.onetcenter.org/IP.html) as references for the six themes; the questions are our own. IB MYP scale: [IB MYP grading](https://ibo.org/programmes/middle-years-programme/assessment-and-exams/grading-and-awards/).

**Demo data:**
- The remaining US fields and all universities outside the US are approximate figures compiled by hand (`supabase/seed/build_seed.py`). The build script keeps rows that already have verified facts.
- `world_rank` is taken approximately from **QS World University Rankings 2025**. It is used only for the prestige priority and is not scraped. Bocconi, SMU and IE University are specialised universities without a comparable overall QS position, so they get conservative placeholder ranks (300, 500 and 500).
- Chinese universities list `ielts_min` as unknown: most bachelor programmes are taught in Chinese and ask for HSK, which is shown as an extra requirement.
- Swiss (ETH, UZH, EPFL), Sorbonne and University of Barcelona bachelors are taught in German, French or Spanish, so `ielts_min` is unknown and the language requirement is listed under extra requirements.
- Deadlines come from a single admission cycle. The engine shifts them to the student's intake year (Aug–Dec deadlines belong to the next year's intake).

**Verification rule.** A value from the Scorecard API, or a CDS value whose quote is found in the official document, gets `is_demo: false`. This is automatic verification, which goes further than the spec's "human-verified" wording, and was agreed for the hackathon. commondatasets.com was not used: its terms forbid scraping or bulk-harvesting its compiled database for republication, so we went to the same public primary sources instead. QS, THE, Mastersportal and Niche are never scraped.

**Pipeline metrics** (`pipeline/out/report.json`):
- Scorecard: 19 universities, 55 of 57 fields published.
- CDS: 12 documents from 11 universities; 17 facts extracted, 17 verified (100%).
- Seed: 73 real facts, 484 demo facts.
- Essays (`python pipeline/essays.py`): 144 essays, 67 matched to catalog universities, 141 with at least one major.

## Essays (`/essays`)

A collection of **144 essays by admitted students** from [openessays.org](https://openessays.org), scraped on 2026-09-18: 16 bachelor's (Common App / Personal Statement), 7 master's, 119 PhD, 1 MBA and 1 other. `pipeline/essays.py` normalizes the raw dump (`data/openessays_dump/`, git-ignored) into `supabase/seed/essays.json`. It parses the school from the title, maps 67 essays to catalog universities, and maps the free-text program onto the 10 majors by keywords. `supabase/seed.py` validates the file with Pydantic and upserts it into the `essays` table (migration `0005`: public read under RLS, like the catalog).

- **Screens.** The list has search and filters by level, essay type, major and university, plus "only universities from my list" and three sort orders. The essay page shows the full text, author, license, links to the source and the original, the university page and similar essays.
- **Recommendations** (`GET /me/essays/recommended`) are deterministic and explained. Weights: bachelor's level +3, university in the student's plan +3 (or in their recommendations +2), shared major +2, Common App / personal statement +1. Ties are broken by id, and every card shows its reasons.
- **Licenses.** 109 essays are CC BY-NC-SA 4.0. For 35, including all bachelor's essays, the source does not state a license; they were published by their authors as public success stories. Every essay is shown with the author's name, a license badge and links to openessays.org and the original. We will remove an essay at the author's request.

## Ready-made components and libraries

- **Frontend:** shadcn/ui (Button, Sheet, Slider, Switch, Collapsible patterns), Radix UI primitives, Tailwind CSS, tailwindcss-animate, class-variance-authority, clsx, tailwind-merge, lucide-react icons, Framer Motion, Recharts, TanStack Query (+ persist client, sync storage persister), Zustand, React Hook Form, Zod, @hookform/resolvers, sonner (toasts), React Router, @supabase/supabase-js, openapi-typescript, Vitest.
- **Fonts:** Manrope (UI) and Playfair Display Italic (the accented word in the landing headline), both from Google Fonts.
- **Backend:** FastAPI, Uvicorn, Pydantic, pydantic-settings, SQLAlchemy, asyncpg, aiosqlite, PyJWT, httpx, google-genai, python-multipart, pytest.
- **Pipeline:** httpx, trafilatura, pypdf, pytest.

Everything else (design-system components in `frontend/src/components/ds`, the scoring engine, the plan, the mentor, the RIASEC questions) is our own code.

## Technical reference

| Area | What we use | Why / how |
| --- | --- | --- |
| AI model | Google Gemini `gemini-3.8-flash` (`google-genai` SDK) | Passport text, explanations, step descriptions, mentor chat with function calling. Never decides tiers, chances, numbers or deadlines. |
| APIs we call | Gemini API; Supabase Auth, Postgres, Storage; College Scorecard API (offline) | Gemini only from the backend; keys only in host env settings. |
| Our API | FastAPI, about 35 endpoints, OpenAPI at `/docs` | `/catalog/*`, `/me/*` (JWT), `/preview`, `/ai/*`, `/essays` |
| External services | Vercel (frontend), Render (backend), Supabase (DB, auth, storage) | Free tiers; see the cold-start note under Submission. |
| Data | 77 universities / 17 countries / 10 majors; 144 essays; 25 activity ideas; exam timings; 30 RIASEC questions | Every fact is `Sourced {value, source_url, checked_at, evidence, is_demo}`. |
| Database | Tables `universities`, `majors`, `profiles`, `achievements`, `achievement_attachments`, `favorites`, `roadmap_items`, `roadmap_progress`, `snapshots`, `llm_cache`, `mentor_messages`, `essays` | Migrations `0001`–`0005`; RLS `user_id = auth.uid()` on user tables; the backend filters every query by the JWT user. |

**How we check the work:**
- **Engine tests (pytest):** determinism, SAT above p25 moves dream → target, a lower budget removes a no-aid university with `OVER_BUDGET`, a major change changes the set, acceptance < 15% is never safety, planned achievements don't count, missing data never blocks, diff added/removed/tier_changed, exam-after-deadline conflict, RIASEC scoring.
- **API tests (pytest):** `PUT /me/profile` returns a diff, user A can't read user B's data, `/preview` saves nothing, error format, attachments, essays, mentor proposals and guardrails. **70 backend tests.**
- **Frontend tests (Vitest):** formatting, profile completeness and payloads, interests, suggestions, image downscaling, essays. **25 tests**, plus a TypeScript strict build.
- **Pipeline tests (pytest):** crawl scoping, robots handling, evidence verification, value validation. **38 tests.**
- **Data verification:** a fact is marked real only when it comes from the Scorecard API or its verbatim quote is found in the official document (`pipeline/verify.py`); everything else carries a demo badge.
- **LLM output checks:** Pydantic validation, no `%`, allowed fields and ids only, template fallback on any failure, 8 s timeout.
- **Manual:** the jury scenario above in the browser on mobile width and desktop, in light and dark themes.

## Limitations

- GPA conversion from the 5-point scale to the 4.0 scale is **approximate**, and the UI says so. 100-point and IB MYP grades are not converted at all.
- Acceptance rates are **overall**, not specific to international applicants.
- Anonymous sessions are **per browser**. Clearing site data or switching devices starts a new profile.
- The "requirement unreachable" filter covers the IELTS minimum only. Other requirements (A-levels, Studienkolleg, interviews, HSK) are shown as information.
- Essays: most are PhD statements of purpose, all texts are in English, and majors are mapped by keywords, so some essays have none.

## Deployed URLs

- Frontend: https://locus-apex.vercel.app
- Backend: https://locus-apex.onrender.com (`/health`, `/docs`)
