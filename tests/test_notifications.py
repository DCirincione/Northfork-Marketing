import os
import unittest
from unittest.mock import patch
import httpx
from fastapi.testclient import TestClient
from app.main import app
from app.notifications import notify_contact_message


@patch.dict(os.environ, {'NTFY_SERVER': 'https://ntfy.sh', 'NTFY_TOPIC': 'test-nofo-topic', 'NTFY_TOKEN': ''})
class NotificationTests(unittest.TestCase):
    def setUp(self):
        self.contact = {'name': 'Jane Smith', 'email': 'jane@example.com', 'phone': '', 'message': 'Private message text'}

    def test_success_payload_contains_requested_contact_fields(self):
        response = httpx.Response(200, request=httpx.Request('POST', 'https://ntfy.sh'))
        with patch('app.notifications.httpx.post', return_value=response) as post:
            self.assertTrue(notify_contact_message(self.contact))
        args = post.call_args.kwargs
        self.assertEqual(args['json']['topic'], 'test-nofo-topic')
        self.assertEqual(set(args['json']), {'topic', 'title', 'message', 'tags'})
        self.assertEqual(args['timeout'], 5.0)
        self.assertEqual(args['json']['title'], 'New Contact Inquiry')
        self.assertEqual(args['json']['message'], 'Name: Jane Smith\nEmail: jane@example.com')
        self.assertNotIn('Private message text', args['json']['message'])

    def test_failed_notification_preserves_successful_contact_submission(self):
        with patch('app.main.save_contact_message') as save, patch('app.notifications.httpx.post', side_effect=httpx.ConnectTimeout('timeout')):
            response = TestClient(app).post('/api/contact', json={'name': 'Test', 'email': 'test@example.com', 'phone': '', 'message': 'Hello'})
        self.assertEqual(response.status_code, 201)
        save.assert_called_once()

    def test_bad_configuration_does_not_publish(self):
        for value in ['', 'topic/invalid']:
            with patch.dict(os.environ, {'NTFY_TOPIC': value}), patch('app.notifications.httpx.post') as post:
                self.assertFalse(notify_contact_message(self.contact))
                post.assert_not_called()

    def test_http_failure(self):
        response = httpx.Response(403, request=httpx.Request('POST', 'https://ntfy.sh'))
        with patch('app.notifications.httpx.post', return_value=response):
            self.assertFalse(notify_contact_message(self.contact))

    def test_token_authentication(self):
        response = httpx.Response(200, request=httpx.Request('POST', 'https://ntfy.sh'))
        with patch.dict(os.environ, {'NTFY_TOKEN': 'test-token'}), patch('app.notifications.httpx.post', return_value=response) as post:
            self.assertTrue(notify_contact_message(self.contact))
        self.assertEqual(post.call_args.kwargs['headers'], {'Authorization': 'Bearer test-token'})

    def test_phone_is_included_when_provided(self):
        self.contact['phone'] = '(631) 555-0100'
        response = httpx.Response(200, request=httpx.Request('POST', 'https://ntfy.sh'))
        with patch('app.notifications.httpx.post', return_value=response) as post:
            self.assertTrue(notify_contact_message(self.contact))
        self.assertEqual(post.call_args.kwargs['json']['message'], 'Name: Jane Smith\nEmail: jane@example.com\nPhone: (631) 555-0100')
