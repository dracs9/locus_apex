# SPEC — AI Admission Route Service (LOCUS Hackathon 2026, Case 02)

**App name:** Applyra · **Participation code:** `LOCUSCASE2` · **Status (2026-09-19):** M1–M4 done, feature freeze passed; only bug fixes and docs from now on.

This spec describes the product as built. Where the build departs from the original plan, the section says **Changed** and gives the reason. `CLAUDE.md` keeps the original working instructions; this file is the source of truth for scope. [README.md](README.md) holds run instructions, the jury scenario and the technical reference.

---

## 0. Working rules

- Build and fix in milestone order (§13). After each change both apps must build, pass tests and deploy.
- Prefer simple, readable code over abstractions. TypeScript strict mode on the frontend, type hints + Pydantic v2 on the backend.
- The **scoring engine is deterministic pure Python** in the backend. The LLM never decides tiers, chances, deadlines or numbers.
- Never invent university facts. Unknown value = `null` and the UI says "не опубликовано".
- Never commit secrets. `.env` files are git-ignored; both apps ship `.env.example`.
- Every third-party UI kit / library is listed in `README.md` (hackathon rule).
- Commit often with meaningful messages (Git history is reviewed).

---

## 1. Product

**Problem.** High-school students don't need another list of universities. They need a route: where to apply, why it fits, and what to do next.

**Audience.** High-school students in Kazakhstan, **grades 9–12** (**Changed:** grade 9 added, since planning starts early), aiming at top universities in developed countries (US, UK, Europe, Asia).

**Core promise.** Short profile → explained recommendations (Dream / Target / Safety) → comparison → personal plan → one clear next step. The route visibly updates whenever the profile or achievements change.

**Beyond the core** (added during the build, all optional for the main path):
- RIASEC interest quiz that suggests majors (§8.10).
- AI mentor chat that proposes plan changes the student confirms (§9.1).
- Essay library with explained reading recommendations (§8.11).
- Photo and link attachments on achievements.

**Out of scope.** Courses, lessons, teacher dashboards, a plain AI chat as the *main* UI, email/password auth, copying LOCUS design.

**Judging (weights).** User journey 30%, UX/UI 25%, personalization 20%, stability 15%, tech 10%. The jury will change budget / major / country / exam and check that results change and are explained.

---

## 2. Tech stack

| Layer | Choice |
| --- | --- |
| Frontend | React 18 + Vite 6 + TypeScript (strict), React Router 6 |
| Styling / UI | Tailwind CSS + shadcn/ui, lucide-react icons, Framer Motion; fonts Manrope + Playfair Display |
| Server state | TanStack Query (with localStorage persister for offline cache of last results) |
| Client state | Zustand (UI state, onboarding draft) |
| Forms / validation | React Hook Form + Zod |
| Charts | Recharts |
| API types | `openapi-typescript` generated from FastAPI's `/openapi.json` |
| Backend | FastAPI (Python 3.11+), Pydantic v2, Uvicorn |
| Database | Supabase Postgres (SQLite for local runs without Supabase) |
| DB access | **SQLAlchemy 2 async + asyncpg** (decided) |
| Auth | Supabase **anonymous sign-in** (no login screen); backend verifies the Supabase JWT (JWKS or legacy HS256 secret) |
| File storage | Supabase Storage, private bucket `achievement-files`, accessed only by the backend |
| LLM | Google Gemini via `google-genai`, model set by `LLM_MODEL` (`gemini-3.8-flash` in production), called only from the backend |
| Data pipeline | Python in `/pipeline`: httpx + trafilatura + pypdf, College Scorecard API (**Changed:** no Crawl4AI/Playwright; static pages and PDFs were enough) |
| Tests | pytest (engine, API, pipeline), Vitest (frontend logic) |
| Deploy | Frontend → Vercel; Backend → Render (`render.yaml`); DB/auth/storage → Supabase |

UI language: Russian (all strings in `frontend/src/i18n/ru.ts` so KZ/EN can be added later).

---

## 3. Architecture

