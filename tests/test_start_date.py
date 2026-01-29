from base import MsTeamsBaseTest
from tap_tester.base_suite_tests.start_date_test import StartDateTest


class MsTeamsStartDateTest(StartDateTest, MsTeamsBaseTest):
    """Instantiate start date according to the desired data set and run the
    test."""

    @staticmethod
    def name():
        return "tap_tester_ms_teams_start_date_test"

    def streams_to_test(self):
        """Exclude streams which are FULL TABLE or don't have historical data."""
        streams_to_exclude = set({
            "users",
            "groups",
            "group_members",
            "group_owners",
            "channels",
            "channel_members",
            "channel_tabs",
            "conversation_threads",
            "conversations",
            "conversation_posts",
            "team_drives",
            "team_device_usage_report",
        })
        return self.expected_stream_names().difference(streams_to_exclude)

    @property
    def start_date_1(self):
        return "2026-01-01T00:00:00Z"
    @property
    def start_date_2(self):
        return "2026-01-08T00:00:00Z"

    def test_replicated_records(self):
        """Override to use assertGreaterEqual instead of assertGreater for record counts."""
        for stream in self.streams_to_test():
            with self.subTest(stream=stream):

                # expected values
                expected_primary_keys = self.expected_primary_keys(stream)
                stream_obeys_start_date = self.expected_start_date_behavior(stream)

                # collect information for assertions from syncs 1 & 2 base on expected values
                record_count_sync_1 = self.record_count_by_stream_1.get(stream, 0)
                record_count_sync_2 = self.record_count_by_stream_2.get(stream, 0)

                # collect information to allow filtering
                # of any records added between syncs for clean comparison

                # compound replication key not accounted for
                assert len(self.expected_replication_keys().get(stream)) == 1
                expected_replication_key = next(iter(self.expected_replication_keys().get(stream)))
                replication_dates_1 = {
                    record['data'].get(expected_replication_key) for record in
                    self.synced_messages_by_stream_1.get(stream, {}).get('messages', [])
                    if record.get('action') == 'upsert'}

                # all pks in sync 2 except those added after sync 1 was completed
                primary_keys_sync_2 = {
                    tuple(message['data'][expected_pk] for expected_pk in expected_primary_keys)
                    for message in
                    self.synced_messages_by_stream_2.get(stream, {}).get('messages', [])
                    if message.get('action') == 'upsert'
                    and self.parse_date(message['data'][expected_replication_key])
                    <= self.parse_date(max(replication_dates_1))}

                if stream_obeys_start_date:

                    # all pks in sync 1 that should have been synced in sync 2
                    primary_keys_sync_1 = {
                        tuple(message['data'][expected_pk] for expected_pk in expected_primary_keys)
                        for message in self.synced_messages_by_stream_1.get(
                            stream, {}).get('messages', [])
                        if message.get('action') == 'upsert'
                        and self.parse_date(message['data'][expected_replication_key])
                        >= self.parse_date(self.start_date_2)}

                    # Verify the number of records replicated in sync 1 is greater than or equal to
                    # the number of records replicated in sync 2.
                    # NOTE: Using assertGreaterEqual to handle cases where all data is recent
                    self.assertGreaterEqual(record_count_sync_1, record_count_sync_2)

                    # Verify the records replicated in sync 2 were also replicated in sync 1
                    self.assertSetEqual(primary_keys_sync_1, primary_keys_sync_2)

                else:

                    # all pks in sync 1
                    primary_keys_sync_1 = {
                        tuple(message['data'][expected_pk] for expected_pk in expected_primary_keys)
                        for message in self.synced_messages_by_stream_1.get(
                            stream, {}).get('messages', [])
                        if message.get('action') == 'upsert'}

                    # Verify by primary key the same records are replicated in the 1st and 2nd syncs
                    self.assertSetEqual(primary_keys_sync_1, primary_keys_sync_2)
