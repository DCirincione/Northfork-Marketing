from pathlib import Path
from datetime import datetime, timezone


from app.clients import list_clients
from app.admin import router as admin_router
from app.supabase_api import SupabaseError
from app.contact_storage import ContactStorageError, save_contact_message
from app.notifications import notify_contact_message

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Marketing Agency Website")
app.include_router(admin_router)


@app.middleware("http")
async def private_admin_responses(request, call_next):
    response = await call_next(request)
    if request.url.path == '/admin' or request.url.path.startswith('/admin/'):
        response.headers['Cache-Control'] = 'private, no-store, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['X-Robots-Tag'] = 'noindex, nofollow, noarchive'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' https: blob:; connect-src 'self'; frame-ancestors 'none'; form-action 'self'; base-uri 'self'"
    return response

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
        save_contact_message(submission.model_dump())
    except ContactStorageError as exc:
        raise HTTPException(status_code=503, detail="We couldn’t confirm your message was saved. Please try again or contact us directly.") from exc
    notify_contact_message(submission.model_dump())
    return {"message": "Thank you! Your message has been received."}



@app.get("/clients", response_class=HTMLResponse)
def clients(request: Request):
    try:
        catalog = list_clients()
    except SupabaseError:
        raise HTTPException(503, 'The client showcase is temporarily unavailable. Please try again.') from None
    return templates.TemplateResponse(request=request, name="clients.html", context={"clients": catalog, "client_data": [client.model_dump(mode="json") for client in catalog]})
