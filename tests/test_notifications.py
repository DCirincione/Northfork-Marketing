import os
import unittest
from unittest.mock import patch
import httpx
from fastapi.testclient import TestClient
from app.main import app
from app.notifications import notify_contact_message


@patch.dict(os.environ, {'NTFY_SERVER': 'https://ntfy.sh', 'NTFY_TOPIC': 'test-nofo-topic', 'NTFY_TOKEN': ''})
class NotificationTests(unittest.TestCase):
    def test_success_payload_contains_no_contact_information(self):
        response = httpx.Response(200, request=httpx.Request('POST', 'https://ntfy.sh'))
        with patch('app.notifications.httpx.post', return_value=response) as post:
            self.assertTrue(notify_contact_message())
        args = post.call_args.kwargs
        self.assertEqual(args['json']['topic'], 'test-nofo-topic')
        self.assertEqual(set(args['json']), {'topic', 'title', 'message', 'tags'})
        self.assertEqual(args['timeout'], 5.0)

    def test_failed_notification_preserves_successful_contact_submission(self):
        with patch('app.main.save_contact_message') as save, patch('app.notifications.httpx.post', side_effect=httpx.ConnectTimeout('timeout')):
            response = TestClient(app).post('/api/contact', json={'name': 'Test', 'email': 'test@example.com', 'phone': '', 'message': 'Hello'})
        self.assertEqual(response.status_code, 201)
        save.assert_called_once()

    def test_bad_configuration_does_not_publish(self):
        for value in ['', 'topic/invalid']:
            with patch.dict(os.environ, {'NTFY_TOPIC': value}), patch('app.notifications.httpx.post') as post:
                self.assertFalse(notify_contact_message())
                post.assert_not_called()

    def test_http_failure(self):
        response = httpx.Response(403, request=httpx.Request('POST', 'https://ntfy.sh'))
        with patch('app.notifications.httpx.post', return_value=response):
            self.assertFalse(notify_contact_message())

    def test_token_authentication(self):
        response = httpx.Response(200, request=httpx.Request('POST', 'https://ntfy.sh'))
        with patch.dict(os.environ, {'NTFY_TOKEN': 'test-token'}), patch('app.notifications.httpx.post', return_value=response) as post:
            self.assertTrue(notify_contact_message())
        self.assertEqual(post.call_args.kwargs['headers'], {'Authorization': 'Bearer test-token'})
