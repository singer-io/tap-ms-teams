import os
from tap_tester.base_suite_tests.base_case import BaseCase


class MsTeamsBaseTest(BaseCase):
    """Setup expectations for test sub classes.

    Metadata describing streams. A bunch of shared methods that are used
    in tap-tester tests. Shared tap-specific methods (as needed).
    """
    start_date = "2025-01-01T00:00:00Z"

    @staticmethod
    def tap_name():
        """The name of the tap."""
        return "tap-ms-teams"

    @staticmethod
    def get_type():
        """The name of the tap."""
        return "platform.ms-teams"

    @classmethod
    def expected_metadata(cls):
        """The expected streams and metadata about the streams."""
        return {
            "users": {
                cls.PRIMARY_KEYS: {"id"},
                cls.REPLICATION_METHOD: cls.FULL_TABLE,
                cls.REPLICATION_KEYS: set(),
                cls.OBEYS_START_DATE: False,
                cls.API_LIMIT: 100
            },
            "groups": {
                cls.PRIMARY_KEYS: {"id"},
                cls.REPLICATION_METHOD: cls.FULL_TABLE,
                cls.REPLICATION_KEYS: set(),
                cls.OBEYS_START_DATE: False,
                cls.API_LIMIT: 100
            },
            "group_members": {
                cls.PRIMARY_KEYS: {"id"},
                cls.REPLICATION_METHOD: cls.FULL_TABLE,
                cls.REPLICATION_KEYS: set(),
                cls.OBEYS_START_DATE: False,
                cls.API_LIMIT: 100
            },
            "group_owners": {
                cls.PRIMARY_KEYS: {"id"},
                cls.REPLICATION_METHOD: cls.FULL_TABLE,
                cls.REPLICATION_KEYS: set(),
                cls.OBEYS_START_DATE: False,
                cls.API_LIMIT: 100
            },
            "team_drives": {
                cls.PRIMARY_KEYS: {"id"},
                cls.REPLICATION_METHOD: cls.INCREMENTAL,
                cls.REPLICATION_KEYS: {"last_modified_date_time"},
                cls.OBEYS_START_DATE: True,
                cls.API_LIMIT: 100
            },
            "channels": {
                cls.PRIMARY_KEYS: {"id"},
                cls.REPLICATION_METHOD: cls.FULL_TABLE,
                cls.REPLICATION_KEYS: set(),
                cls.OBEYS_START_DATE: False,
                cls.API_LIMIT: 100
            },
            "channel_members": {
                cls.PRIMARY_KEYS: {"id"},
                cls.REPLICATION_METHOD: cls.FULL_TABLE,
                cls.REPLICATION_KEYS: set(),
                cls.OBEYS_START_DATE: False,
                cls.API_LIMIT: 100
            },
            "channel_tabs": {
                cls.PRIMARY_KEYS: {"id"},
                cls.REPLICATION_METHOD: cls.FULL_TABLE,
                cls.REPLICATION_KEYS: set(),
                cls.OBEYS_START_DATE: False,
                cls.API_LIMIT: 100
            },
            "channel_messages": {
                cls.PRIMARY_KEYS: {"id"},
                cls.REPLICATION_METHOD: cls.INCREMENTAL,
                cls.REPLICATION_KEYS: {"last_modified_date_time", "created_date_time", "deleted_date_time"},
                cls.OBEYS_START_DATE: True,
                cls.API_LIMIT: 100
            },
            "channel_message_replies": {
                cls.PRIMARY_KEYS: {"id"},
                cls.REPLICATION_METHOD: cls.INCREMENTAL,
                cls.REPLICATION_KEYS: {"created_date_time", "last_modified_date_time", "deleted_date_time"},
                cls.OBEYS_START_DATE: True,
                cls.API_LIMIT: 100
            },
            "conversations": {
                cls.PRIMARY_KEYS: {"id"},
                cls.REPLICATION_METHOD: cls.INCREMENTAL,
                cls.REPLICATION_KEYS: {"last_delivered_date_time"},
                cls.OBEYS_START_DATE: True,
                cls.API_LIMIT: 100
            },
            "conversation_threads": {
                cls.PRIMARY_KEYS: {"id"},
                cls.REPLICATION_METHOD: cls.INCREMENTAL,
                cls.REPLICATION_KEYS: {"last_delivered_date_time"},
                cls.OBEYS_START_DATE: True,
                cls.API_LIMIT: 100
            },
            "conversation_posts": {
                cls.PRIMARY_KEYS: {"id", "change_key"},
                cls.REPLICATION_METHOD: cls.INCREMENTAL,
                cls.REPLICATION_KEYS: {"last_modified_date_time", "received_date_time"},
                cls.OBEYS_START_DATE: True,
                cls.API_LIMIT: 100
            },
            "team_device_usage_report": {
                cls.PRIMARY_KEYS: {"user_principal_name", "report_refresh_date"},
                cls.REPLICATION_METHOD: cls.INCREMENTAL,
                cls.REPLICATION_KEYS: {"report_refresh_date"},
                cls.OBEYS_START_DATE: True,
                cls.API_LIMIT: 100
            }
        }

    @staticmethod
    def get_credentials():
        """Authentication information for the test account."""
        credentials_dict = {}
        creds = {
            'client_id': 'TAP_MS_TEAMS_CLIENT_ID',
            'client_secret': 'TAP_MS_TEAMS_CLIENT_SECRET',
            'tenant_id': 'TAP_MS_TEAMS_TENANT_ID'
        }

        for cred in creds:
            credentials_dict[cred] = os.getenv(creds[cred])

        return credentials_dict

    def get_properties(self, original: bool = True):
        """Configuration of properties required for the tap."""
        return_value = {
            "start_date": "2025-01-01T00:00:00Z",
            "user_agent": "tap-ms-teams-test"
        }
        if original:
            return return_value

        return_value["start_date"] = self.start_date
        return return_value
