"""Contact inbox persistence through Supabase's insert-only public API."""
import logging
import os
from pathlib import Path
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / '.env', override=False)
logger = logging.getLogger(__name__)


class ContactStorageError(Exception):
    """The message was not confirmed as saved."""


def save_contact_message(message: dict[str, str]) -> None:
    url = os.getenv('SUPABASE_URL', '').strip().rstrip('/')
    key = os.getenv('SUPABASE_PUBLISHABLE_KEY', '').strip()
    if not key or urlparse(url).scheme != 'https' or not urlparse(url).netloc:
        logger.error('Supabase contact storage is not configured.')
        raise ContactStorageError('Contact storage is not configured.')
    try:
        response = httpx.post(
            f'{url}/rest/v1/contact_messages',
            headers={'apikey': key, 'Prefer': 'return=minimal'},
            json=message,
            timeout=15.0,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        # Never log message content, credentials, or database response bodies.
        logger.error('Supabase contact insert failed (HTTP %s).', exc.response.status_code)
        raise ContactStorageError('Contact storage rejected the message.') from None
    except httpx.RequestError:
        logger.error('Supabase contact insert could not be confirmed due to a network error.')
        raise ContactStorageError('Contact storage is unavailable.') from None
