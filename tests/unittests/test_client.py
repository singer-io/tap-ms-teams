import unittest
from unittest.mock import patch, MagicMock, Mock
from tap_ms_teams.client import MicrosoftGraphClient, Server5xxError, Server42xRateLimitError


default_config = {
    "client_id": "test_client_id",
    "client_secret": "test_client_secret",
    "tenant_id": "test_tenant_id",
    "user_agent": "test_user_agent"
}

class MockResponse:
    def __init__(self, status_code, json_data=None, text="", headers=None):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text
        self.headers = headers or {}
        self.url = "http://test.com/csv"

    def json(self):
        return self._json_data

    def iter_lines(self, chunk_size=1024):
        return iter([b"header1,header2", b"value1,value2"])


class TestMicrosoftGraphClient(unittest.TestCase):

    @patch('tap_ms_teams.client.requests.Session')
    def test_client_initialization(self, mock_session):
        """Test that client initializes correctly with config"""
        client = MicrosoftGraphClient(default_config)

        self.assertEqual(client.config, default_config)
        self.assertIsNone(client.access_token)
        self.assertIsNone(client.login_timer)
        mock_session.assert_called_once()

    @patch('tap_ms_teams.client.threading.Timer')
    @patch('tap_ms_teams.client.requests.Session')
    def test_login_success(self, mock_session, mock_timer):
        """Test successful login and token refresh"""
        client = MicrosoftGraphClient(default_config)

        mock_response = MockResponse(
            200,
            json_data={'access_token': 'test_token_123'}
        )
        mock_session_instance = mock_session.return_value
        mock_session_instance.post.return_value = mock_response

        client.login()

        self.assertEqual(client.access_token, 'test_token_123')
        self.assertEqual(client.client_id, 'test_client_id')
        self.assertEqual(client.client_secret, 'test_client_secret')
        self.assertEqual(client.tenant_id, 'test_tenant_id')
        mock_timer.assert_called_once()

    def test_build_url(self):
        """Test URL building with parameters"""
        url = MicrosoftGraphClient.build_url(
            'https://graph.microsoft.com',
            'v1.0',
            'users',
            {'$top': '100', '$orderby': 'displayName'}
        )

        self.assertIn('https://graph.microsoft.com/v1.0/users', url)
        self.assertIn('%24top=100', url)
        self.assertIn('%24orderby=displayName', url)

    @patch('tap_ms_teams.client.requests.Session')
    def test_get_all_resources_with_pagination(self, mock_session):
        """Test fetching all resources with pagination"""
        client = MicrosoftGraphClient(default_config)
        client.access_token = 'test_token'

        # Mock paginated responses
        response1 = MockResponse(200, json_data={
            'value': [{'id': '1'}, {'id': '2'}],
            '@odata.nextLink': 'https://graph.microsoft.com/v1.0/users?$skip=2'
        })
        response2 = MockResponse(200, json_data={
            'value': [{'id': '3'}]
        })

        mock_session_instance = mock_session.return_value
        mock_session_instance.get.side_effect = [response1, response2]

        result = client.get_all_resources('v1.0', 'users', top=100)

        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]['id'], '1')
        self.assertEqual(result[2]['id'], '3')
        self.assertEqual(mock_session_instance.get.call_count, 2)

    @patch('time.sleep', return_value=None)
    @patch('tap_ms_teams.client.requests.Session')
    def test_make_request_rate_limit_retry(self, mock_session, mock_sleep):
        """Test that rate limit triggers retry with proper wait"""
        client = MicrosoftGraphClient(default_config)
        client.access_token = 'test_token'

        # Mock rate limit response that will be returned every time
        rate_limit_response = MockResponse(
            429,
            headers={'Retry-After': '60'}
        )

        mock_session_instance = mock_session.return_value
        # Return rate limit response for all attempts to trigger max retries
        mock_session_instance.get.return_value = rate_limit_response

        with self.assertRaises(Server42xRateLimitError):
            client.make_request('GET', url='https://graph.microsoft.com/v1.0/users')

        # Verify sleep was called with the retry-after value
        mock_sleep.assert_called_with(60)

    @patch('tap_ms_teams.client.requests.Session')
    def test_make_request_401_triggers_relogin(self, mock_session):
        """Test that 401 status triggers login attempt"""
        client = MicrosoftGraphClient(default_config)
        client.access_token = 'expired_token'
        client.login = MagicMock()

        unauthorized_response = MockResponse(401)

        mock_session_instance = mock_session.return_value
        mock_session_instance.get.return_value = unauthorized_response

        try:
            client.make_request('GET', url='https://graph.microsoft.com/v1.0/users')
        except RuntimeError:
            pass

        client.login.assert_called_once()

    @patch('tap_ms_teams.client.requests.Session')
    def test_make_request_500_raises_server_error(self, mock_session):
        """Test that 500 status raises Server5xxError"""
        client = MicrosoftGraphClient(default_config)
        client.access_token = 'test_token'

        server_error_response = MockResponse(500)

        mock_session_instance = mock_session.return_value
        mock_session_instance.get.return_value = server_error_response

        with self.assertRaises(Server5xxError):
            client.make_request('GET', url='https://graph.microsoft.com/v1.0/users')

    @patch('tap_ms_teams.client.requests.Session')
    def test_make_request_post_method(self, mock_session):
        """Test POST request with data"""
        client = MicrosoftGraphClient(default_config)
        client.access_token = 'test_token'

        success_response = MockResponse(200, json_data={'access_token': 'new_token'})

        mock_session_instance = mock_session.return_value
        mock_session_instance.post.return_value = success_response

        result = client.make_request(
            'POST',
            url='https://login.microsoftonline.com/oauth2/token',
            data={'grant_type': 'client_credentials'}
        )

        self.assertEqual(result['access_token'], 'new_token')
        mock_session_instance.post.assert_called_once()

    def test_make_request_unsupported_method(self):
        """Test that unsupported HTTP method raises exception"""
        client = MicrosoftGraphClient(default_config)
        client.access_token = 'test_token'

        with self.assertRaises(Exception) as context:
            client.make_request('DELETE', url='https://graph.microsoft.com/v1.0/users/1')

        self.assertIn('Unsupported HTTP method', str(context.exception))

    @patch('tap_ms_teams.client.requests.get')
    def test_stream_csv(self, mock_get):
        """Test CSV streaming functionality"""
        client = MicrosoftGraphClient(default_config)

        mock_response = Mock()
        mock_response.iter_lines.return_value = [
            b'header1,header2',
            b'value1,value2',
            b'value3,value4',
            b'value5,value6'
        ]
        mock_get.return_value.__enter__.return_value = mock_response

        batches = list(client.stream_csv('http://test.com/csv', batch_size=2))

        # CSV reader consumes header, so we get 3 data rows in 2 batches
        self.assertEqual(len(batches), 2)
        self.assertEqual(len(batches[0]), 2)
        self.assertEqual(len(batches[1]), 1)

    @patch('time.sleep', return_value=None)
    @patch('tap_ms_teams.client.requests.Session')
    def test_get_report_with_rate_limit(self, mock_session, mock_sleep):
        """Test get_report handles rate limiting"""
        client = MicrosoftGraphClient(default_config)
        client.access_token = 'test_token'
        client.stream_csv = MagicMock(return_value=[])

        rate_limit_response = MockResponse(429, headers={'Retry-After': '30'})

        mock_session_instance = mock_session.return_value
        mock_session_instance.get.return_value = rate_limit_response

        with self.assertRaises(Server42xRateLimitError):
            list(client.get_report('v1.0', 'reports/getTeamsDeviceUsageUserDetail'))

        mock_sleep.assert_called_with(30)
