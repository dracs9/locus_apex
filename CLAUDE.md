# SPEC — AI Admission Route Service (LOCUS Hackathon 2026, Case 02)

# NAME OF THE APP: Applyra

## 0. How to work (instructions for Claude Code)

- Build in the milestone order in §11. After each milestone both apps must build, pass tests and deploy.
- Prefer simple, readable code over abstractions. TypeScript strict mode on the frontend, type hints + Pydantic v2 on the backend.
- The **scoring engine is deterministic pure Python** in the backend. The LLM never decides tiers, chances, deadlines or numbers.
- Never invent university facts. Unknown value = `null` and the UI says "not published".
- Never commit secrets. Use `.env` files (git-ignored) and provide `.env.example` for both apps.
- Every third-party UI kit / library used must be listed in `README.md` (hackathon rule).
- Commit often with meaningful messages (Git history is reviewed).
- Ask before adding new heavy dependencies or changing the stack.

---

## 1. Product

**Problem.** High-school students don't need another list of universities. They need a route: where to apply, why it fits, and what to do next.

**Audience.** High-school students (grades 10–12) in Kazakhstan aiming at top universities in developed countries (US, UK, Europe, Asia).

**Core promise.** Short profile → explained recommendations (Dream / Target / Safety) → comparison → personal roadmap → one clear next step. The route visibly updates whenever the profile or achievements change.

**Out of scope.** Courses, lessons, teacher dashboards, a plain AI chat as the main UI, email/password auth, copying LOCUS design.

**Judging (weights).** User journey 30%, UX/UI 25%, personalization 20%, stability 15%, tech 10%. The jury will change budget / major / country / exam and check that results change and are explained.

---

## 2. Tech stack

| Layer | Choice |
| --- | --- |
| Frontend | React 18 + Vite + TypeScript (strict), React Router |
| Styling / UI | Tailwind CSS + shadcn/ui, lucide-react icons, Framer Motion |
| Server state | TanStack Query (with localStorage persister for offline cache of last results) |
| Client state | Zustand (UI state, onboarding draft) |
| Forms / validation | React Hook Form + Zod |
| Charts | Recharts |
| API types | `openapi-typescript` generated from FastAPI's `/openapi.json` |
| Backend | FastAPI (Python 3.11+), Pydantic v2, Uvicorn |
| Database | Supabase Postgres (+ pgvector for RAG in M5) |
| Auth | Supabase **anonymous sign-in** (no login screen); backend verifies the Supabase JWT |
| DB access | `supabase-py` or SQLAlchemy/asyncpg with the Postgres connection string (pick one, stay consistent) |
| LLM | Gemini API, called only from the backend |
| Data pipeline | Python in `/pipeline` (Crawl4AI or trafilatura + Playwright) |
| Tests | pytest (engine + API), Vitest (frontend utils), Playwright e2e happy path (optional) |
| Deploy | Frontend → Vercel; Backend → Render / Railway / Fly.io; DB → Supabase |

UI language: Russian first (all strings in `frontend/src/i18n/ru.ts` so KZ/EN can be added later).

---

## 3. Architecture

```
React (Vite)  ──HTTPS + Supabase JWT──▶  FastAPI
   │  supabase-js (anon session only)        ├── engine/   (pure, deterministic)
   │                                          ├── services/ (profile, roadmap, snapshots, ai)
   └── TanStack Query cache (localStorage)    ├── llm/      (prompts, fallbacks, cache)
                                              └── db ─────▶ Supabase Postgres (+ pgvector)
pipeline/ (offline) ──▶ Supabase (universities, doc_chunks)
```

Rules:
- The frontend talks to Supabase **only** for anonymous auth. All data goes through FastAPI.
- The backend verifies the JWT (Supabase JWKS or JWT secret) and uses `sub` as `user_id`.
- Recomputation happens on the backend after every profile/achievement change; the response contains the new result **and** the diff.
- "What-if" previews (compare sliders, trying a different budget) use a stateless endpoint that doesn't save anything.
- If the backend is unreachable, the frontend shows the last cached result with an "offline" banner and disables edits.

---

## 4. Repository structure

