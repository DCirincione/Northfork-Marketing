"""Small server-side Supabase transport; never exposes credentials or raw errors."""
import os
from pathlib import Path
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / '.env', override=False)


class SupabaseError(Exception):
    def __init__(self, status=503, code=''):
        self.status = status
        self.code = code
        super().__init__('Supabase request failed')


def settings():
    url = os.getenv('SUPABASE_URL', '').strip().rstrip('/')
    key = os.getenv('SUPABASE_PUBLISHABLE_KEY', '').strip()
    if urlparse(url).scheme != 'https' or not urlparse(url).netloc or not key:
        raise SupabaseError()
    return url, key


def request(method, path, *, token=None, json=None, params=None, content=None, headers=None):
    url, key = settings()
    outgoing = {'apikey': key, **(headers or {})}
    if token:
        outgoing['Authorization'] = f'Bearer {token}'
    try:
        response = httpx.request(method, url + path, headers=outgoing, json=json,
                                params=params, content=content, timeout=15.0)
    except httpx.RequestError:
        raise SupabaseError() from None
    if not response.is_success:
        try:
            code = response.json().get('code', '')
        except (ValueError, AttributeError):
            code = ''
        raise SupabaseError(response.status_code, code)
    if not response.content:
        return None
    try:
        return response.json()
    except ValueError:
        raise SupabaseError() from None
