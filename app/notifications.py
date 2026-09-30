"""Best-effort ntfy alerts after a contact message has been persisted."""
import logging
import os
import re
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)


def notify_contact_message(contact: dict[str, str]) -> bool:
    topic = os.getenv('NTFY_TOPIC', '').strip()
    if not topic:
        return False
    server = os.getenv('NTFY_SERVER', 'https://ntfy.sh').strip().rstrip('/')
    parsed = urlparse(server)
    if parsed.scheme != 'https' or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', topic):
        logger.warning('ntfy configuration is invalid; message remains saved in Supabase.')
        return False
    lines = [f"Name: {contact['name']}", f"Email: {contact['email']}"]
    phone = contact.get('phone', '').strip()
    if phone:
        lines.append(f"Phone: {phone}")
    headers = {}
    token = os.getenv('NTFY_TOKEN', '').strip()
    if token:
        headers['Authorization'] = f'Bearer {token}'
    try:
        # Complete before returning to Vercel; no detached process or thread.
        response = httpx.post(
            server,
            headers=headers,
            json={
                'topic': topic,
                'title': 'New Contact Inquiry',
                'message': '\n'.join(lines),
                'tags': ['incoming_envelope'],
            },
            timeout=5.0,
        )
        response.raise_for_status()
        return True
    except (httpx.HTTPError, ValueError):
        # Avoid logging tokens, topic URLs, and contact information.
        logger.warning('ntfy delivery failed; message remains saved in Supabase.')
        return False