```
frontend/
  src/
    main.tsx  App.tsx  router.tsx
    pages/
      Landing.tsx  Onboarding.tsx  Passport.tsx  Recommendations.tsx
      University.tsx  Compare.tsx  Roadmap.tsx  Today.tsx  History.tsx
      Changes.tsx  Settings.tsx
    components/
      ui/                     # shadcn
      ds/                     # Card, ReasonChip, TierBadge, ChanceBadge, SourceBadge,
                              # DemoBadge, Stepper, EmptyState, ErrorState, OfflineBanner, Skeletons
      achievements/AddAchievementSheet.tsx
      layout/                 # BottomTabBar, Sidebar, AppShell
    api/
      client.ts               # fetch wrapper, attaches JWT, error normalization
      schema.d.ts             # generated from OpenAPI
      hooks.ts                # TanStack Query hooks
    lib/
      supabase.ts             # anon sign-in
      format.ts
    store/                    # zustand
    i18n/ru.ts
    styles/tokens.css
  .env.example                # VITE_API_URL, VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY

backend/
  app/
    main.py                   # FastAPI app, CORS, routers, /health
    config.py                 # pydantic-settings
    deps.py                   # auth (JWT verify), db session
    schemas/                  # Pydantic models (§5)
    routers/
      catalog.py  profile.py  achievements.py  recommendations.py
      roadmap.py  history.py  ai.py  demo.py
    engine/
      normalize.py  filters.py  fit.py  score.py  tier.py
      recommend.py  diff.py  roadmap.py  history.py  config.py
    services/
      profiles.py  snapshots.py  roadmap_state.py  ics.py
    llm/
      client.py  prompts.py  fallbacks.py  cache.py
    data/
      exams.json  demo_profile.json
  tests/
    engine/  api/
  pyproject.toml
  .env.example                # DATABASE_URL, SUPABASE_URL, SUPABASE_JWT_SECRET, LLM_API_KEY, CORS_ORIGINS

supabase/
  migrations/                 # SQL (§6)
  seed/universities.json  seed/majors.json
  seed.py                     # validates with Pydantic, upserts into DB

pipeline/
  crawl.py  extract.py  verify.py  embed.py  README.md

README.md  SPEC.md
```

---

## 5. Data model (`backend/app/schemas`)

Pydantic is the source of truth; frontend types are generated from OpenAPI.

```python
class Sourced(BaseModel, Generic[T]):
    value: T | None
    source_url: str | None = None
    checked_at: date | None = None
    evidence: str | None = None      # verbatim quote from source
    is_demo: bool                    # True = not verified, UI shows "Demo data"

class SatRange(BaseModel):
    p25: int; p50: int | None = None; p75: int

class Deadline(BaseModel):
    type: Literal['ED', 'EA', 'REA', 'RD', 'UCAS', 'OTHER']
    date: date

class University(BaseModel):
    id: str
    name: str
    country: str                     # 'US' | 'UK' | 'DE' | 'NL' | 'KR' | 'JP' | 'SG' | 'CA' | ...
    city: str
    website: str
    majors: list[str]                # ids from majors table
    acceptance_rate: Sourced[float]  # 0..1, overall (not intl-specific)
    sat: Sourced[SatRange]
    gpa_avg: Sourced[float]          # 4.0 scale
    ielts_min: Sourced[float]
    cost_per_year_usd: Sourced[int]  # tuition + living
    intl_aid: Sourced[Literal['full_need', 'partial', 'merit_only', 'none']]
    deadlines: list[Sourced[Deadline]]
    extra_requirements: list[str]    # e.g. "A-levels or foundation", "interview"
    documents: list[str]
    world_rank: int                  # cite the ranking source + year in README

AchievementType = Literal['SAT', 'IELTS', 'TOEFL', 'OLYMPIAD', 'PROJECT',
                          'VOLUNTEER', 'COMPETITION', 'OTHER']

class Achievement(BaseModel):
    id: UUID
    type: AchievementType
    score: float | None = None
    title: str | None = None
    level: Literal['school', 'city', 'national', 'international'] | None = None
    date: date
    status: Literal['done', 'planned']

class Priorities(BaseModel):
    cost: float; prestige: float; location: float; aid: float   # 0..1

class Profile(BaseModel):
    grade: Literal[10, 11, 12]
    gpa5: float = Field(ge=2.0, le=5.0)   # Kazakh 5-point scale
    majors: list[str] = Field(min_length=1, max_length=3)
    countries: list[str] = Field(min_length=1)
    budget_per_year_usd: int = Field(ge=0)
    needs_aid: bool
    intake_year: int
    priorities: Priorities
    achievements: list[Achievement] = []
    created_at: datetime

class Reason(BaseModel):
    kind: Literal['plus', 'risk', 'blocker']
    code: str                        # e.g. 'SAT_BELOW_P25'
    text: str                        # human Russian text
    profile_field: str               # 'budget_per_year_usd' | 'achievement:SAT' | ...
    gap: float | None = None

Tier = Literal['dream', 'target', 'safety']
Chance = Literal['low', 'medium', 'high']

class Recommendation(BaseModel):
    university_id: str; tier: Tier; chance: Chance; score: float; reasons: list[Reason]

class Excluded(BaseModel):
    university_id: str; reasons: list[Reason]      # blockers only

class RecommendationResult(BaseModel):
    recs: list[Recommendation]; excluded: list[Excluded]
    suggestions: list[str]           # "what to change" when < 3 recs
    computed_at: datetime

class RoadmapStep(BaseModel):
    id: str                          # deterministic id, e.g. 'exam:IELTS' / 'apply:mit:RD'
    kind: Literal['exam', 'document', 'academic', 'activity', 'application']
    title: str
    due_date: date
    depends_on: list[str]
    university_ids: list[str]
    source_url: str | None = None
    is_demo: bool
    done: bool
    priority: int

class Conflict(BaseModel):
    step_id: str; message: str

class Roadmap(BaseModel):
    steps: list[RoadmapStep]; conflicts: list[Conflict]; next_step_id: str | None
    progress: float                  # 0..1

class Diff(BaseModel):
    added: list[str]; removed: list[str]
    tier_changed: list[dict]         # {id, from, to}
    chance_changed: list[dict]
    gaps_closed: list[dict]          # {id, code}
    roadmap_added: list[str]; roadmap_removed: list[str]
    cause: str                       # which profile field changed, human text

class Snapshot(BaseModel):
    id: UUID; at: datetime; result: RecommendationResult
    roadmap_step_ids: list[str]; profile_hash: str; cause: str

class ComputeResponse(BaseModel):
    result: RecommendationResult; roadmap: Roadmap; diff: Diff | None
```

