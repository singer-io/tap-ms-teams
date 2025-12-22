
from base import MsTeamsBaseTest
from tap_tester.base_suite_tests.interrupted_sync_test import InterruptedSyncTest


class MsTeamsInterruptedSyncTest(InterruptedSyncTest, MsTeamsBaseTest):
    """Test tap sets a bookmark and respects it for the next sync of a
    stream."""

    @staticmethod
    def name():
        return "tap_tester_ms_teams_interrupted_sync_test"

    def streams_to_test(self):
        return self.expected_stream_names()


    def manipulate_state(self):
        return {
            "currently_syncing": "team_drives",
            "bookmarks": {
                "team_drives": {"last_modified_date_time": "2024-01-01T00:00:00Z"},
                "channel_messages": {"last_modified_date_time": "2024-01-01T00:00:00Z"},
                "channel_message_replies": {"created_date_time": "2024-01-01T00:00:00Z"},
                "conversations": {"last_delivered_date_time": "2024-01-01T00:00:00Z"},
                "conversation_threads": {"last_delivered_date_time": "2024-01-01T00:00:00Z"},
                "conversation_posts": {"last_modified_date_time": "2024-01-01T00:00:00Z"},
                "team_device_usage_report": {"report_refresh_date": "2024-01-01T00:00:00Z"},
            }
        }

