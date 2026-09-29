"""Public client catalog. Replace this loader with a database repository when admin is added."""
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator

CATALOG_PATH = Path(__file__).resolve().parent / "content" / "clients.json"


class Client(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9-]+$")
    name: str
    location: str = ""
    image: str
    image_kind: Literal["phone", "artwork"] = "artwork"
    gallery: list[str] = Field(default_factory=list)
    description: str = ""
    project_details: str = ""
    website_url: HttpUrl | None = None
    instagram_url: HttpUrl | None = None
    tiktok_url: HttpUrl | None = None
    display_order: int = 0
    published: bool = False

    @field_validator("image")
    @classmethod
    def validate_image(cls, value):
        if not value.startswith("/static/"):
            return str(HttpUrl(value))
        return value

    @field_validator("gallery")
    @classmethod
    def validate_gallery(cls, value):
        return [cls.validate_image(image) for image in value]


def list_clients() -> list[Client]:
    clients = [Client.model_validate(record) for record in json.loads(CATALOG_PATH.read_text())]
    if len({client.id for client in clients}) != len(clients):
        raise ValueError("Client IDs must be unique")
    return sorted((client for client in clients if client.published), key=lambda client: (client.display_order, client.id))