```
React (Vite)  ──HTTPS + Supabase JWT──▶  FastAPI
   │  supabase-js (anon session only)        ├── engine/   pure, deterministic scoring, diff, plan suggestions
   │                                          ├── services/ profiles, snapshots, compute, plan, ics, essays, mentor, storage
   └── TanStack Query cache (localStorage)    ├── llm/      prompts, fallbacks, cache, mentor tools ──▶ Gemini
                                              └── db ─────▶ Supabase Postgres + Storage
pipeline/ (offline) ──▶ supabase/seed/*.json ──▶ seed.py ──▶ Supabase (universities, majors, essays)
```

Rules:
- The frontend talks to Supabase **only** for anonymous auth. All data, including photos, goes through FastAPI.
- The backend verifies the JWT and uses `sub` as `user_id`; every user query filters by it.
- Recomputation happens on the backend after every profile / achievement / favorite change; the response contains the new result **and** the diff.
- "What-if" previews (Compare sliders, viewing a country outside the profile) use the stateless `/preview`, which never saves anything.
- If the backend is unreachable, the frontend shows the last cached result with an "offline" banner and disables edits.

---

## 4. Repository structure

```
frontend/
  src/
    main.tsx  App.tsx  router.tsx
    pages/      Landing Onboarding Passport Interests Recommendations University Compare
                Roadmap Mentor Essays Essay Today History Changes Settings
    components/
      ui/            shadcn
      ds/            Card, badges (Tier/Chance/Source/Demo/Reason), Stepper, UniversityCard,
                     StepRow, ChanceChart, states (Empty/Error/Offline/Skeletons)
      achievements/  AddAchievementSheet, AttachmentsEditor, AttachmentStrip
      passport/      GoalHero, StatTiles, WeekFocus, AdviceCard, PassportUniCard
      profile/       ProfileEditorSheet, AcademicField
      interests/     HollandQuiz
      essays/  roadmap/  brand/  layout/AppShell (bottom tabs + sidebar)
    api/        client.ts  schema.d.ts (generated)  hooks.ts
    lib/        supabase, format, academic, interests, profileIn, profileCompleteness, suggestions, essays, image
    data/holland.json   (copy of the backend file; a test checks they match)
    store/  i18n/ru.ts  styles/tokens.css
  .env.example          VITE_API_URL, VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY

backend/
  app/
    main.py  config.py  deps.py
    schemas/   profile, university, recommendation, roadmap, ai, mentor, essay
    routers/   catalog profile achievements recommendations roadmap history ai mentor essays demo
    engine/    normalize filters fit score tier recommend diff roadmap history interests text config
    services/  profiles snapshots compute plan roadmap_items ics essays mentor mentor_store attachments storage catalog
    llm/       client prompts fallbacks cache mentor_model
    data/      exams.json activities.json holland.json demo_profile.json
  tests/       engine/  api/
  scripts/dump_openapi.py
  .env.example          DATABASE_URL, SUPABASE_URL, SUPABASE_JWT_SECRET, SUPABASE_SERVICE_KEY, LLM_API_KEY, LLM_MODEL, CORS_ORIGINS

supabase/
  migrations/  0001_init  0002_achievement_attachments  0003_roadmap_items  0004_mentor_messages  0005_essays
  seed/        universities.json  majors.json  essays.json  build_seed.py
  migrate.py  seed.py

pipeline/      scorecard.py  cds.py  crawl.py  extract.py  verify.py  essays.py  embed.py (stub)  tests/  README.md
docs/          TEAM_GUIDE.md (Russian team notes)
README.md  SPEC.md  CLAUDE.md  render.yaml  run-back.sh  run-front.sh
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
    is_demo: bool = True             # True = not verified, UI shows "Демо-данные"

class SatRange(BaseModel):  p25: int; p50: int | None = None; p75: int
class Deadline(BaseModel):  type: Literal['ED', 'EA', 'REA', 'RD', 'UCAS', 'OTHER']; date: date

class University(BaseModel):
    id: str; name: str; country: str; city: str; website: str
    majors: list[str]
    acceptance_rate: Sourced[float]  # 0..1, overall (not intl-specific)
    sat: Sourced[SatRange]
    gpa_avg: Sourced[float]          # 4.0 scale
    ielts_min: Sourced[float]
    cost_per_year_usd: Sourced[int]  # tuition + living
    intl_aid: Sourced[Literal['full_need', 'partial', 'merit_only', 'none']]
    deadlines: list[Sourced[Deadline]]
    extra_requirements: list[str]; documents: list[str]
    world_rank: int                  # QS World University Rankings 2025, approximate

class Major(BaseModel): id: str; name_ru: str; name_en: str; cip_codes: list[str]

AchievementType = Literal['SAT', 'IELTS', 'TOEFL', 'OLYMPIAD', 'PROJECT', 'VOLUNTEER', 'COMPETITION', 'OTHER']

class Attachment(BaseModel):         # added: evidence only, never affects scoring
    id: UUID; kind: Literal['photo', 'link']; url: str | None   # link, or 1-hour signed URL for photos
    title: str | None; content_type: str | None; created_at: datetime

class Achievement(BaseModel):
    id: UUID; type: AchievementType; score: float | None; title: str | None
    level: Literal['school', 'city', 'national', 'international'] | None
    date: date; status: Literal['done', 'planned']
    attachments: list[Attachment] = []          # max 5

class Priorities(BaseModel): cost: float; prestige: float; location: float; aid: float   # 0..1

class AcademicRecord(BaseModel):     # added: the grade as the student knows it
    scale: Literal['5', '4', '100', 'ib8']; value: float       # value <= scale maximum

class HollandAssessment(BaseModel):  # added: RIASEC answers
    version: Literal['applyra-riasec-v1']; answers: dict[str, int]   # all 30 questions, 0..4

class Profile(BaseModel):
    grade: Literal[9, 10, 11, 12]                  # Changed: 9 added
    gpa5: float | None                             # Changed: optional; legacy field, still read
    academic_record: AcademicRecord | None
    holland: HollandAssessment | None
    majors: list[str] = Field(min_length=1, max_length=3)
    countries: list[str] = Field(min_length=1)
    budget_per_year_usd: int = Field(ge=0)         # family's yearly contribution; 0 = full aid needed
    needs_aid: bool                                # kept for old clients; onboarding sends True
    intake_year: int
    priorities: Priorities
    achievements: list[Achievement] = []
    created_at: datetime

class Reason(BaseModel):
    kind: Literal['plus', 'risk', 'blocker']; code: str; text: str
    profile_field: str; gap: float | None = None

class Recommendation(BaseModel):  university_id: str; tier: Tier; chance: Chance; score: float; priority_match: float; reasons: list[Reason]
class Excluded(BaseModel):        university_id: str; reasons: list[Reason]      # blockers only
class RecommendationResult(BaseModel):
    recs: list[Recommendation]; excluded: list[Excluded]; suggestions: list[str]; computed_at: datetime

# Plan — Changed 2026-09-18: suggestions + student-owned steps (see §8.7)
class Suggestion(BaseModel):
    id: str                          # deterministic: 'exam:SAT', 'doc:essay', 'apply:mit:RD', 'act:olympiad'
    kind: Literal['exam', 'document', 'academic', 'activity', 'application']
    title: str; why: SuggestionWhy   # {text, profile_field}
    description: str; suggested_due: date; university_ids: list[str]
    source_url: str | None; is_demo: bool; priority: int

class RoadmapStep(BaseModel):
    id: str; kind: StepKind; title: str; due_date: date
    depends_on: list[str]; university_ids: list[str]
    source_url: str | None; is_demo: bool; done: bool; priority: int
    source_key: str | None           # suggestion it came from; None for a custom step
    note: str | None

class Conflict(BaseModel):  step_id: str; message: str
class Roadmap(BaseModel):   steps: list[RoadmapStep]; conflicts: list[Conflict]; next_step_id: str | None; progress: float

class Diff(BaseModel):
    added: list[str]; removed: list[str]
    tier_changed: list[TierChange]; chance_changed: list[ChanceChange]   # {id, from, to}
    gaps_closed: list[GapClosed]     # {id, code}
    roadmap_added: list[str]; roadmap_removed: list[str]                 # suggestion ids
    cause: str

class Snapshot(BaseModel): id: UUID; at: datetime; result: RecommendationResult
                           roadmap_step_ids: list[str]; profile_hash: str; cause: str
class ComputeResponse(BaseModel): result: RecommendationResult; roadmap: Roadmap; diff: Diff | None
class ChancePoint(BaseModel): date: date; chance_by_uni: dict[str, Chance | None]; achievement_id: str | None

# Mentor (added)
class MentorAction(BaseModel):
    type: Literal['add_suggestion', 'add_step', 'update_step', 'delete_step']
    summary: str; args: dict; status: Literal['pending', 'applied', 'dismissed', 'failed']
class MentorMessage(BaseModel):
    id: UUID; role: Literal['user', 'assistant']; text: str
    actions: list[MentorAction]; generated: bool; created_at: datetime

# Essays (added)
class EssaySummary(BaseModel):
    id: str; school: str | None; university_id: str | None; level; kind; prompt: str | None
    program: str | None; majors: list[str]; topics: list[str]; author: str | None
    license: Literal['CC_BY_NC_SA_4_0', 'UNKNOWN']; source_url: str; original_url: str | None
    word_count: int; excerpt: str
class Essay(EssaySummary): body: str; references: list[str]
class RecommendedEssay(BaseModel): essay: EssaySummary; reasons: list[str]
```

