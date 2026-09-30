from pathlib import Path
from datetime import datetime, timezone


from app.clients import list_clients
from app.contact_storage import ContactStorageError, save_contact_message
from app.notifications import notify_contact_message

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent

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
        save_contact_message(submission.model_dump())
    except ContactStorageError as exc:
        raise HTTPException(status_code=503, detail="We couldn’t confirm your message was saved. Please try again or contact us directly.") from exc
    notify_contact_message(submission.model_dump())
    return {"message": "Thank you! Your message has been received."}



@app.get("/clients", response_class=HTMLResponse)
def clients(request: Request):
    catalog = list_clients()
    return templates.TemplateResponse(request=request, name="clients.html", context={"clients": catalog, "client_data": [client.model_dump(mode="json") for client in catalog]})
