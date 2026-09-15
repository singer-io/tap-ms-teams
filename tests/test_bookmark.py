from datetime import timedelta
from base import MsTeamsBaseTest
from tap_tester.base_suite_tests.bookmark_test import BookmarkTest


class MsTeamsBookMarkTest(BookmarkTest, MsTeamsBaseTest):
    """Test tap sets a bookmark and respects it for the next sync of a
    stream."""
    bookmark_format = "%Y-%m-%dT%H:%M:%S.%fZ"
    initial_bookmarks = {
        "bookmarks": {
            "conversations": {"last_delivered_date_time": "2024-01-01T00:00:00Z"},
            "conversation_threads": {"last_delivered_date_time": "2024-01-01T00:00:00Z"},
            "conversation_posts": {"last_modified_date_time": "2024-01-01T00:00:00Z"}
        }
    }
    @staticmethod
    def name():
        return "tap_tester_ms_teams_bookmark_test"

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
            # Only 3 records in test tenant; calculate_new_bookmarks() needs >=4
            # (3+ values below the max) to compute a meaningful sync-2 bookmark
            'team_drives',
        })
        return self.expected_stream_names().difference(streams_to_exclude)