---

## 6. Database (`supabase/migrations`)

| Table | Migration | Notes |
| --- | --- | --- |
| `universities` | 0001 | `id`, `name`, `country`, `city`, `website`, `world_rank`, `data jsonb` (all `Sourced` fields, validated by `seed.py`); public read |
| `majors` | 0001 | `id`, `name_ru`, `name_en`, `cip_codes`; public read |
| `profiles` | 0001 | one row per user, `data jsonb` |
| `achievements` | 0001 | one row per achievement |
| `favorites` | 0001 | pk (`user_id`, `university_id`) |
| `roadmap_progress` | 0001 | legacy progress of generated steps; superseded by `roadmap_items` |
| `snapshots` | 0001 | last 50 per user |
| `llm_cache` | 0001 | `key` = hash of input |
| `achievement_attachments` | 0002 | photo / link rows; creates the private `achievement-files` Storage bucket |
| `roadmap_items` | 0003 | the student's plan steps (from a suggestion via `source_key`, or custom) |
| `mentor_messages` | 0004 | chat history with actions; last 100 per user |
| `essays` | 0005 | essay collection; public read |

- RLS on all user tables (`user_id = auth.uid()`), although the backend is the only client.
- The backend uses the service connection string and always filters by the authenticated `user_id`.
- `universities`, `majors`, `essays` are read-only for clients.
- **Changed:** `doc_chunks` / pgvector (M5 RAG) not created; the mentor uses structured catalog tools instead (§9.1).

