import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
from singer.utils import strptime_to_utc
from tap_ms_teams.streams import (
    TeamDrives,
    ChannelMessages,
    Conversations,
    ConversationThreads,
    ConversationPosts,
    TeamDeviceUsageReport
)


class TestIncrementalStreams(unittest.TestCase):

    def setUp(self):
        """Set up common test fixtures"""
        self.mock_client = MagicMock()
        self.mock_config = {
            'attribution_window': 7,
            'start_date': '2025-01-01T00:00:00Z'
        }
        self.mock_catalog = MagicMock()
        self.mock_state = {
            'bookmarks': {
                'team_drives': {'last_modified_date_time': '2025-01-15T00:00:00Z'},
                'channel_messages': {'last_modified_date_time': '2025-01-15T00:00:00Z'},
                'conversations': {'last_delivered_date_time': '2025-01-15T00:00:00Z'}
            }
        }

    def test_team_drives_bookmark_initialization(self):
        """Test TeamDrives stream has correct incremental properties"""
        stream = TeamDrives(
            client=self.mock_client,
            config=self.mock_config,
            catalog=self.mock_catalog,
            state=self.mock_state
        )

        self.assertEqual(stream.replication_method, 'INCREMENTAL')
        self.assertEqual(stream.replication_key, 'last_modified_date_time')
        self.assertIn('last_modified_date_time', stream.valid_replication_keys)

    def test_channel_messages_bookmark_initialization(self):
        """Test ChannelMessages stream has correct incremental properties"""
        stream = ChannelMessages(
            client=self.mock_client,
            config=self.mock_config,
            catalog=self.mock_catalog,
            state=self.mock_state
        )

        self.assertEqual(stream.replication_method, 'INCREMENTAL')
        self.assertEqual(stream.replication_key, 'last_modified_date_time')
        self.assertIn('last_modified_date_time', stream.valid_replication_keys)

    def test_get_bookmark_with_state(self):
        """Test get_bookmark returns stored state value"""
        stream = TeamDrives(
            client=self.mock_client,
            config=self.mock_config,
            catalog=self.mock_catalog,
            state=self.mock_state
        )

        bookmark = stream.get_bookmark('team_drives', 'last_modified_date_time', '2025-01-01T00:00:00Z')
        self.assertEqual(bookmark, '2025-01-15T00:00:00Z')

    def test_get_bookmark_without_state(self):
        """Test get_bookmark returns default when no state exists"""
        stream = TeamDrives(
            client=self.mock_client,
            config=self.mock_config,
            catalog=self.mock_catalog,
            state={}
        )

        default_date = '2025-01-01T00:00:00Z'
        bookmark = stream.get_bookmark('team_drives', 'last_modified_date_time', default_date)
        self.assertEqual(bookmark, default_date)

    def test_update_bookmark(self):
        """Test update_bookmark updates state correctly"""
        stream = TeamDrives(
            client=self.mock_client,
            config=self.mock_config,
            catalog=self.mock_catalog,
            state={}
        )

        new_bookmark = '2025-01-20T00:00:00Z'
        stream.update_bookmark('team_drives', 'last_modified_date_time', new_bookmark)

        self.assertEqual(stream.state['bookmarks']['team_drives']['last_modified_date_time'], new_bookmark)

    def test_max_from_replication_dates(self):
        """Test max_from_replication_dates returns the maximum date"""
        stream = ChannelMessages(
            client=self.mock_client,
            config=self.mock_config,
            catalog=self.mock_catalog,
            state=self.mock_state
        )

        record = {
            'last_modified_date_time': '2025-01-20T10:00:00Z',
            'created_date_time': '2025-01-15T08:00:00Z',
            'deleted_date_time': '2025-01-18T12:00:00Z'
        }

        max_date = stream.max_from_replication_dates(record)
        expected_date = strptime_to_utc('2025-01-20T10:00:00Z')
        self.assertEqual(max_date, expected_date)

    def test_conversations_replication_key(self):
        """Test Conversations stream uses correct replication key"""
        stream = Conversations(
            client=self.mock_client,
            config=self.mock_config,
            catalog=self.mock_catalog,
            state=self.mock_state
        )

        self.assertEqual(stream.replication_method, 'INCREMENTAL')
        self.assertEqual(stream.replication_key, 'last_delivered_date_time')
        self.assertIn('last_delivered_date_time', stream.valid_replication_keys)

    def test_conversation_threads_replication_key(self):
        """Test ConversationThreads stream uses correct replication key"""
        stream = ConversationThreads(
            client=self.mock_client,
            config=self.mock_config,
            catalog=self.mock_catalog,
            state=self.mock_state
        )

        self.assertEqual(stream.replication_method, 'INCREMENTAL')
        self.assertEqual(stream.replication_key, 'last_delivered_date_time')

    def test_conversation_posts_replication_key(self):
        """Test ConversationPosts stream uses correct replication key"""
        stream = ConversationPosts(
            client=self.mock_client,
            config=self.mock_config,
            catalog=self.mock_catalog,
            state=self.mock_state
        )

        self.assertEqual(stream.replication_method, 'INCREMENTAL')
        self.assertEqual(stream.replication_key, 'last_modified_date_time')
        self.assertIn('last_modified_date_time', stream.valid_replication_keys)

    @patch('tap_ms_teams.streams.now')
    def test_get_absolute_start_end_time_within_window(self, mock_now):
        """Test get_absolute_start_end_time when delta is less than attribution window"""
        mock_now.return_value = datetime(2025, 1, 20, 12, 0, 0)

        stream = TeamDeviceUsageReport(
            client=self.mock_client,
            config=self.mock_config,
            catalog=self.mock_catalog,
            state=self.mock_state
        )

        last_dttm = datetime(2025, 1, 18, 12, 0, 0)
        attribution_window = 7

        start, end = stream.get_absolute_start_end_time(last_dttm, attribution_window)

        expected_start = datetime(2025, 1, 12, 0, 0, 0)
        self.assertEqual(start, expected_start)

    @patch('tap_ms_teams.streams.now')
    def test_get_absolute_start_end_time_exceeds_max(self, mock_now):
        """Test get_absolute_start_end_time when delta exceeds 26 days"""
        mock_now.return_value = datetime(2025, 2, 20, 12, 0, 0)

        stream = TeamDeviceUsageReport(
            client=self.mock_client,
            config=self.mock_config,
            catalog=self.mock_catalog,
            state=self.mock_state
        )

        last_dttm = datetime(2025, 1, 1, 12, 0, 0)
        attribution_window = 7

        start, end = stream.get_absolute_start_end_time(last_dttm, attribution_window)

        expected_start_date = datetime(2025, 1, 24, 0, 0, 0)
        self.assertEqual(start, expected_start_date)

    @patch('tap_ms_teams.streams.now')
    def test_get_absolute_start_end_time_normal_range(self, mock_now):
        """Test get_absolute_start_end_time in normal range"""
        mock_now.return_value = datetime(2025, 1, 20, 12, 0, 0)

        stream = TeamDeviceUsageReport(
            client=self.mock_client,
            config=self.mock_config,
            catalog=self.mock_catalog,
            state=self.mock_state
        )

        last_dttm = datetime(2025, 1, 10, 12, 0, 0)
        attribution_window = 7

        start, end = stream.get_absolute_start_end_time(last_dttm, attribution_window)

        expected_start = datetime(2025, 1, 9, 0, 0, 0)
        self.assertEqual(start, expected_start)

    def test_update_currently_syncing(self):
        """Test update_currently_syncing sets and clears current stream"""
        stream = TeamDrives(
            client=self.mock_client,
            config=self.mock_config,
            catalog=self.mock_catalog,
            state={}
        )

        stream.update_currently_syncing('team_drives')
        self.assertEqual(stream.state.get('currently_syncing'), 'team_drives')

        stream.update_currently_syncing(None)
        self.assertNotIn('currently_syncing', stream.state)

    def test_round_times(self):
        """Test round_times rounds to day boundaries"""
        stream = TeamDrives(
            client=self.mock_client,
            config=self.mock_config,
            catalog=self.mock_catalog,
            state=self.mock_state
        )

        start = datetime(2025, 1, 15, 14, 30, 45)
        end = datetime(2025, 1, 20, 8, 15, 30)

        rounded_start, rounded_end = stream.round_times(start, end)

        self.assertEqual(rounded_start, datetime(2025, 1, 14, 0, 0, 0))
        self.assertEqual(rounded_end, datetime(2025, 1, 21, 0, 0, 0))
