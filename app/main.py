from pathlib import Path
from datetime import datetime, timezone
import sqlite3

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent
CONTACT_DB = BASE_DIR.parent / "data" / "contacts.sqlite3"

app = FastAPI(title="Marketing Agency Website")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(
    directory=BASE_DIR / "templates",
    context_processors=[lambda request: {"current_year": datetime.now(timezone.utc).year}],
)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    return templates.TemplateResponse(request=request, name="about.html")


@app.get("/contact", response_class=HTMLResponse)
async def contact(request: Request):
    return templates.TemplateResponse(request=request, name="contact.html")


class ContactSubmission(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    phone: str = Field(default="", max_length=40, pattern=r"^[0-9+().\s\-xX]*$")
    message: str = Field(min_length=1, max_length=5000)


@app.post("/api/contact", status_code=201)
def submit_contact(submission: ContactSubmission):
    try:
        CONTACT_DB.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(CONTACT_DB) as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")
            connection.execute(
                "INSERT INTO contacts (name, email, phone, message) VALUES (?, ?, ?, ?)",
                (submission.name, submission.email, submission.phone, submission.message),
            )
    except (OSError, sqlite3.Error) as exc:
        raise HTTPException(status_code=503, detail="We couldn’t save your message. Please try again or contact us directly.") from exc
    return {"message": "Your message has been saved. For a direct reply, please call or email us while email delivery is being connected."}
