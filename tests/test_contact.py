import os
import unittest
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.contact_storage import ContactStorageError, save_contact_message


class ContactTests(unittest.TestCase):
    def setUp(self):
        notification = patch('app.main.notify_contact_message', return_value=True)
        self.notify = notification.start()
        self.addCleanup(notification.stop)
        self.client = TestClient(app)
        self.payload = dict(name='Test Visitor', email='visitor@example.com', phone='', message='Test inquiry')

    def test_valid_submission_is_saved(self):
        with patch('app.main.save_contact_message') as save:
            response = self.client.post('/api/contact', json=dict(self.payload, name=' Test Visitor '))
        self.assertEqual(response.status_code, 201)
        save.assert_called_once_with(self.payload)
        self.assertIn('received', response.json()['message'])
        self.notify.assert_called_once_with(self.payload)

    def test_invalid_submissions_never_reach_storage(self):
        for change in [dict(name=' '), dict(email='invalid'), dict(message=' '), dict(message='x'*5001), dict(phone='abc'), dict(is_read=True)]:
            with self.subTest(change=list(change)), patch('app.main.save_contact_message') as save:
                self.assertEqual(self.client.post('/api/contact', json=dict(self.payload, **change)).status_code, 422)
                save.assert_not_called()

    def test_storage_failure_is_not_reported_as_success(self):
        with patch('app.main.save_contact_message', side_effect=ContactStorageError('private error')):
            response = self.client.post('/api/contact', json=self.payload)
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('private error', response.text)
        self.notify.assert_not_called()

    @patch.dict(os.environ, {'SUPABASE_URL': 'https://example.supabase.co', 'SUPABASE_PUBLISHABLE_KEY': 'test-key'})
    def test_insert_uses_public_key_and_no_readback(self):
        response = httpx.Response(201, request=httpx.Request('POST', 'https://example.supabase.co/rest/v1/contact_messages'))
        with patch('app.contact_storage.httpx.post', return_value=response) as post:
            save_contact_message(self.payload)
        post.assert_called_once_with('https://example.supabase.co/rest/v1/contact_messages', headers={'apikey': 'test-key', 'Prefer': 'return=minimal'}, json=self.payload, timeout=15.0)

    @patch.dict(os.environ, {'SUPABASE_URL': 'https://example.supabase.co', 'SUPABASE_PUBLISHABLE_KEY': 'test-key'})
    def test_remote_failures(self):
        for status in [401, 403, 404, 500]:
            response = httpx.Response(status, request=httpx.Request('POST', 'https://example.supabase.co/rest/v1/contact_messages'))
            with self.subTest(status=status), patch('app.contact_storage.httpx.post', return_value=response), self.assertRaises(ContactStorageError):
                save_contact_message(self.payload)
        with patch('app.contact_storage.httpx.post', side_effect=httpx.ConnectTimeout('timeout')), self.assertRaises(ContactStorageError):
            save_contact_message(self.payload)

    @patch.dict(os.environ, {'SUPABASE_URL': '', 'SUPABASE_PUBLISHABLE_KEY': ''})
    def test_missing_configuration_does_not_send(self):
        with patch('app.contact_storage.httpx.post') as post, self.assertRaises(ContactStorageError):
            save_contact_message(self.payload)
        post.assert_not_called()


if __name__ == '__main__':
    unittest.main()
