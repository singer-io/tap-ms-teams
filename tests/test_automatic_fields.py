"""Test that with no fields selected for a stream automatic fields are still
replicated."""
from base import MsTeamsBaseTest
from tap_tester.base_suite_tests.automatic_fields_test import MinimumSelectionTest


class MsTeamsAutomaticFields(MinimumSelectionTest, MsTeamsBaseTest):
    """Test that with no fields selected for a stream automatic fields are
    still replicated."""

    @staticmethod
    def name():
        return "tap_tester_ms_teams_automatic_fields_test"

    def streams_to_test(self):
        streams_to_exclude = set({
            'team_device_usage_report',
            # No Teams license assigned in test tenant -> these streams emit 0 records
            'channels',
            'channel_members',
            'channel_tabs',
            'channel_messages',
            'channel_message_replies',
        })
        return self.expected_stream_names().difference(streams_to_exclude)
