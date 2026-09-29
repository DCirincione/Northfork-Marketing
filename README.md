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

`/contact` provides name, email, optional phone, and message fields. `POST /api/contact` validates submissions and saves them in `data/contacts.sqlite3` (created automatically and excluded from Git). Submissions are stored locally; no email is sent. Connect an email provider before using this as a live inbox. Back up the database and use persistent writable storage when deploying.

## Client showcase

`/clients` renders the published records in `app/content/clients.json`. The header, footer, and homepage CTA link to it. The carousel advances every 6.5 seconds, supports arrows and keyboard navigation, and pauses during keyboard navigation, an open detail dialog, or a hidden browser tab. Mouse hover and focus left behind by arrow clicks do not stop autoplay. Reduced-motion users start with autoplay paused. A pause/play button is always available.

Each record has a stable `id`, `name`, `location`, `image`, `image_kind` (`phone` or `artwork`), `gallery` of image paths/URLs, `description`, `project_details`, optional `website_url`, `instagram_url`, and `tiktok_url`, plus `display_order` and `published`. Lower display orders appear first. Images use a consistent square frame. Existing supplied phone images are used until separate client artwork is provided. Empty project writeups, locations, and links are omitted from the view.

The public catalog loader lives in `app/clients.py`, separate from the routes and templates. No admin dashboard or Supabase connection is implemented yet. When adding the admin dashboard, replace this loader with a database query using the same record shape; store uploaded artwork in object storage, and save drag-to-reorder changes to `display_order`. Administrative writes and publishing require authenticated access; public readers should only see published clients. Never put a database service-role key in browser code.
