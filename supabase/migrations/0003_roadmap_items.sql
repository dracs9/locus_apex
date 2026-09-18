-- Applyra — the student's own plan. The engine only suggests steps; the student adds, edits and deletes them.
-- roadmap_progress (0001) is no longer used: generated steps are gone, so there is nothing to attach progress to.

create table if not exists public.roadmap_items (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references auth.users (id) on delete cascade,
  kind            text not null check (kind in ('exam', 'document', 'academic', 'activity', 'application')),
  title           text not null check (length(title) between 1 and 200),
  due_date        date not null,
  note            text,
  source_key      text,            -- suggestion id it was added from, e.g. 'exam:SAT', 'apply:mit:RD', 'act:olympiad'
  university_ids  text[] not null default '{}',
  source_url      text,
  is_demo         boolean not null default false,
  done            boolean not null default false,
  done_at         timestamptz,
  created_at      timestamptz not null default now()
);
create index if not exists roadmap_items_user_idx on public.roadmap_items (user_id);
create unique index if not exists roadmap_items_user_source_key on public.roadmap_items (user_id, source_key)
  where source_key is not null;

alter table public.roadmap_items enable row level security;
drop policy if exists "own roadmap items" on public.roadmap_items;
create policy "own roadmap items" on public.roadmap_items
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());
