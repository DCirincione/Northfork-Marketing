import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.admin import COOKIE, MAX_UPLOAD
from app.supabase_api import SupabaseError
from app.clients import list_clients

ORIGIN = {'Origin': 'https://testserver', 'X-Admin-Request': '1'}
RECORD = {'id': 'test-client', 'name': 'Test Client', 'image': '/static/images/augusta.png', 'published': False}


class AdminTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app, base_url='https://testserver')

    def authenticate(self):
        self.client.cookies.set(COOKIE, 'test-access-token', path='/admin')

    @staticmethod
    def database(method, path, **kwargs):
        if path == '/auth/v1/user': return {'id': 'approved-user'}
        if path == '/rest/v1/rpc/is_admin': return True
        if path == '/rest/v1/clients': return [RECORD]
        if path == '/rest/v1/contact_messages': return []
        return None

    def test_unauthenticated_pages_redirect_and_apis_reject(self):
        with patch('app.admin.db.request') as request:
            response = self.client.get('/admin', follow_redirects=False)
            self.assertEqual(response.status_code, 303)
            self.assertEqual(response.headers['location'], '/admin/login')
            for method, url, body in [('GET', '/admin/api/messages', None), ('GET', '/admin/api/clients', None), ('POST', '/admin/api/clients', RECORD), ('POST', '/admin/api/clients/reorder', {'ids': ['test-client']}), ('POST', '/admin/api/uploads', None)]:
                response = self.client.request(method, url, json=body, headers=ORIGIN)
                self.assertEqual(response.status_code, 401, url)
            request.assert_not_called()

    def test_unapproved_user_cannot_access(self):
        self.authenticate()
        with patch('app.admin.db.request', side_effect=[{'id': 'outsider'}, False]):
            self.assertEqual(self.client.get('/admin/api/messages').status_code, 403)

    def test_invalid_and_expired_tokens_rejected(self):
        self.authenticate()
        with patch('app.admin.db.request', side_effect=SupabaseError(401)):
            self.assertEqual(self.client.get('/admin/api/clients').status_code, 401)

    def test_fail_closed_when_membership_unavailable(self):
        self.authenticate()
        with patch('app.admin.db.request', side_effect=SupabaseError(503)):
            self.assertEqual(self.client.get('/admin/api/messages').status_code, 503)

    def test_login_cookie_and_no_token_in_body(self):
        with patch('app.admin.db.request', side_effect=[{'access_token': 'test-access-token', 'expires_in': 3600}, {'id': 'approved'}, True]):
            response = self.client.post('/admin/api/login', json={'email': 'admin@example.com', 'password': 'not-a-real-password'}, headers=ORIGIN)
        self.assertEqual(response.status_code, 200)
        cookie = response.headers['set-cookie']
        for flag in ['HttpOnly', 'Secure', 'SameSite=strict', 'Path=/admin', 'Max-Age=3600']:
            self.assertIn(flag, cookie)
        self.assertNotIn('test-access-token', response.text)

    def test_unapproved_login_does_not_set_cookie(self):
        with patch('app.admin.db.request', side_effect=[{'access_token': 'test-access-token'}, {'id': 'outsider'}, False]):
            response = self.client.post('/admin/api/login', json={'email': 'other@example.com', 'password': 'password'}, headers=ORIGIN)
        self.assertEqual(response.status_code, 403)
        self.assertNotIn('set-cookie', response.headers)

    def test_cross_origin_or_missing_header_rejected(self):
        self.authenticate()
        for headers in [{}, {'Origin': 'https://evil.example', 'X-Admin-Request': '1'}, {'Origin': 'https://testserver'}]:
            with patch('app.admin.db.request') as request:
                response = self.client.post('/admin/api/login', json={'email': 'a@b.com', 'password': 'password'}, headers=headers)
                self.assertEqual(response.status_code, 403)
                request.assert_not_called()

    def test_private_headers_on_pages_and_errors(self):
        for url in ['/admin/login', '/admin/api/messages']:
            response = self.client.get(url)
            self.assertIn('no-store', response.headers['cache-control'])
            self.assertIn('noindex', response.headers['x-robots-tag'])
            self.assertEqual(response.headers['x-frame-options'], 'DENY')

    def test_messages_read_state_and_client_crud_use_user_token(self):
        self.authenticate()
        with patch('app.admin.db.request', side_effect=self.database) as request:
            self.assertEqual(self.client.get('/admin/api/messages').status_code, 200)
            self.assertEqual(self.client.post('/admin/api/clients', json=RECORD, headers=ORIGIN).status_code, 201)
            self.assertEqual(self.client.put('/admin/api/clients/test-client', json=RECORD, headers=ORIGIN).status_code, 200)
            self.assertEqual(self.client.delete('/admin/api/clients/test-client', headers=ORIGIN).status_code, 200)
        for call in request.call_args_list:
            self.assertEqual(call.kwargs['token'], 'test-access-token')

    def test_client_urls_cannot_be_javascript(self):
        self.authenticate()
        with patch('app.admin.db.request', side_effect=self.database):
            response = self.client.post('/admin/api/clients', json=dict(RECORD, website_url='javascript:alert(1)'), headers=ORIGIN)
        self.assertEqual(response.status_code, 422)

    def test_duplicate_order_is_rejected(self):
        self.authenticate()
        with patch('app.admin.db.request', side_effect=self.database) as request:
            response = self.client.post('/admin/api/clients/reorder', json={'ids': ['test-client', 'test-client']}, headers=ORIGIN)
        self.assertEqual(response.status_code, 422)
        self.assertFalse(any(call.args[1] == '/rest/v1/rpc/reorder_clients' for call in request.call_args_list))

    def test_atomic_reorder_rpc(self):
        self.authenticate()
        with patch('app.admin.db.request', side_effect=self.database) as request:
            response = self.client.post('/admin/api/clients/reorder', json={'ids': ['test-client']}, headers=ORIGIN)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(request.call_args.args[1], '/rest/v1/rpc/reorder_clients')
        self.assertEqual(request.call_args.kwargs['json'], {'ordered_ids': ['test-client']})

    def test_upload_rejects_svg_mismatched_and_oversized_files(self):
        self.authenticate()
        for media, data, expected in [('image/svg+xml', b'<svg/>', 422), ('image/png', b'not-an-image', 422), ('image/png', b'\x89PNG\r\n\x1a\n' + b'a' * MAX_UPLOAD, 413)]:
            with patch('app.admin.db.request', side_effect=self.database) as request:
                response = self.client.post('/admin/api/uploads', headers={**ORIGIN, 'Content-Type': media}, content=data)
            self.assertEqual(response.status_code, expected)
            self.assertFalse(any('/storage/' in call.args[1] for call in request.call_args_list))

    def test_logout_clears_expired_session(self):
        self.authenticate()
        with patch('app.admin.db.request', side_effect=SupabaseError(401)):
            response = self.client.post('/admin/api/logout', headers=ORIGIN)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Max-Age=0', response.headers['set-cookie'])

    def test_public_catalog_uses_database_and_does_not_restore_empty_catalog(self):
        with patch('app.clients.db.request', return_value=[]):
            self.assertEqual(list_clients(), [])
        with patch('app.clients.db.request', side_effect=SupabaseError(503)):
            with self.assertRaises(SupabaseError): list_clients()
