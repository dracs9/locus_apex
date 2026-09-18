-- Applyra — AI mentor chat history. The mentor only proposes plan changes (actions);
-- the student applies or dismisses each one, and its status is kept in `actions`.

create table if not exists public.mentor_messages (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references auth.users (id) on delete cascade,
  role        text not null check (role in ('user', 'assistant')),
  text        text not null,
  actions     jsonb not null default '[]'::jsonb,
  generated   boolean not null default false,
  created_at  timestamptz not null default now()
);
create index if not exists mentor_messages_user_idx on public.mentor_messages (user_id, created_at);

alter table public.mentor_messages enable row level security;
drop policy if exists "own mentor messages" on public.mentor_messages;
create policy "own mentor messages" on public.mentor_messages
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());
