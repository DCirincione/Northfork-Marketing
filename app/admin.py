"""Admin-only routes. Supabase validates identity; RLS also enforces membership."""
import os
import re
import uuid
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool

from app import supabase_api as db
from app.clients import Client

router = APIRouter(prefix='/admin')
templates = Jinja2Templates(directory=Path(__file__).resolve().parent / 'templates')
COOKIE = 'nofo_admin_access'
MAX_UPLOAD = 4 * 1024 * 1024


def require_origin(request: Request):
    origin = urlparse(request.headers.get('origin', ''))
    local = request.url.hostname in {'localhost', '127.0.0.1', 'testserver'} and not os.getenv('VERCEL')
    if (origin.netloc != request.url.netloc or origin.scheme not in ({'http', 'https'} if local else {'https'})
            or request.headers.get('x-admin-request') != '1'):
        raise HTTPException(403, 'Request origin could not be verified. Reload and try again.')


def secure_cookie(request):
    return bool(os.getenv('VERCEL')) or request.url.scheme == 'https' or request.url.hostname not in {'localhost', '127.0.0.1', 'testserver'}


def authorized(token):
    user = db.request('GET', '/auth/v1/user', token=token)
    if not isinstance(user, dict) or not user.get('id'):
        raise HTTPException(401, 'Please sign in again.')
    if db.request('POST', '/rest/v1/rpc/is_admin', token=token, json={}) is not True:
        raise HTTPException(403, 'This account does not have admin access.')
    return user


def require_admin(request: Request):
    token = request.cookies.get(COOKIE)
    if not token:
        raise HTTPException(401, 'Please sign in.')
    try:
        authorized(token)
    except db.SupabaseError as exc:
        if exc.status in (401, 403):
            raise HTTPException(401, 'Your session expired. Please sign in again.') from None
        raise HTTPException(503, 'Admin access could not be verified. Please try again.') from None
    return token


def data_request(*args, **kwargs):
    try:
        return db.request(*args, **kwargs)
    except db.SupabaseError as exc:
        if exc.status in (401, 403):
            raise HTTPException(403, 'Access denied. Please sign in again.') from None
        if exc.status == 409:
            raise HTTPException(409, 'That client ID already exists. Choose a different ID.') from None
        if exc.code == 'PGRST205' or exc.status == 404:
            raise HTTPException(503, 'Admin database setup is incomplete. Run the admin migration in Supabase.') from None
        raise HTTPException(503, 'Could not complete the request. Please try again.') from None


@router.get('')
@router.get('/', include_in_schema=False)
def dashboard(request: Request):
    try:
        require_admin(request)
    except HTTPException as exc:
        if exc.status_code in (401, 403):
            return RedirectResponse('/admin/login', status_code=303)
        raise
    return templates.TemplateResponse(request=request, name='admin/dashboard.html')


@router.get('/login')
def login_page(request: Request):
    return templates.TemplateResponse(request=request, name='admin/login.html')


class Login(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=1024)


@router.post('/api/login', dependencies=[Depends(require_origin)])
def login(payload: Login, request: Request, response: Response):
    try:
        session = db.request('POST', '/auth/v1/token', params={'grant_type': 'password'},
                             json={'email': payload.email.strip(), 'password': payload.password})
        token = session['access_token']
        authorized(token)
    except db.SupabaseError as exc:
        if exc.status == 429:
            raise HTTPException(429, 'Too many login attempts. Please wait before trying again.') from None
        if exc.status in (400, 401, 403):
            raise HTTPException(401, 'Unable to sign in with these credentials.') from None
        raise HTTPException(503, 'Login is unavailable. Check the Supabase admin setup.') from None
    except (KeyError, TypeError):
        raise HTTPException(503, 'Login is unavailable. Please try again.') from None
    # No refresh token persisted: expiration requires a fresh login, at most one hour.
    lifetime = max(1, min(int(session.get('expires_in', 3600)), 3600))
    response.set_cookie(COOKIE, token, max_age=lifetime, path='/admin', httponly=True,
                        secure=secure_cookie(request), samesite='strict')
    return {'ok': True}


@router.post('/api/logout', dependencies=[Depends(require_origin)])
def logout(request: Request, response: Response):
    token = request.cookies.get(COOKIE)
    if token:
        try:
            db.request('POST', '/auth/v1/logout', token=token, params={'scope': 'local'})
        except db.SupabaseError:
            pass
    response.delete_cookie(COOKIE, path='/admin', httponly=True,
                           secure=secure_cookie(request), samesite='strict')
    return {'ok': True}


