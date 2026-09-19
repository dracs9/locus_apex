-- Applyra — collection of admitted students' essays (openessays.org), loaded by supabase/seed.py.
-- Read-only catalog data like universities: public read, writes only through the service connection.

create table if not exists public.essays (
  id             text primary key,
  university_id  text,                 -- catalog id when the school is in public.universities
  level          text not null check (level in ('bachelor', 'master', 'phd', 'mba', 'other')),
  kind           text not null,
  word_count     int  not null,
  data           jsonb not null,       -- the rest of EssaySummary (school, program, majors, topics, author, license, links, excerpt)
  body           text not null,
  refs           jsonb not null default '[]'::jsonb
);
create index if not exists essays_university_idx on public.essays (university_id);

alter table public.essays enable row level security;
drop policy if exists "essays read" on public.essays;
create policy "essays read" on public.essays for select using (true);
