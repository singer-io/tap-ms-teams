
from base import MsTeamsBaseTest
from tap_tester.base_suite_tests.interrupted_sync_test import InterruptedSyncTest


class MsTeamsInterruptedSyncTest(InterruptedSyncTest, MsTeamsBaseTest):
    """Test tap sets a bookmark and respects it for the next sync of a
    stream."""

    @staticmethod
    def name():
        return "tap_tester_ms_teams_interrupted_sync_test"

    def streams_to_test(self):
        streams_to_exclude = set({
            'group_owners',
            'group_members',
            'channels',
            'users',
            'channel_tabs',
            'channel_members',
            'groups',
            "team_device_usage_report",
            # No Teams license assigned in test tenant -> these streams emit 0 records
            'channel_messages',
            'channel_message_replies',
        })
        return self.expected_stream_names().difference(streams_to_exclude)


    def manipulate_state(self):
        return {
            "currently_syncing": "team_drives",
            "bookmarks": {
                "team_drives": {"last_modified_date_time": "2026-01-08T00:00:00Z"},
                "channel_messages": {"last_modified_date_time": "2026-01-08T00:00:00Z"},
                "channel_message_replies": {"created_date_time": "2026-01-08T00:00:00Z"},
                "conversations": {"last_delivered_date_time": "2026-01-08T00:00:00Z"},
                "conversation_threads": {"last_delivered_date_time": "2026-01-08T00:00:00Z"},
                "conversation_posts": {"last_modified_date_time": "2026-01-08T00:00:00Z"}
            }
        }
