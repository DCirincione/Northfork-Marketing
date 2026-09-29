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