---

## 6. Database (`supabase/migrations`)

| Table | Columns (main) | Notes |
| --- | --- | --- |
| `universities` | `id text pk`, `name`, `country`, `city`, `website`, `world_rank int`, `data jsonb` | `data` holds all `Sourced` fields; validated by Pydantic in `seed.py` |
| `majors` | `id text pk`, `name_ru`, `name_en`, `cip_codes text[]` | |
| `profiles` | `user_id uuid pk → auth.users`, `data jsonb`, `updated_at` | one row per user |
| `achievements` | `id uuid pk`, `user_id`, `type`, `score`, `title`, `level`, `date`, `status`, `created_at` | |
| `favorites` | `user_id`, `university_id`, pk both | |
| `roadmap_progress` | `user_id`, `step_id`, `done bool`, `done_at`, pk both | steps are recomputed, only progress is stored |
| `snapshots` | `id uuid pk`, `user_id`, `at`, `result jsonb`, `roadmap_step_ids text[]`, `profile_hash`, `cause` | keep last 50 per user |
| `llm_cache` | `key text pk` (hash of input), `value jsonb`, `created_at` | |
| `doc_chunks` (M5) | `id`, `university_id`, `source_url`, `checked_at`, `content`, `embedding vector(…)` | index on `university_id`; ivfflat/hnsw on embedding |

- Enable RLS on all user tables (`user_id = auth.uid()`), even though the backend is the only client.
- The backend uses the service connection string; it must always filter by the authenticated `user_id`.
- `universities` / `majors` are read-only for clients.

---

## 7. API (FastAPI)

All `/me/*` routes require `Authorization: Bearer <supabase jwt>`. Errors return `{ "error": { "code", "message" } }`.

| Method & path | Purpose |
| --- | --- |
| `GET /health` | liveness (also used to warm up the server before the demo) |
| `GET /catalog/universities` · `GET /catalog/universities/{id}` · `GET /catalog/majors` | catalog |
| `GET /me/profile` · `PUT /me/profile` | read / replace profile → **returns `ComputeResponse`** |
| `POST /me/achievements` · `PATCH /me/achievements/{id}` · `DELETE /me/achievements/{id}` | CRUD → **returns `ComputeResponse`** |
| `GET /me/recommendations` | latest result (from last snapshot) |
| `POST /preview` | stateless: `{ profile, priorities_override? }` → `RecommendationResult`; used by Compare sliders and what-if; never saves |
| `GET /me/changes/latest` | last diff with cause |
| `GET /me/roadmap` · `PATCH /me/roadmap/steps/{step_id}` | roadmap, mark done/undone |
| `GET /me/roadmap.ics` | calendar export |
| `PUT /me/favorites/{university_id}` · `DELETE …` | favorites (affect roadmap) |
| `GET /me/chance-history?ids=a,b,c` | chance history (§8.8) |
| `POST /me/demo` · `POST /me/reset` | load demo profile / wipe user data |
| `POST /ai/passport` · `POST /ai/explain` · `POST /ai/roadmap-text` | LLM texts with fallback (§9) |
| `POST /ai/ask` (M5) | RAG question about one university |

