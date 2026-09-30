# Marketing Agency Website

A minimal FastAPI website with Jinja2 templates and static CSS and images.
Requires Python 3.10 or newer.

## Local setup

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000 in your browser. Stop the server with Ctrl+C.

## Project layout

- `app/main.py`: FastAPI application and routes.
- `app/templates/base.html`: Shared HTML layout.
- `app/templates/index.html`: Landing page with the supplied client phone images.
- `app/static/css/styles.css`: Website styles.
- `app/static/images/`: Website image assets.

The landing page follows the supplied reference with responsive typography and overlapping phone images. The shared header displays the supplied North Fork Marketing logo. Home, About, Contact, Clients, Instagram, and TikTok links work. The About page at `/about` includes the agency story and Joseph and Francis’s supplied headshots. Fonts are served locally; their licenses are included in `app/static/fonts/`.
`GET /health` returns `{"status": "ok"}`.

## Contact form

`/contact` provides name, email, optional phone, and message fields. `POST /api/contact` validates submissions and inserts them into Supabase’s `public.contact_messages` table. Success is returned only after Supabase confirms the insert; failures preserve the form contents. No email notification is sent.

Setup:

1. Run `supabase/migrations/202609290001_contact_messages.sql` once in your Supabase project's SQL Editor. It creates the table with insert-only visitor permissions and row-level security. The inbox cannot be read, updated, or deleted using the public key. Admin access is deferred.
2. Set `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY` in `.env` locally and in Vercel’s environment variables for each deployment environment. Redeploy Vercel after setting them. Deployed environment variables take precedence over `.env`.
3. Install `requirements.txt` and restart the app.

Existing local SQLite messages are not automatically migrated or deleted. The new handler does not fall back to local storage. A missing table, invalid configuration, or unavailable Supabase connection returns an error instead of reporting a saved message.

Run isolated storage/validation checks with `python -m unittest discover -s tests`.

## Client showcase

`/clients` renders the published records in `app/content/clients.json`. The header, footer, and homepage CTA link to it. The carousel advances every 6.5 seconds, supports arrows and keyboard navigation, and pauses during keyboard navigation, an open detail dialog, or a hidden browser tab. Mouse hover and focus left behind by arrow clicks do not stop autoplay. Reduced-motion users start with autoplay paused. A pause/play button is always available.

Each record has a stable `id`, `name`, `location`, `image`, `image_kind` (`phone` or `artwork`), `gallery` of image paths/URLs, `description`, `project_details`, optional `website_url`, `instagram_url`, and `tiktok_url`, plus `display_order` and `published`. Lower display orders appear first. Images use a consistent square frame. Existing supplied phone images are used until separate client artwork is provided. Empty project writeups, locations, and links are omitted from the view.

The public catalog loader lives in `app/clients.py`, separate from the routes and templates. The client catalog still uses JSON; its admin dashboard and Supabase migration are deferred. When adding the admin dashboard, replace this loader with a database query using the same record shape; store uploaded artwork in object storage, and save drag-to-reorder changes to `display_order`. Administrative writes and publishing require authenticated access; public readers should only see published clients. Never put a database service-role key in browser code.

## ntfy contact alerts

After a contact message is confirmed saved in Supabase, the server publishes a “New Contact Inquiry” alert to ntfy containing the sender’s name, email, and phone number when provided. The message text remains in Supabase. Set `NTFY_SERVER=https://ntfy.sh` and a long, unpredictable `NTFY_TOPIC` in `.env` and in Vercel’s environment settings, then redeploy. Subscribe to that exact topic in the ntfy phone app. Topic names are not passwords: anyone who knows an unprotected topic can read or publish to it. Optional `NTFY_TOKEN` supports a protected topic with bearer authentication.

Leave `NTFY_TOPIC` empty to disable alerts. Delivery is attempted synchronously with a five-second HTTP timeout so it runs before Vercel finishes the request. Notification failures do not change successful contact responses or undo saved messages. Delivery failures are logged without credentials or contact contents. This is best-effort delivery, without a retry queue; Supabase remains the source of truth for the inbox.