---

## 7. API (FastAPI)

All `/me/*` and `/ai/*` routes require `Authorization: Bearer <supabase jwt>`. Errors return `{ "error": { "code", "message" } }`. OpenAPI at `/docs`.

| Method & path | Purpose |
| --- | --- |
| `GET /health` | liveness; also warms up the server before a demo |
| `GET /catalog/universities` · `GET /catalog/universities/{id}` · `GET /catalog/majors` | catalog |
| `GET /me/profile` · `PUT /me/profile` | read / replace profile → `ComputeResponse` |
| `POST /me/achievements` · `PATCH /me/achievements/{id}` · `DELETE /me/achievements/{id}` | CRUD → `ComputeResponse` (POST also returns `achievement_id`) |
| `POST /me/achievements/{id}/attachments/photo` · `…/link` · `DELETE …/attachments/{attachment_id}` | attachments; no recomputation |
| `GET /me/recommendations` | latest result |
| `POST /preview` | stateless `{ profile, priorities_override? }` → `RecommendationResult`; never saves |
| `GET /me/changes/latest` | last diff with cause |
| `GET /me/roadmap` · `GET /me/roadmap/suggestions` | the plan · explained suggestions |
| `POST /me/roadmap/items` · `PATCH`/`DELETE /me/roadmap/items/{id}` | add (`{suggestion_id}` or `{title, kind, due_date, note}`), edit, mark done, delete |
| `GET /me/roadmap.ics` | calendar export |
| `GET /me/favorites` · `PUT`/`DELETE /me/favorites/{university_id}` | favorites (affect suggestions) → `ComputeResponse` |
| `GET /me/chance-history?ids=a,b,c` | chance history (§8.8) |
| `POST /me/demo` · `POST /me/reset` | load demo profile / wipe user data, files and chat |
| `POST /ai/passport` · `POST /ai/explain` · `POST /ai/roadmap-text` | LLM texts with fallback (§9) |
| `GET /ai/mentor` · `POST /ai/mentor` · `POST /ai/mentor/{message_id}/actions/{index}` · `DELETE /ai/mentor` | mentor chat, apply/dismiss a proposal, clear (§9.1) |
| `GET /essays` · `GET /essays/{id}` · `GET /me/essays/recommended` | essays (§8.11) |