@router.get('/api/messages')
def messages(offset: int = 0, unread: bool = False, token=Depends(require_admin)):
    if offset < 0 or offset > 1000000:
        raise HTTPException(422, 'Invalid page.')
    params = {'select': 'id,name,email,phone,message,is_read,created_at', 'order': 'created_at.desc,id.desc',
              'limit': '26', 'offset': str(offset)}
    if unread:
        params['is_read'] = 'eq.false'
    rows = data_request('GET', '/rest/v1/contact_messages', token=token, params=params)
    return {'items': rows[:25], 'has_more': len(rows) > 25}


class MessageState(BaseModel):
    model_config = ConfigDict(extra='forbid')
    is_read: bool


@router.patch('/api/messages/{message_id}', dependencies=[Depends(require_origin)])
def update_message(message_id: uuid.UUID, payload: MessageState, token=Depends(require_admin)):
    rows = data_request('PATCH', '/rest/v1/contact_messages', token=token,
                        params={'id': f'eq.{message_id}'}, json=payload.model_dump(),
                        headers={'Prefer': 'return=representation'})
    if not rows:
        raise HTTPException(404, 'Message not found.')
    return {'ok': True}


@router.get('/api/clients')
def clients(token=Depends(require_admin)):
    return data_request('GET', '/rest/v1/clients', token=token,
                        params={'select': '*', 'order': 'display_order.asc,id.asc'})


class ClientInput(Client):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=120)
    location: str = Field(default='', max_length=180)
    description: str = Field(default='', max_length=5000)
    project_details: str = Field(default='', max_length=10000)
    gallery: list[str] = Field(default_factory=list, max_length=20)
    display_order: int = Field(default=0, ge=0, le=1000000)


def client_id(value):
    if not re.fullmatch(r'[a-z0-9-]{1,100}', value):
        raise HTTPException(422, 'Use a client ID containing lowercase letters, numbers, and hyphens.')
    return value


@router.post('/api/clients', status_code=201, dependencies=[Depends(require_origin)])
def create_client(payload: ClientInput, token=Depends(require_admin)):
    client_id(payload.id)
    return data_request('POST', '/rest/v1/clients', token=token,
                        json=payload.model_dump(mode='json'), headers={'Prefer': 'return=representation'})[0]


@router.put('/api/clients/{identifier}', dependencies=[Depends(require_origin)])
def edit_client(identifier: str, payload: ClientInput, token=Depends(require_admin)):
    if client_id(identifier) != payload.id:
        raise HTTPException(422, 'Client IDs cannot be changed after creation.')
    rows = data_request('PATCH', '/rest/v1/clients', token=token,
                        params={'id': f'eq.{identifier}'}, json=payload.model_dump(mode='json'),
                        headers={'Prefer': 'return=representation'})
    if not rows:
        raise HTTPException(404, 'Client not found.')
    return rows[0]


@router.delete('/api/clients/{identifier}', dependencies=[Depends(require_origin)])
def delete_client(identifier: str, token=Depends(require_admin)):
    data_request('DELETE', '/rest/v1/clients', token=token, params={'id': f'eq.{client_id(identifier)}'})
    return {'ok': True}


class ClientOrder(BaseModel):
    ids: list[str] = Field(min_length=1, max_length=1000)


@router.post('/api/clients/reorder', dependencies=[Depends(require_origin)])
def reorder(payload: ClientOrder, token=Depends(require_admin)):
    if len(set(payload.ids)) != len(payload.ids):
        raise HTTPException(422, 'Each client must appear exactly once.')
    for identifier in payload.ids:
        client_id(identifier)
    data_request('POST', '/rest/v1/rpc/reorder_clients', token=token, json={'ordered_ids': payload.ids})
    return {'ok': True}


@router.post('/api/uploads', dependencies=[Depends(require_origin)])
async def upload(request: Request, token=Depends(require_admin)):
    media_type = request.headers.get('content-type', '').split(';')[0]
    extensions = {'image/png': 'png', 'image/jpeg': 'jpg', 'image/webp': 'webp'}
    if media_type not in extensions:
        raise HTTPException(422, 'Upload a PNG, JPEG, or WebP image.')
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > MAX_UPLOAD:
            raise HTTPException(413, 'Images must be 4 MB or smaller.')
    signatures = {'image/png': data.startswith(b'\x89PNG\r\n\x1a\n'),
                  'image/jpeg': data.startswith(b'\xff\xd8\xff'),
                  'image/webp': data.startswith(b'RIFF') and data[8:12] == b'WEBP'}
    if not signatures[media_type]:
        raise HTTPException(422, 'The file does not match the selected image type.')
    filename = f'{uuid.uuid4()}.{extensions[media_type]}'
    await run_in_threadpool(data_request, 'POST', f'/storage/v1/object/client-images/{filename}',
                            token=token, content=bytes(data), headers={'Content-Type': media_type, 'x-upsert': 'false'})
    url, _ = db.settings()
    return {'url': f'{url}/storage/v1/object/public/client-images/{filename}'}
