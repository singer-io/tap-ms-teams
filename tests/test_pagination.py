from tap_tester.base_suite_tests.pagination_test import PaginationTest
from base import MsTeamsBaseTest

class MsTeamsPaginationTest(PaginationTest, MsTeamsBaseTest):
    """
    Ensure tap can replicate multiple pages of data for streams that use pagination.
    """

    @staticmethod
    def name():
        return "tap_tester_ms_teams_pagination_test"

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
