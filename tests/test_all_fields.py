from base import MsTeamsBaseTest
from tap_tester.base_suite_tests.all_fields_test import AllFieldsTest


class MsTeamsAllFields(AllFieldsTest, MsTeamsBaseTest):
    """Ensure running the tap with all streams and fields selected results in
    the replication of all fields."""

    MISSING_FIELDS = {
        "channel_tabs": {"sort_order_index", "teams_app"}
    }

    @staticmethod
    def name():
        return "tap_tester_ms_teams_all_fields_test"

    def streams_to_test(self):
        streams_to_exclude = set({
            'team_device_usage_report'
        })
        return self.expected_stream_names().difference(streams_to_exclude)