Change flow (profile or achievement):
1. load previous snapshot → 2. save change → 3. `recommend()` + `build_roadmap()` → 4. `diff(prev, new)` → 5. save new snapshot → 6. return `ComputeResponse`.
The frontend shows a toast "Route updated: +2, ↑1" linking to `/changes`.

CORS: only the frontend origins from `CORS_ORIGINS`.

---

## 8. Scoring engine (`backend/app/engine`)

All thresholds and weights live in `engine/config.py`. Every function is pure (no DB, no clock — pass `today` explicitly) and covered by pytest.

### 8.1 Normalization
- `gpa5_to_gpa4(gpa5)`: linear table `5.0→4.0, 4.5→3.5, 4.0→3.0, 3.5→2.5, 3.0→2.0`, interpolate between. UI must say "approximate conversion".
- Best exam score = highest `done` achievement of that type. `planned` achievements never affect scoring.
- `profile_at(profile, date)`: profile with only achievements dated `<= date` (used for history).

### 8.2 Hard filters → `excluded`
A university is excluded (with a `blocker` reason) if:
1. none of `profile.majors` is in `university.majors` → `MAJOR_NOT_OFFERED`
2. `university.country` not in `profile.countries` → `COUNTRY_NOT_SELECTED` (just filter, don't list in "why not")
3. `cost > budget` AND (`not needs_aid` OR `intl_aid in {none, merit_only}`) → `OVER_BUDGET`
4. an `extra_requirement` can't be met before the earliest deadline → `REQUIREMENT_UNREACHABLE`

Unknown cost (`None`) is never a blocker; add a `risk` reason `COST_UNKNOWN`.

### 8.3 Fit factors
```
sat_fit:   sat >= p75 → 'above' | sat >= p25 → 'within' | else 'below' (gap = p25 - sat)
gpa_fit:   gpa4 >= avg → 'above' | gpa4 >= avg - 0.2 → 'within' | else 'below'
ielts_fit: ielts >= min → 'ok' | no IELTS yet → 'missing' (risk)
           | below → 'below' (blocker, unless a planned IELTS exists before deadline → risk)
```
Missing university data → factor skipped, reason `DATA_NOT_PUBLISHED` (kind `risk`, neutral wording).

### 8.4 Score
`score = Σ weight_i * factor_i` over: academic fit (SAT, GPA), language, major match, affordability, priorities match (`prestige` uses `world_rank`), achievements bonus (by `level`). Weights in `config.py`, documented in README. Sort by tier, then score desc, then `id` (stable).

### 8.5 Tier + chance
| Rule (first match wins) | Tier | Chance |
| --- | --- | --- |
| acceptance_rate < 0.15 | dream | low (medium only if all fits are `above`) |
| any fit is `below` but gap is closable before deadline | dream | low |
| all fits `above`/`within` and acceptance_rate >= 0.30 | safety | high |
| otherwise | target | medium |

Never output percentages. If fewer than 3 recs, fill `suggestions` from `excluded` reasons (e.g. "raise budget to $X", "add country Y").

### 8.6 Diff
`diff(prev: Snapshot | None, new: Snapshot) -> Diff | None` — returns `None` on first compute. `cause` is built from the fields that changed between the two profile versions.

### 8.7 Roadmap
`build_roadmap(profile, favorite_ids, recs, progress, today)`:
- Steps from gaps and requirements of favorites (fallback: top 3 recs): take/retake SAT/IELTS, documents, essays, recommendation letters, activities, application submission per deadline.
- Due dates computed backwards from the earliest relevant deadline using `data/exams.json` (e.g. IELTS result delay ≈ 13 days, SAT scores ≈ 2 weeks — `is_demo` if unverified).
- Step ids are deterministic so stored progress survives recomputation.
- `detect_conflicts(steps, today)`: a step that can't finish before its dependant's due date → `Conflict`.
- `next_step(steps)`: earliest not-done step with all dependencies done, highest priority.
- Frontend: completing an exam step opens `AddAchievementSheet` prefilled with that exam.

### 8.8 Chance history
`chance_history(profile, university_ids, universities)`: for each distinct achievement date (plus `created_at`) run the engine on `profile_at(date)`; return `[{date, chance_by_uni, achievement_id}]`. Rendered as a step chart with achievement markers.

### 8.9 Required tests (pytest)
- same input → identical output (determinism)
- raising SAT above p25 moves a university from dream → target
- lowering budget removes a no-aid university and adds `OVER_BUDGET`
- changing major changes the recommendation set
- acceptance_rate < 0.15 is never `safety`
- `planned` achievements don't affect scoring
- missing data never produces a blocker
- diff reports added / removed / tier_changed correctly
- conflict detected when an exam result arrives after the deadline
- API: `PUT /me/profile` returns a diff; user A can't read user B's data; `/preview` saves nothing

---

## 9. AI layer (`backend/app/llm`)

| Route | Input | Output (Pydantic-validated JSON) | Fallback |
| --- | --- | --- | --- |
| `POST /ai/passport` | current profile | `{ goal, strengths[3], constraints[2], risk }` | template from fields |
| `POST /ai/explain` | university_id (+ current rec) | `{ summary }` (≤ 2 sentences, only from given reasons) | join `reason.text` |
| `POST /ai/roadmap-text` | step ids | `[{ id, description }]` | static descriptions |
| `POST /ai/ask` (M5) | university_id + question | `{ answer, sources[] }` | "Not stated on the university site" + link |

Rules:
- Prompts forbid adding facts not present in the input; invalid JSON → fallback.
- 8 s timeout; cache in `llm_cache` by hash of input.
- Responses include `{ "generated": true | false }` so the UI can mark template text.
- Tier, chance, numbers, deadlines always come from the engine, never from the LLM.
- RAG retrieval is always filtered by `university_id`; answers cite `source_url` + `checked_at`.

---

## 10. Frontend: screens & UX

Main path with a stepper: Landing → Onboarding → Passport → Recommendations → Compare → Roadmap → Today.
After onboarding: bottom tab bar on mobile (Today, Universities, Plan, Profile), sidebar on desktop.

| Screen | Content | Primary action |
| --- | --- | --- |
| Landing | Value in one sentence, preview of result | "Build my route", "Try demo profile" |
| Onboarding | One question per screen, progress bar, back, "I don't know"; draft kept in Zustand until submit | Next |
| Passport | Goal, 3 strengths, 2 constraints, main risk; tap item → shows source answer | "Show options" |
| Recommendations | 3 tier sections, cards with reason chips, "Why not recommended" collapsible, suggestions if < 3 | ★ favorite, Compare |
| University | Requirements vs your data table, cost, aid, deadlines, SourceBadge on every fact | Add to plan, Ask (M5) |
| Compare | 2–3 columns, priority sliders re-rank live via `/preview` (debounced 300 ms) | Pick favorite |
| Roadmap | Timeline by month, conflicts highlighted, sources on deadlines | Mark done, export .ics |
| Today | One big next-step card, progress ring, chance history chart | Done, "+ Achievement" |
| History | Achievements timeline, filter by type | Add / edit / delete |
| Changes | Diff with causes, animated card moves (Framer Motion `layout`) | "Back to route" |
| Settings | Reset profile, load demo profile | — |

**Add achievement in 2 taps:** floating "+" → bottom sheet with type presets → score + date → Save.

**Design system:** CSS variables in `tokens.css` (tier colors: dream / target / safety; reason kinds: plus / risk / blocker), typography scale, radius, spacing. Original look — do not copy LOCUS or other platforms. Light + dark.

**States on every data screen:** loading skeleton, empty, error with retry, backend offline (cached data + banner), LLM unavailable (template text marked), no matching universities (suggestions), demo data badge.

**Mobile:** must work at 360 px wide. No horizontal page scroll.

**Auth UX:** on first load call `supabase.auth.signInAnonymously()` silently; no login screen. Session persists in the browser.

---

## 11. Data (`supabase/seed`, `pipeline/`)

- `universities.json`: 10–30 universities per selected country (start with US + UK, then others), chosen so that changing SAT / budget / major / country clearly changes results.
- Sources: US — Common Data Set (C1 admissions, C9 SAT, C11–C12 GPA, C21–C22 deadlines, H6 intl aid) and College Scorecard API; UK — university programme pages + UCAS; others — official admissions pages for international students. `world_rank`: one named ranking and year, cited in README.
- Every numeric fact is `Sourced`. Anything not verified by a human → `is_demo: true`.
- Do not scrape QS, THE, Mastersportal, Niche.

Pipeline (Python, run offline, writes to `supabase/seed/` and DB):
1. `crawl.py` — crawl 1–2 levels per university, keep pages matching admission / tuition / fees / requirements / deadline / international; respect robots.txt, 1 req/s.
2. `extract.py` — LLM extracts fields into JSON; every field must include a verbatim `evidence` quote; missing → `null`.
3. `verify.py` — drop any field whose `evidence` isn't found in the page text; write a report (pages processed, % fields verified).
4. `embed.py` (M5) — chunk 500–800 tokens with `university_id`, `source_url`, `checked_at` → `doc_chunks`.

---

## 12. README requirements (hackathon)

Task, solution, stack, architecture diagram, local run instructions for both apps (+ Supabase setup and migrations), test scenario for the jury, team roles, data sources with dates, AI models / APIs and why, list of ready-made components (shadcn/ui, Recharts, etc.), scoring weights, limitations (approximate GPA conversion, overall acceptance rates, demo data, anonymous sessions are per-browser), pipeline metrics, deployed URLs. Include both `.env.example` files.

---

## 13. Milestones

**M1 — Foundation**
- [ ] Monorepo: `frontend/` (Vite + React + TS + Tailwind + shadcn), `backend/` (FastAPI), `supabase/`
- [ ] Supabase project, migrations, RLS, anonymous sign-in enabled
- [ ] Seed: `universities.json` (≥ 15 records, demo flags), `majors.json`; `seed.py`
- [ ] Engine: normalize, filters, fit, score, tier, recommend + pytest
- [ ] `/health`, `/catalog/*`, JWT auth dependency
- [ ] Deploy frontend (Vercel) + backend (Render/Railway) and check CORS end-to-end
- [ ] Design tokens + `components/ds`

**M2 — Core journey**
- [ ] OpenAPI → TS types, API client, TanStack Query hooks
- [ ] Profile endpoints + snapshots + `ComputeResponse`
- [ ] Landing, Onboarding, Passport (template text), Recommendations with reasons + "why not"
- [ ] University page, `/preview`, Compare with sliders
- [ ] Demo / reset endpoints and Settings screen

**M3 — Living route**
- [ ] Achievements CRUD + 2-tap sheet + History
- [ ] Diff + Changes screen + toast
- [ ] Roadmap (deadlines, dependencies, conflicts, progress) + Today screen
- [ ] Favorites affect roadmap
- [ ] Chance history endpoint + chart

**M4 — AI + polish**
- [ ] `/ai/passport`, `/ai/explain`, `/ai/roadmap-text` with fallbacks and cache
- [ ] All states (loading / empty / error / offline / LLM down), 360 px check, dark mode
- [ ] `.ics` export
- [ ] README complete

**M5 — Optional (only if M1–M4 are stable)**
- [ ] Pipeline run on more universities
- [ ] RAG `/ai/ask` on the university page
- [ ] Voice guide (Web Speech API → backend intent JSON → highlight / navigate / filter)

**Feature freeze:** 2026-09-18 22:00. After that only bug fixes and docs.

---

## 14. Deployment notes

- Free backend hosts sleep after inactivity (cold start 30–60 s). Before any demo or jury window: hit `/health`; consider a scheduled ping or a paid instance for 19–24 September.
- Frontend must show a friendly "waking up the server…" state if the first request is slow (> 3 s), not a blank page.
- `VITE_API_URL` points to the deployed backend; backend `CORS_ORIGINS` includes the Vercel domain.
- Service keys and `LLM_API_KEY` live only in the backend host's env settings.

---

## 15. Acceptance criteria (jury scenario)

1. From landing to a personal roadmap in under 3 minutes on a phone, no login.
2. Every recommendation shows at least 2 human-readable reasons linked to profile fields.
3. At least 3 recommendations for the demo profile, across ≥ 2 tiers.
4. Changing budget, major, country or SAT visibly changes recommendations and opens a diff explaining why.
5. Adding an achievement updates recommendations, roadmap and chance history.
6. Every deadline and requirement shows a source badge or a "Demo data" badge.
7. No percentages of admission chance anywhere.
8. App works with the LLM API disabled.
9. Reload keeps all state (same browser). Reset clears it.
10. Backend cold start or outage never shows a blank screen.
11. No console errors on the main path; no secrets in the repo.
