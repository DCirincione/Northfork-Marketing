-- Run after 202609290001_contact_messages.sql, once, in Supabase SQL Editor.
begin;
create schema if not exists private;
revoke all on schema private from public, anon, authenticated;
create table private.admin_users (
    user_id uuid primary key references auth.users(id) on delete cascade,
    created_at timestamptz not null default now()
);
alter table private.admin_users enable row level security;
revoke all on private.admin_users from public, anon, authenticated;

create or replace function public.is_admin() returns boolean
language sql stable security definer set search_path = ''
as $$ select exists (select 1 from private.admin_users where user_id = (select auth.uid())); $$;
revoke all on function public.is_admin() from public, anon;
grant execute on function public.is_admin() to authenticated;

grant select on public.contact_messages to authenticated;
grant update (is_read) on public.contact_messages to authenticated;
create policy "Admins read contact messages" on public.contact_messages
    for select to authenticated using ((select public.is_admin()));
create policy "Admins update message read status" on public.contact_messages
    for update to authenticated using ((select public.is_admin())) with check ((select public.is_admin()));

create table public.clients (
    id text primary key check (id ~ '^[a-z0-9-]{1,100}$'),
    name text not null check (char_length(btrim(name)) between 1 and 120),
    location text not null default '' check (char_length(location) <= 180),
    image text not null,
    image_kind text not null default 'artwork' check (image_kind in ('phone', 'artwork')),
    gallery jsonb not null default '[]' check (jsonb_typeof(gallery) = 'array' and jsonb_array_length(gallery) <= 20),
    description text not null default '' check (char_length(description) <= 5000),
    project_details text not null default '' check (char_length(project_details) <= 10000),
    website_url text,
    instagram_url text,
    tiktok_url text,
    display_order integer not null default 0 check (display_order between 0 and 1000000),
    published boolean not null default false,
    created_at timestamptz not null default now()
);
alter table public.clients enable row level security;
revoke all on public.clients from public, anon, authenticated;
grant select on public.clients to anon, authenticated;
grant insert, update, delete on public.clients to authenticated;
create policy "Visitors see published clients" on public.clients for select to anon, authenticated using (published);
create policy "Admins manage clients" on public.clients for all to authenticated
    using ((select public.is_admin())) with check ((select public.is_admin()));
create index clients_display_order_idx on public.clients (display_order, id);

-- Validate a complete list and update all positions in one transaction.
create function public.reorder_clients(ordered_ids text[]) returns void
language plpgsql security invoker set search_path = '' as $$
begin
    if not public.is_admin() then raise exception 'Admin access required' using errcode = '42501'; end if;
    lock table public.clients in share row exclusive mode;
    if cardinality(ordered_ids) <> (select count(*) from public.clients)
       or cardinality(ordered_ids) <> (select count(distinct id) from unnest(ordered_ids) as t(id))
       or exists (select 1 from unnest(ordered_ids) as t(id) where not exists (select 1 from public.clients c where c.id=t.id))
    then raise exception 'Client list changed; reload before reordering'; end if;
    update public.clients c set display_order = t.position::integer * 10
    from unnest(ordered_ids) with ordinality as t(id, position) where c.id = t.id;
end; $$;
revoke all on function public.reorder_clients(text[]) from public, anon;
grant execute on function public.reorder_clients(text[]) to authenticated;

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('client-images', 'client-images', true, 4194304, array['image/png', 'image/jpeg', 'image/webp']);
create policy "Admins upload client images" on storage.objects for insert to authenticated
    with check (bucket_id = 'client-images' and (select public.is_admin()));
create policy "Admins inspect client images" on storage.objects for select to authenticated
    using (bucket_id = 'client-images' and (select public.is_admin()));

-- Seed the existing showcase; no client is lost when switching to the database.
insert into public.clients (id, name, location, image, image_kind, gallery, description, project_details, website_url, instagram_url, tiktok_url, display_order, published)
select id, name, location, image, image_kind, gallery, description, project_details, website_url, instagram_url, tiktok_url, display_order, published
from jsonb_to_recordset('[{"id": "box-pickleball", "name": "Box Pickleball", "location": "Riverhead, NY", "image": "/static/images/box-pickleball.png", "image_kind": "phone", "gallery": [], "description": "Long Island\u2019s pickleball destination, with courts, a bar, food, and events.", "project_details": "", "website_url": null, "instagram_url": "https://www.instagram.com/boxpickleball/", "tiktok_url": null, "display_order": 10, "published": true}, {"id": "aldrich-sports", "name": "Aldrich Sports", "location": "Mattituck, NY", "image": "/static/images/aldrich-sports.png", "image_kind": "phone", "gallery": [], "description": "Long Island sports leagues, events, content, and fundraisers.", "project_details": "", "website_url": "https://www.aldrichsports.com/", "instagram_url": "https://www.instagram.com/aldrichsportsny/", "tiktok_url": null, "display_order": 20, "published": true}, {"id": "augusta", "name": "Augusta Lawn Care", "location": "Westhampton, NY", "image": "/static/images/augusta.png", "image_kind": "phone", "gallery": [], "description": "Augusta Lawn Care Services of Westhampton. Design. Build. Maintain.", "project_details": "", "website_url": null, "instagram_url": "https://www.instagram.com/augustalawncarewhb/", "tiktok_url": null, "display_order": 30, "published": true}, {"id": "wish-you-were-beer", "name": "Wish You Were Beer", "location": "", "image": "/static/images/wish-you-were-beer.png", "image_kind": "phone", "gallery": [], "description": "Wish You Were Beer clothing and merchandise.", "project_details": "", "website_url": null, "instagram_url": "https://www.instagram.com/shopwishyouwerebeer/", "tiktok_url": null, "display_order": 40, "published": true}, {"id": "mattituck-run-club", "name": "Mattituck Run Club", "location": "Mattituck, NY", "image": "/static/images/run-club.png", "image_kind": "phone", "gallery": [], "description": "A local run club bringing runners and walkers together in Mattituck.", "project_details": "", "website_url": null, "instagram_url": "https://www.instagram.com/mattituckrunclub/", "tiktok_url": null, "display_order": 50, "published": true}]'::jsonb) as x(id text, name text, location text, image text, image_kind text, gallery jsonb, description text, project_details text, website_url text, instagram_url text, tiktok_url text, display_order integer, published boolean);
notify pgrst, 'reload schema';
commit;