Change flow (profile, achievement or favorite):
1. load previous snapshot → 2. save change → 3. `recommend()` + `suggest_actions()` + `build_roadmap()` → 4. `diff(prev, new)` → 5. save new snapshot → 6. return `ComputeResponse`.
The frontend shows a toast "Маршрут обновлён: +2, ↕1" linking to `/changes`.

CORS: only the frontend origins from `CORS_ORIGINS`.

---

## 8. Engine (`backend/app/engine`)

All thresholds and weights live in `engine/config.py` and are documented in the README. Every function is pure (no DB, no clock — `today` is passed in) and covered by pytest.

### 8.1 Normalization
- `gpa5_to_gpa4`: linear table `5.0→4.0, 4.5→3.5, 4.0→3.0, 3.5→2.5, 3.0→2.0`, interpolated. UI says "approximate conversion".
- `profile_gpa4`: `academic_record` scale `4` is used as is, scale `5` is converted, scales `100` and `ib8` are **not converted** (no official conversion) → GPA treated as missing with a `DATA_NOT_PUBLISHED`-style risk. Falls back to legacy `gpa5`.
- TOEFL → IELTS by the ETS comparison table. Best exam score = highest `done` achievement. `planned` achievements never affect scoring.
- `profile_at(profile, date)`: only achievements dated `<= date` (history).
- `project_deadline`: seed deadlines are shifted to the student's intake year (Aug–Dec deadlines belong to next year's intake).

### 8.2 Hard filters → `excluded`
1. none of `profile.majors` in `university.majors` → `MAJOR_NOT_OFFERED`
2. `country` not in `profile.countries` → filtered silently
3. `cost > budget` and no need-based aid (`intl_aid in {none, merit_only}`) → `OVER_BUDGET`
4. IELTS below minimum with no planned retake before the deadline → `REQUIREMENT_UNREACHABLE` (**only IELTS is checked**; other requirements are shown as information)

Unknown cost is never a blocker (`COST_UNKNOWN` risk); unknown aid → `AID_UNKNOWN` risk.

### 8.3 Fit factors
```
sat_fit:   sat >= p75 → above | sat >= p25 → within | else below (gap = p25 - sat)
gpa_fit:   gpa4 >= avg → above | gpa4 >= avg - 0.2 → within | else below
ielts_fit: ielts >= min → ok | none yet → missing (risk) | below → blocker unless a planned retake → risk
```
Missing university data → factor skipped, reason `DATA_NOT_PUBLISHED` (risk, neutral wording).

### 8.4 Score
Weighted sum (0..100, ordering only): academic 0.35, language 0.15, affordability 0.20, priorities 0.15 (cost, prestige by `world_rank`, aid, first country), major match 0.10 (refined by RIASEC fit), achievements 0.05 (by level, capped). Sort by tier, then score desc, then `id`. Each rec also carries `priority_match` (0..100, the priorities factor alone: cost 1 − cost/$100k, prestige 1 − ln(rank)/ln(600)); Compare sorts by it so the sliders re-rank the columns.

### 8.5 Tier + chance
| Rule (first match wins) | Tier | Chance |
| --- | --- | --- |
| acceptance_rate < 0.15 | dream | low (medium only if all fits are `above`) |
| any fit `below` (closable: SAT gap ≤ 150, GPA gap ≤ 0.3, ≥ 60 days left) | dream | low |
| all fits `above`/`within` and acceptance_rate ≥ 0.30 | safety | high |
| otherwise | target | medium |

Unclosable gaps are also dream (never target) with a separate "hard to close" reason. Never output percentages. Fewer than 3 recs → `suggestions` from `excluded` reasons ("raise budget to $X", "add country Y").

### 8.6 Diff
`diff(prev, new) -> Diff | None` — `None` on first compute. `cause` names the changed profile fields in human text (e.g. "Бюджет $50 000 → $20 000"). `roadmap_added/removed` compare suggestion ids.

### 8.7 Plan (roadmap)
> **Changed 2026-09-18:** the plan is no longer generated. A generated plan felt imposed and could not hold the student's own steps.

