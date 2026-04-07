import unittest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from tap_ms_teams import sync, discover
from tap_ms_teams.streams import Users, Groups, TeamDrives


default_config = {
    "client_id": "test_client_id",
    "client_secret": "test_client_secret",
    "tenant_id": "test_tenant_id",
    "user_agent": "test_user_agent",
    "start_date": "2025-01-01T00:00:00Z"
}


class TestSync(unittest.TestCase):

    @patch('tap_ms_teams.generate_catalog')
    @patch('json.dump')
    def test_discover_generates_catalog(self, mock_json_dump, mock_generate_catalog):
        """Test that discover generates and outputs catalog"""
        mock_client = MagicMock()
        mock_catalog = {'streams': []}
        mock_generate_catalog.return_value = mock_catalog

        discover(mock_client)

        mock_generate_catalog.assert_called_once()
        mock_json_dump.assert_called_once()

    @patch('singer.Transformer')
    @patch('singer.write_record')
    @patch('singer.write_state')
    @patch('singer.metrics.record_counter')
    def test_sync_full_table_stream(self, mock_counter, mock_write_state, mock_write_record, mock_transformer):
        """Test syncing a FULL_TABLE stream (Users)"""
        mock_client = MagicMock()

        mock_catalog = MagicMock()
        catalog_entry = MagicMock()
        catalog_entry.stream = 'users'
        catalog_entry.schema.to_dict.return_value = {'properties': {}}
        catalog_entry.metadata = []
        mock_catalog.get_selected_streams.return_value = [catalog_entry]

        state = {}

        mock_counter_instance = MagicMock()
        mock_counter.return_value.__enter__.return_value = mock_counter_instance

        mock_transformer_instance = MagicMock()
        mock_transformer_instance.transform.return_value = {'id': '123', 'display_name': 'Test User'}
        mock_transformer.return_value.__enter__.return_value = mock_transformer_instance


        with patch.object(Users, 'sync', return_value=[[{'id': '123', 'display_name': 'Test User'}]]):
            with patch.object(Users, 'write_schema'):
                with patch.object(Users, 'write_state'):
                    with patch.object(Users, 'update_currently_syncing'):
                        sync(mock_client, default_config, mock_catalog, state)

        mock_write_record.assert_called()

    @patch('singer.Transformer')
    @patch('singer.write_record')
    @patch('singer.write_state')
    @patch('singer.metrics.record_counter')
    @patch('singer.utils.strptime_to_utc')
    @patch('singer.utils.strftime')
    def test_sync_incremental_stream(self, mock_strftime, mock_strptime, mock_counter,
                                     mock_write_state, mock_write_record, mock_transformer):
        """Test syncing an INCREMENTAL stream (TeamDrives)"""
        mock_client = MagicMock()

        mock_catalog = MagicMock()
        catalog_entry = MagicMock()
        catalog_entry.stream = 'team_drives'
        catalog_entry.schema.to_dict.return_value = {'properties': {}}
        catalog_entry.metadata = []
        mock_catalog.get_selected_streams.return_value = [catalog_entry]

        state = {'bookmarks': {'team_drives': '2025-01-10T00:00:00Z'}}

        mock_strptime.return_value = datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        mock_strftime.return_value = '2025-01-15T00:00:00Z'

        mock_counter_instance = MagicMock()
        mock_counter.return_value.__enter__.return_value = mock_counter_instance

        mock_transformer_instance = MagicMock()
        mock_transformer_instance.transform.return_value = {
            'id': '456',
            'last_modified_date_time': '2025-01-15T00:00:00Z'
        }
        mock_transformer.return_value.__enter__.return_value = mock_transformer_instance

        with patch.object(TeamDrives, 'sync', return_value=[[{
            'id': '456',
            'last_modified_date_time': '2025-01-15T00:00:00Z'
        }]]):
            with patch.object(TeamDrives, 'write_schema'):
                with patch.object(TeamDrives, 'write_state'):
                    with patch.object(TeamDrives, 'update_currently_syncing'):
                        with patch.object(TeamDrives, 'update_bookmark'):
                            with patch.object(TeamDrives, 'get_bookmark', return_value='2025-01-10T00:00:00Z'):
                                with patch.object(TeamDrives, 'max_from_replication_dates', return_value=datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc)):
                                    sync(mock_client, default_config, mock_catalog, state)

        # Verify record was written
        mock_write_record.assert_called()

    @patch('singer.Transformer')
    @patch('singer.write_record')
    @patch('singer.write_state')
    @patch('singer.metrics.record_counter')
    def test_sync_multiple_streams(self, mock_counter, mock_write_state, mock_write_record, mock_transformer):
        """Test syncing multiple streams"""
        mock_client = MagicMock()

        mock_catalog = MagicMock()

        users_entry = MagicMock()
        users_entry.stream = 'users'
        users_entry.schema.to_dict.return_value = {'properties': {}}
        users_entry.metadata = []

        groups_entry = MagicMock()
        groups_entry.stream = 'groups'
        groups_entry.schema.to_dict.return_value = {'properties': {}}
        groups_entry.metadata = []

        mock_catalog.get_selected_streams.return_value = [users_entry, groups_entry]

        state = {}

        mock_counter_instance = MagicMock()
        mock_counter.return_value.__enter__.return_value = mock_counter_instance

        mock_transformer_instance = MagicMock()
        mock_transformer_instance.transform.return_value = {'id': '123'}
        mock_transformer.return_value.__enter__.return_value = mock_transformer_instance

        with patch.object(Users, 'sync', return_value=[[{'id': '123'}]]):
            with patch.object(Groups, 'sync', return_value=[[{'id': '456'}]]):
                with patch.object(Users, 'write_schema'):
                    with patch.object(Groups, 'write_schema'):
                        with patch.object(Users, 'write_state'):
                            with patch.object(Groups, 'write_state'):
                                with patch.object(Users, 'update_currently_syncing'):
                                    with patch.object(Groups, 'update_currently_syncing'):
                                        sync(mock_client, default_config, mock_catalog, state)

        self.assertEqual(mock_write_record.call_count, 2)

    @patch('singer.Transformer')
    @patch('singer.write_state')
    @patch('singer.metrics.record_counter')
    def test_sync_updates_currently_syncing(self, mock_counter, mock_write_state, mock_transformer):
        """Test that currently_syncing is updated during sync"""
        mock_client = MagicMock()

        mock_catalog = MagicMock()
        catalog_entry = MagicMock()
        catalog_entry.stream = 'users'
        catalog_entry.schema.to_dict.return_value = {'properties': {}}
        catalog_entry.metadata = []
        mock_catalog.get_selected_streams.return_value = [catalog_entry]

        state = {}

        mock_counter_instance = MagicMock()
        mock_counter.return_value.__enter__.return_value = mock_counter_instance

        mock_transformer_instance = MagicMock()
        mock_transformer.return_value.__enter__.return_value = mock_transformer_instance

        with patch.object(Users, 'sync', return_value=[[]]):
            with patch.object(Users, 'write_schema'):
                with patch.object(Users, 'write_state'):
                    with patch.object(Users, 'update_currently_syncing') as mock_update:
                        sync(mock_client, default_config, mock_catalog, state)

                        self.assertTrue(mock_update.called)
                        calls = mock_update.call_args_list
                        self.assertEqual(calls[0][0][0], 'users')
                        self.assertEqual(calls[1][0][0], None)

    @patch('singer.Transformer')
    @patch('singer.write_record')
    @patch('singer.write_state')
    @patch('singer.metrics.record_counter')
    @patch('singer.utils.strptime_to_utc')
    def test_sync_incremental_filters_old_records(self, mock_strptime, mock_counter,
                                                   mock_write_state, mock_write_record, mock_transformer):
        """Test that incremental sync filters records older than bookmark"""
        mock_client = MagicMock()

        mock_catalog = MagicMock()
        catalog_entry = MagicMock()
        catalog_entry.stream = 'team_drives'
        catalog_entry.schema.to_dict.return_value = {'properties': {}}
        catalog_entry.metadata = []
        mock_catalog.get_selected_streams.return_value = [catalog_entry]

        state = {'bookmarks': {'team_drives': '2025-01-15T00:00:00Z'}}

        bookmark_time = datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        old_time = datetime(2025, 1, 10, 0, 0, 0, tzinfo=timezone.utc)
        new_time = datetime(2025, 1, 20, 0, 0, 0, tzinfo=timezone.utc)

        def strptime_side_effect(date_str):
            if '2025-01-15' in date_str:
                return bookmark_time
            elif '2025-01-10' in date_str:
                return old_time
            else:
                return new_time

        mock_strptime.side_effect = strptime_side_effect

        mock_counter_instance = MagicMock()
        mock_counter.return_value.__enter__.return_value = mock_counter_instance

        mock_transformer_instance = MagicMock()
        mock_transformer_instance.transform.return_value = {'id': '456'}
        mock_transformer.return_value.__enter__.return_value = mock_transformer_instance

        old_record = {'id': '123', 'last_modified_date_time': '2025-01-10T00:00:00Z'}
        new_record = {'id': '456', 'last_modified_date_time': '2025-01-20T00:00:00Z'}

        with patch.object(TeamDrives, 'sync', return_value=[[old_record, new_record]]):
            with patch.object(TeamDrives, 'write_schema'):
                with patch.object(TeamDrives, 'write_state'):
                    with patch.object(TeamDrives, 'update_currently_syncing'):
                        with patch.object(TeamDrives, 'update_bookmark'):
                            with patch.object(TeamDrives, 'get_bookmark', return_value='2025-01-15T00:00:00Z'):
                                def max_replication_side_effect(record):
                                    if record['id'] == '123':
                                        return old_time
                                    return new_time

                                with patch.object(TeamDrives, 'max_from_replication_dates', side_effect=max_replication_side_effect):
                                    sync(mock_client, default_config, mock_catalog, state)

        self.assertEqual(mock_write_record.call_count, 1)

    @patch('singer.Transformer')
    @patch('singer.write_state')
    @patch('singer.metrics.record_counter')
    def test_sync_writes_schema_for_each_stream(self, mock_counter, mock_write_state, mock_transformer):
        """Test that schema is written for each stream"""
        mock_client = MagicMock()

        mock_catalog = MagicMock()
        catalog_entry = MagicMock()
        catalog_entry.stream = 'users'
        catalog_entry.schema.to_dict.return_value = {'properties': {}}
        catalog_entry.metadata = []
        mock_catalog.get_selected_streams.return_value = [catalog_entry]

        state = {}

        mock_counter_instance = MagicMock()
        mock_counter.return_value.__enter__.return_value = mock_counter_instance

        mock_transformer_instance = MagicMock()
        mock_transformer.return_value.__enter__.return_value = mock_transformer_instance

        with patch.object(Users, 'sync', return_value=[[]]):
            with patch.object(Users, 'write_schema') as mock_write_schema:
                with patch.object(Users, 'write_state'):
                    with patch.object(Users, 'update_currently_syncing'):
                        sync(mock_client, default_config, mock_catalog, state)

                        mock_write_schema.assert_called_once()

    @patch('singer.Transformer')
    @patch('singer.write_state')
    @patch('singer.metrics.record_counter')
    @patch('singer.utils.strptime_to_utc')
    @patch('singer.utils.strftime')
    def test_sync_updates_bookmark_for_incremental(self, mock_strftime, mock_strptime,
                                                    mock_counter, mock_write_state, mock_transformer):
        """Test that bookmark is updated for incremental streams"""
        mock_client = MagicMock()

        mock_catalog = MagicMock()
        catalog_entry = MagicMock()
        catalog_entry.stream = 'team_drives'
        catalog_entry.schema.to_dict.return_value = {'properties': {}}
        catalog_entry.metadata = []
        mock_catalog.get_selected_streams.return_value = [catalog_entry]

        state = {'bookmarks': {'team_drives': '2025-01-10T00:00:00Z'}}

        mock_strptime.return_value = datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        mock_strftime.return_value = '2025-01-15T00:00:00Z'

        mock_counter_instance = MagicMock()
        mock_counter.return_value.__enter__.return_value = mock_counter_instance

        mock_transformer_instance = MagicMock()
        mock_transformer.return_value.__enter__.return_value = mock_transformer_instance

        with patch.object(TeamDrives, 'sync', return_value=[[{
            'id': '456',
            'last_modified_date_time': '2025-01-15T00:00:00Z'
        }]]):
            with patch.object(TeamDrives, 'write_schema'):
                with patch.object(TeamDrives, 'write_state'):
                    with patch.object(TeamDrives, 'update_currently_syncing'):
                        with patch.object(TeamDrives, 'update_bookmark') as mock_update_bookmark:
                            with patch.object(TeamDrives, 'get_bookmark', return_value='2025-01-10T00:00:00Z'):
                                with patch.object(TeamDrives, 'max_from_replication_dates', return_value=datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc)):
                                    sync(mock_client, default_config, mock_catalog, state)

                                    mock_update_bookmark.assert_called()
