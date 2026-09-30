# Admin setup

The dashboard code is ready at `/admin`. It is not linked in public navigation. Five clicks on the header logo within six seconds open it. Ordinary logo clicks still navigate home. The shortcut is a convenience, not an access control.

## One-time Supabase setup

1. In the same Supabase project used for contact messages, open **SQL Editor** and run `supabase/migrations/202609290002_admin_dashboard.sql`. The earlier contact-message migration must already be applied. This creates the admin allowlist, client table, image bucket, access policies, ordering function, and seeds all five existing clients. Run it once; the migration is transactional.
2. Under **Authentication**, disable new user signups in the project's authentication settings. There is no registration route or form on this site.
3. Under **Authentication → Users**, manually create each administrator with their own email and strong password. Confirm the email for these manually provisioned accounts. Do not share a password or use a public visitor account.
4. Approve each created account in SQL Editor. Replace the email in the following block and run it once per administrator:

```sql
do $$
declare
    approved_user uuid;
begin
    select id into approved_user
    from auth.users where lower(email) = lower('REPLACE_WITH_ADMIN_EMAIL');
    if approved_user is null then
        raise exception 'Create the user in Authentication → Users first';
    end if;
    insert into private.admin_users (user_id)
    values (approved_user) on conflict do nothing;
end $$;
```

5. Ensure `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY` are configured in Vercel, then deploy the code. No service-role key or new session secret is needed. Visit `/admin/login` and sign in.
6. Verify an approved account can read messages and save a draft client. Publish it and confirm it appears at `/clients`. Verify an unapproved account cannot access the dashboard. Test uploading a PNG/JPEG/WebP and reordering clients.

The local checks use mocked Supabase responses. Live authentication, database policies, and uploads can only be verified after this setup is applied.

## Features

- Inbox with 25 messages per page, an unread filter, full message details, and read/unread controls.
- Create, edit, delete, draft, and publish clients; manage names, locations, card images, galleries, project text, and social/website links.
- Drag clients to reorder, or use accessible up/down buttons, then select **Save order**. The whole order is saved atomically.
- Upload PNG, JPEG, or WebP images up to 4 MB. `client-images` is a public asset bucket; do not upload private documents. Deleting a client does not delete images, since other clients may reference them.
- Public pages read published clients from Supabase after migration. An empty table remains empty. The JSON catalog is used only when credentials are absent or the clients table does not yet exist, not on transient database errors.

## Sessions and authorization

- Supabase validates email/password and verifies each session. An entry in `private.admin_users` is also required for every admin request.
- Row-level security independently enforces access on messages, clients, reordering, and uploads. Normal authenticated users are not admins and cannot grant themselves access.
- Access tokens are stored in an HTTP-only, same-site cookie scoped to `/admin`, with Secure enabled for production. Refresh tokens are not persisted. Login expires after at most one hour, requiring a fresh sign-in.
- Admin responses are private/no-store, excluded from indexing, and protected against framing. Write requests require a matching Origin and custom request header. Tokens are not exposed to JavaScript or localStorage.
- Sign out clears the cookie and attempts Supabase logout. Supabase access tokens can remain valid until expiry; removing allowlist membership immediately prevents further admin requests even if a token still exists.

To revoke admin access:

```sql
delete from private.admin_users
where user_id in (select id from auth.users where lower(email) = lower('REPLACE_WITH_ADMIN_EMAIL'));
```

Passwords are managed in Supabase Auth, not stored in this repository. Use Supabase's account-management/recovery workflow if an administrator needs a reset.