- `suggest_actions(profile, favorite_ids, recs, universities, added_keys, today)` returns explained `Suggestion`s: exams (SAT/IELTS register + take when missing or below), documents per target university, "raise grades" when GPA is below average, the application per earliest open deadline, and up to 8 activities from `data/activities.json` (25 generic ideas, ranked by major match, top Holland theme, general; skipped if the student already has that type at national level or higher). Targets = favorites, else the best university of each tier.
- Dates count back from the earliest open deadline with result delays from `data/exams.json` (SAT ≈ 28 days, IELTS 13, TOEFL 3; official sources, `is_demo: false`) plus a 3-day buffer.
- Suggestion ids are deterministic; an added suggestion disappears from the list.
- The student's steps live in `roadmap_items`. `build_roadmap(steps, today)` orders them, links an application step to the exam/document steps of the same university, computes progress and `next_step_id` (earliest undone step with all dependencies done, highest priority).
- `detect_conflicts`: overdue steps; an exam whose result would arrive after the linked application date.
- Demo profile gets the first two suggestions of each kind so the plan isn't empty. Completing an exam step opens `AddAchievementSheet` prefilled with that exam.

### 8.8 Chance history
`chance_history(profile, university_ids, universities)`: for each achievement date (plus `created_at`) run the engine on `profile_at(date)`; returns `[ChancePoint]`. Rendered as a step chart with achievement markers.

### 8.9 Required tests (pytest) — all present
- same input → identical output
- raising SAT above p25 moves a university dream → target
- lowering budget removes a no-aid university with `OVER_BUDGET`
- changing major changes the recommendation set
- acceptance_rate < 0.15 is never `safety`
- `planned` achievements don't affect scoring
- missing data never produces a blocker
- diff reports added / removed / tier_changed correctly
- conflict when an exam result arrives after the deadline
- API: `PUT /me/profile` returns a diff; user A can't read user B's data; `/preview` saves nothing
- added: RIASEC scoring, attachments (type sniffing, limits, cleanup), essays, mentor proposals and guardrails, error format

Current counts: backend 70, frontend (Vitest) 25, pipeline 38.

