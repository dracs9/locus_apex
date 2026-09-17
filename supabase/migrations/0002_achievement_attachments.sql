-- Applyra — photos and links attached to achievements

create table if not exists public.achievement_attachments (
  id              uuid primary key default gen_random_uuid(),
  achievement_id  uuid not null references public.achievements (id) on delete cascade,
  user_id         uuid not null references auth.users (id) on delete cascade,
  kind            text not null check (kind in ('photo', 'link')),
  url             text,
  storage_path    text,
  title           text,
  content_type    text,
  size_bytes      int,
  created_at      timestamptz not null default now(),
  check ((kind = 'link' and url is not null) or (kind = 'photo' and storage_path is not null))
);
create index if not exists achievement_attachments_achievement_idx on public.achievement_attachments (achievement_id);
create index if not exists achievement_attachments_user_idx on public.achievement_attachments (user_id);

alter table public.achievement_attachments enable row level security;
drop policy if exists "own attachments" on public.achievement_attachments;
create policy "own attachments" on public.achievement_attachments
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

-- Private bucket; only the backend (service key) reads and writes it, photos are shown via signed URLs.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('achievement-files', 'achievement-files', false, 5242880,
        array['image/jpeg', 'image/png', 'image/webp', 'image/heic', 'image/heif'])
on conflict (id) do nothing;
