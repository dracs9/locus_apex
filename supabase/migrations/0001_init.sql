-- AI Admission Route — initial schema (§6)

create table if not exists public.universities (
  id          text primary key,
  name        text not null,
  country     text not null,
  city        text not null,
  website     text not null,
  world_rank  int  not null,
  data        jsonb not null
);
create index if not exists universities_country_idx on public.universities (country);

create table if not exists public.majors (
  id         text primary key,
  name_ru    text not null,
  name_en    text not null,
  cip_codes  text[] not null default '{}'
);

create table if not exists public.profiles (
  user_id     uuid primary key references auth.users (id) on delete cascade,
  data        jsonb not null,
  updated_at  timestamptz not null default now()
);

create table if not exists public.achievements (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references auth.users (id) on delete cascade,
  type        text not null check (type in ('SAT','IELTS','TOEFL','OLYMPIAD','PROJECT','VOLUNTEER','COMPETITION','OTHER')),
  score       double precision,
  title       text,
  level       text check (level in ('school','city','national','international')),
  date        date not null,
  status      text not null check (status in ('done','planned')),
  created_at  timestamptz not null default now()
);
create index if not exists achievements_user_idx on public.achievements (user_id);

create table if not exists public.favorites (
  user_id        uuid not null references auth.users (id) on delete cascade,
  university_id  text not null references public.universities (id) on delete cascade,
  primary key (user_id, university_id)
);

create table if not exists public.roadmap_progress (
  user_id  uuid not null references auth.users (id) on delete cascade,
  step_id  text not null,
  done     boolean not null,
  done_at  timestamptz,
  primary key (user_id, step_id)
);

create table if not exists public.snapshots (
  id                uuid primary key default gen_random_uuid(),
  user_id           uuid not null references auth.users (id) on delete cascade,
  at                timestamptz not null default now(),
  result            jsonb not null,
  roadmap_step_ids  text[] not null default '{}',
  profile_hash      text not null,
  cause             text not null,
  diff              jsonb
);
create index if not exists snapshots_user_at_idx on public.snapshots (user_id, at desc);

create table if not exists public.llm_cache (
  key         text primary key,
  value       jsonb not null,
  created_at  timestamptz not null default now()
);

-- Row Level Security. The backend connects with the service connection string (bypasses RLS)
-- and always filters by the authenticated user_id; RLS protects against direct client access.
alter table public.universities     enable row level security;
alter table public.majors           enable row level security;
alter table public.profiles         enable row level security;
alter table public.achievements     enable row level security;
alter table public.favorites        enable row level security;
alter table public.roadmap_progress enable row level security;
alter table public.snapshots        enable row level security;
alter table public.llm_cache        enable row level security;

drop policy if exists "catalog read" on public.universities;
create policy "catalog read" on public.universities for select using (true);
drop policy if exists "majors read" on public.majors;
create policy "majors read" on public.majors for select using (true);

drop policy if exists "own profile" on public.profiles;
create policy "own profile" on public.profiles for all using (user_id = auth.uid()) with check (user_id = auth.uid());
drop policy if exists "own achievements" on public.achievements;
create policy "own achievements" on public.achievements for all using (user_id = auth.uid()) with check (user_id = auth.uid());
drop policy if exists "own favorites" on public.favorites;
create policy "own favorites" on public.favorites for all using (user_id = auth.uid()) with check (user_id = auth.uid());
drop policy if exists "own progress" on public.roadmap_progress;
create policy "own progress" on public.roadmap_progress for all using (user_id = auth.uid()) with check (user_id = auth.uid());
drop policy if exists "own snapshots" on public.snapshots;
create policy "own snapshots" on public.snapshots for all using (user_id = auth.uid()) with check (user_id = auth.uid());
-- llm_cache: no policies = no client access (backend only)