### 8.10 Interests (RIASEC) — added
- `data/holland.json`: 30 original questions (not Truity's), six themes, answers 0..4, each theme 0..20. The frontend copy must equal the backend file (tested).
- The result suggests majors; the student confirms or changes them. The engine uses interests only inside the major-match factor, only among the student's chosen majors. With a fully flat profile no themes are auto-selected.
- Not psychometrically validated; the UI says it describes interests, not abilities or chances.

### 8.11 Essay recommendations — added
Deterministic, explained: bachelor's +3, university in the plan +3 (or in recommendations +2), shared major +2, Common App / personal statement +1; ties by id; each card lists its reasons.

---

## 9. AI layer (`backend/app/llm`)

| Route | Input | Output (Pydantic-validated JSON) | Fallback |
| --- | --- | --- | --- |
| `POST /ai/passport` | current profile | `{ goal, strengths[≤3], constraints[≤2], risk }`, each `{text, profile_field}` | template from fields |
| `POST /ai/explain` | `university_id` | `{ summary }` (≤ 2 sentences, only from given reasons) | joined `reason.text` |
| `POST /ai/roadmap-text` | step / suggestion ids | `[{ id, description }]` | static descriptions |

Rules:
- Prompts forbid facts, numbers and percentages not present in the input. Invalid JSON, `%`, unknown `profile_field` or mismatched ids → fallback.
- 8 s timeout; results cached in `llm_cache` by hash of input.
- Responses include `generated: true | false`; the UI marks template text "Шаблонный текст".
- Tier, chance, numbers and deadlines always come from the engine.
- The app works fully with `LLM_API_KEY` empty.

### 9.1 Mentor — added (replaces M5 RAG `/ai/ask`)
- Gemini with function calling, temperature 0.3, 25 s per call, ≤ 4 tool rounds per reply.
- Context rebuilt per message: profile, top 10 recs with engine reasons, favorites, plan with conflicts, suggestions.
- Retrieval tools: `get_university` (facts with source + demo flag, projected deadlines, the student's tier) and `find_universities` (by country, major, cost). The catalog is small and structured, so tools replace vector search.
- Plan tools only **propose** (`propose_add_suggestion`, `propose_add_step`, `propose_update_step`, `propose_delete_step`), validated with the same models as the plan API; dates between today and +2 years. The student presses "Применить"/"Отклонить"; applying runs the plan endpoint code.
- Replies pairing "шанс" with a percentage are sanitized server-side. Unknown values → "не опубликовано"; demo data is called approximate.
- Last 100 messages stored, last 12 sent to the model. Without a key the mentor answers with a template naming the next plan step.

---

## 10. Frontend: screens & UX

Main path with a stepper: Landing → Onboarding → Passport → Recommendations → Compare → Plan → Today.
After onboarding: bottom tab bar on mobile (Сегодня, Университеты, План, Профиль), sidebar on desktop with all sections and a country list.

| Screen | Content | Primary action |
| --- | --- | --- |
| Landing | Value in one sentence, preview of result | "Построить маршрут", "Попробовать демо-профиль" |
| Onboarding | One question per screen, progress bar, back, "не знаю" (incl. budget, with a tip to discuss it with parents); grade scale choice (5 / 4 / 100 / IB MYP); draft in Zustand | Next |
| Passport | Goal hero, stat tiles, 3 strengths, 2 constraints, main risk, weekly focus; tap item → source answer; profile editor sheet | "Показать варианты" |
| Interests | RIASEC quiz (5 blocks), themes, suggested majors to confirm | Save majors |
| Recommendations | Grouped by tier and country, filters by country and difficulty (`?country=US`), reason chips, "Почему не рекомендованы", suggestions if < 3 | ★ favorite, Compare |
| University | Requirements vs your data, cost, aid, deadlines, SourceBadge on every fact, related essays | Add to plan |
| Compare | Up to 10 universities, priority sliders re-rank live via `/preview` (debounced 300 ms) | Pick favorite |
| Plan | Student's steps by month, conflicts highlighted, sources on deadlines; "Рекомендации для тебя" with reasons; "Свой шаг" | Add, edit, mark done, export .ics |
| Mentor | Chat, proposal cards | Применить / Отклонить |
| Essays / Essay | Search, filters, sort, recommended with reasons; full text with author, license, source | Read |
| Today | One big next-step card, progress ring, chance history chart, essays entry | Done, "+ Достижение" |
| History (Достижения) | Achievements timeline, filter by type, attachments | Add / edit / delete |
| Changes | Diff with causes, animated card moves (Framer Motion `layout`) | "Назад к маршруту" |
| Settings | Reset profile, load demo profile | — |

**Add achievement in 2 taps:** floating "+" → bottom sheet with type presets → score + date → Save.

**Design system:** CSS variables in `tokens.css` (tier colors dream / target / safety; reason kinds plus / risk / blocker), Manrope typography, blue accent, radius, spacing. Original look, not LOCUS. Light + dark. Logo: `frontend/public/applyra-mark.svg`.

**States on every data screen:** loading skeleton, empty, error with retry, backend offline (cached data + banner), server waking up (> 3 s), LLM unavailable (template text marked), no matching universities (suggestions), demo data badge.

**Mobile:** works at 360 px wide, no horizontal page scroll.

**Auth UX:** `supabase.auth.signInAnonymously()` on first load, silently; no login screen. Session persists in the browser.

---

## 11. Data (`supabase/seed`, `pipeline/`)

- `universities.json`: **77 universities in 17 countries** (US 19, UK 10, NL/CA/AU 4 each, DE, KR, SG, HK, CN, IT, JP, CH, FR, IE, SE, ES 3 each), 10 majors. 557 facts: 73 real, 484 demo.
- US real data: College Scorecard API (acceptance rate, SAT 25/75 as sum of section percentiles, international cost) and official Common Data Sets (C12 GPA, C14/C21/C22 deadlines, H6 aid) with verbatim quotes. Other countries: hand-compiled approximate values, `is_demo: true`.
- `world_rank`: QS World University Rankings 2025, approximate, not scraped.
- Every numeric fact is `Sourced`. **Changed:** "verified" means automatic verification (Scorecard API value, or a quote found in the official document by `verify.py`), agreed for the hackathon instead of human verification.
- Never scraped: QS, THE, Mastersportal, Niche, commondatasets.com (terms forbid harvesting). Sites that block bots or need a login are skipped.
- Essays: 144 from openessays.org (2026-09-18), normalized by `pipeline/essays.py`, shown with author, license and source.

Pipeline (offline): `scorecard.py` → `cds.py` → `crawl.py` (official pages only, robots.txt, 1 req/s, own domain only) → `extract.py` (Gemini, every field needs a verbatim quote, missing → null) → `verify.py` (drops fields whose quote isn't in the page, writes `out/report.json`, `--merge` updates the seed). `embed.py` is a stub (M5 not built).

---

## 12. Hackathon submission requirements

Team of 1–5 participants aged 14–19, registered in LOCUS Hackathons; one team per person, one project per team for one case. The **captain** submits on **aistartify.com** with **«Промокод / код участия» = `LOCUSCASE2`** (binds the project to case 2; not a discount code).

| Item | Required content | Where |
| --- | --- | --- |
| Working product | Link to the deployed site; test login if sign-in is needed | https://locus-apex.vercel.app — no login (anonymous auth + demo profile) |
| GitHub | Accessible repository with source code and development history | https://github.com/dracs9/locus_apex |
| README | Task, solution, stack, architecture, run instructions, test scenario, team roles, sources, AI/API, ready-made components, limitations | [README.md](README.md) |
| Demo video | ≤ 3 min: problem, main user journey, live product, final result | link in README → Submission |
| Presentation | ≤ 8 slides, PDF: problem, solution, demo, technology, advantages, team, roadmap | link in README → Submission |
| Technical reference | Models, APIs, libraries, external services, data, verification methods (may be in README) | README → Technical reference |

---

## 13. Milestones

**M1 — Foundation** ✅ monorepo, Supabase migrations + RLS + anonymous sign-in, seed + `seed.py`, engine + pytest, `/health`, `/catalog/*`, JWT auth, deploy (Vercel + Render) with CORS, design tokens + `components/ds`.

**M2 — Core journey** ✅ OpenAPI types + client + hooks, profile endpoints + snapshots + `ComputeResponse`, Landing / Onboarding / Passport / Recommendations with reasons and "why not", University page, `/preview`, Compare with sliders, demo / reset + Settings.

**M3 — Living route** ✅ achievements CRUD + 2-tap sheet + History, diff + Changes + toast, plan (suggestions, student steps, dependencies, conflicts, progress) + Today, favorites affect suggestions, chance history + chart.

**M4 — AI + polish** ✅ `/ai/passport`, `/ai/explain`, `/ai/roadmap-text` with fallbacks and cache; all states; 360 px; dark mode; `.ics`; README.

**Added after M4 (before freeze):** RIASEC interests, grade scales and grade 9, country navigation, attachments, AI mentor, essays, real US data from Scorecard + CDS, 77 universities.

**M5 — Optional:** pipeline run on more universities ✅ (US via Scorecard + CDS); RAG `/ai/ask` ✗ (replaced by mentor tools); voice guide ✗.

**Feature freeze:** 2026-09-18 22:00. After that only bug fixes and docs.

---

## 14. Deployment notes

- Free Render instances sleep (cold start 30–60 s). Before any demo or jury window (19–24 September) hit `/health`; consider a scheduled ping.
- The frontend shows "Пробуждаем сервер…" when a request takes > 3 s, never a blank page.
- `VITE_API_URL` points to the deployed backend; backend `CORS_ORIGINS` includes the Vercel domain.
- Service keys, `SUPABASE_SERVICE_KEY` and `LLM_API_KEY` live only in the backend host's env settings.
- Deploy backend and migrations together; new profile fields live in JSON and need no migration.

---

## 15. Acceptance criteria (jury scenario)

1. From landing to a personal plan in under 3 minutes on a phone, no login.
2. Every recommendation shows at least 2 human-readable reasons linked to profile fields.
3. At least 3 recommendations for the demo profile, across ≥ 2 tiers.
4. Changing budget, major, country or SAT visibly changes recommendations and opens a diff explaining why.
5. Adding an achievement updates recommendations, plan suggestions and chance history.
6. Every deadline and requirement shows a source badge or a "Демо-данные" badge.
7. No percentages of admission chance anywhere (engine, UI, AI and mentor).
8. App works with the LLM API disabled.
9. Reload keeps all state (same browser). Reset clears it.
10. Backend cold start or outage never shows a blank screen.
11. No console errors on the main path; no secrets in the repo.
12. Mentor never changes the plan without the student pressing "Применить".
