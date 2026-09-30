-- Run once in the Supabase SQL Editor for this project.
-- Public submissions can insert only the four form fields; inbox access is private.
begin;

create table public.contact_messages (
    id uuid primary key default gen_random_uuid(),
    name text not null check (char_length(btrim(name)) between 1 and 120),
    email text not null check (
        char_length(email) <= 254 and email ~ '^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$'
    ),
    phone text not null default '' check (
        char_length(phone) <= 40 and phone ~ '^[0-9+().[:space:]xX-]*$'
    ),
    message text not null check (char_length(btrim(message)) between 1 and 5000),
    is_read boolean not null default false,
    created_at timestamptz not null default now()
);

create index contact_messages_created_at_idx on public.contact_messages (created_at desc);
alter table public.contact_messages enable row level security;

revoke all on table public.contact_messages from public, anon, authenticated;
grant usage on schema public to anon, authenticated;
grant insert (name, email, phone, message) on public.contact_messages to anon, authenticated;

create policy "Visitors can submit contact messages"
    on public.contact_messages for insert
    to anon, authenticated
    with check (is_read = false);

-- No public SELECT, UPDATE, or DELETE access. Admin access will be added separately.
notify pgrst, 'reload schema';
commit;
