import os
from datetime import timedelta

import humps
import singer
import singer.metrics
from singer.utils import now, strptime_to_utc
from tap_ms_teams.client import GraphVersion
from tap_ms_teams.transform import transform

LOGGER = singer.get_logger()
TOP_API_PARAM_DEFAULT = 100


class GraphStream:
    # pylint: disable=too-many-instance-attributes,no-member
    def __init__(self, client=None, config=None, catalog=None, state=None):
        self.client = client
        self.config = config
        self.catalog = catalog
        self.state = state
        self.top = TOP_API_PARAM_DEFAULT

    @staticmethod
    def get_abs_path(path):
        return os.path.join(os.path.dirname(os.path.realpath(__file__)), path)

    def load_schema(self):
        schema_path = self.get_abs_path('schemas')
        # pylint: disable=no-member
        return singer.utils.load_json('{}/{}.json'.format(
            schema_path, self.name))

    def write_schema(self):
        schema = self.load_schema()
        # pylint: disable=no-member
        return singer.write_schema(stream_name=self.name,
                                   schema=schema,
                                   key_properties=self.key_properties)

    def write_state(self):
        return singer.write_state(self.state)

    def update_bookmark(self, stream, value):
        if 'bookmarks' not in self.state:
            self.state['bookmarks'] = {}
        self.state['bookmarks'][stream] = value
        LOGGER.info('Stream: %s - Write state, bookmark value: %s', stream, value)
        self.write_state()

    def get_bookmark(self, stream, default):
        # default only populated on initial sync
        if (self.state is None) or ('bookmarks' not in self.state):
            return default
        return self.state.get('bookmarks', {}).get(stream, default)

    # Currently syncing sets the stream currently being delivered in the state.
    # If the integration is interrupted, this state property is used to identify
    #  the starting point to continue from.
    # Reference: https://github.com/singer-io/singer-python/blob/master/singer/bookmarks.py#L41-L46
    def update_currently_syncing(self, stream_name):
        if (stream_name is None) and ('currently_syncing' in self.state):
            del self.state['currently_syncing']
        else:
            singer.set_currently_syncing(self.state, stream_name)
        singer.write_state(self.state)
        LOGGER.info('Stream: %s - Currently Syncing', stream_name)

    # Returns max key and date time for all replication key data in record
    def max_from_replication_dates(self, record):
        date_times = {
            dt: strptime_to_utc(record[dt])
            for dt in self.valid_replication_keys if record[dt] is not None
        }
        max_key = max(date_times)
        return date_times[max_key]

    def remove_hours_local(self, dttm): # pylint: disable = no-self-use
        new_dttm = dttm.replace(hour=0, minute=0, second=0, microsecond=0)
        return new_dttm

    # Round time based to day
    def round_times(self, start=None, end=None):
        start_rounded = None
        end_rounded = None
        # Round min_start, max_end to hours or dates
        start_rounded = self.remove_hours_local(start) - timedelta(days=1)
        end_rounded = self.remove_hours_local(end) + timedelta(days=1)
        return start_rounded, end_rounded

    # Determine absolute start and end times w/ attribution_window constraint
    # abs_start/end and window_start/end must be rounded to nearest hour or day (granularity)
    # Graph API enforces max history of 28 days
    def get_absolute_start_end_time(self, last_dttm, attribution_window):
        now_dttm = now()
        delta_days = (now_dttm - last_dttm).days
        if delta_days < attribution_window:
            start = now_dttm - timedelta(days=attribution_window)
        # 28 days NOT including current
        elif delta_days > 26:
            start = now_dttm - timedelta(26)
            LOGGER.info('Start date exceeds max. Setting start date to %s', start)
        else:
            start = last_dttm

        abs_start, abs_end = self.round_times(start, now_dttm)
        return abs_start, abs_end

    # pylint: disable=unused-argument
    def sync(self, client, startdate=None):
        resources = client.get_all_resources(self.version,
                                             self.endpoint,
                                             top=self.top,
                                             orderby=self.orderby)

        yield humps.decamelize(resources)


class Users(GraphStream):
    name = 'users'
    version = GraphVersion.V1.value
    key_properties = ['id']
    replication_method = 'FULL_TABLE'
    replication_key = None
    endpoint = 'users'
    valid_replication_keys = []
    date_fields = []
    orderby = 'displayName'


class Groups(GraphStream):
    name = 'groups'
    version = GraphVersion.BETA.value
    key_properties = ['id']
    replication_method = 'FULL_TABLE'
    replication_key = None
    endpoint = 'groups'
    valid_replication_keys = []
    date_fields = []
    orderby = None

    # Get all groups with filter for teams with resourceProvisioningOptions
    # Ensures we get only Team groups
    # See, https://docs.microsoft.com/en-us/graph/known-issues#missing-teams-in-list-all-teams
    def get_all_groups(self, client):
        return client.get_all_resources(
            self.version,
            Groups.endpoint,
            top=self.top,
            filter_param="resourceProvisioningOptions/Any(x:x eq 'Team')")

    def sync(self, client, startdate=None):
        yield humps.decamelize(self.get_all_groups(client))


class GroupMembers(GraphStream):
    name = 'group_members'
    version = GraphVersion.V1.value
    key_properties = ['id']
    replication_method = 'FULL_TABLE'
    replication_key = None
    endpoint = 'groups/{group_id}/members'
    valid_replication_keys = []
    date_fields = []
    orderby = 'displayName'

    def sync(self, client, startdate=None):
        owners_result = []
        for group in Groups().get_all_groups(client):
            resources = client.get_all_resources(
                self.version, self.endpoint.format(group_id=group.get('id')))

            # Inject group id
            for owner in resources:
                owner['group_id'] = group.get('id')

            transformed_resources = humps.decamelize(resources)
            owners_result.extend(transformed_resources)
        yield owners_result


class GroupOwners(GraphStream):
    name = 'group_owners'
    version = GraphVersion.V1.value
    key_properties = ['id']
    replication_method = 'FULL_TABLE'
    replication_key = None
    endpoint = 'groups/{group_id}/owners'
    valid_replication_keys = []
    date_fields = []
    orderby = 'displayName'

    def sync(self, client, startdate=None):
        owners_result = []
        for group in Groups().get_all_groups(client):
            resources = client.get_all_resources(
                self.version, self.endpoint.format(group_id=group.get('id')))

            # Inject group id
            for owner in resources:
                owner['group_id'] = group.get('id')

            transformed_resources = humps.decamelize(resources)
            owners_result.extend(transformed_resources)
        yield owners_result


class TeamDrives(GraphStream):
    name = 'team_drives'
    version = GraphVersion.V1.value
    key_properties = ['id']
    replication_method = 'INCREMENTAL'
    replication_key = 'last_modified_date_time'
    endpoint = 'groups/{group_id}/drives'
    valid_replication_keys = ['last_modified_date_time']
    date_fields = []
    orderby = 'displayName'

    def sync(self, client, startdate=None):
        owners_result = []
        for group in Groups().get_all_groups(client):
            resources = client.get_all_resources(
                self.version, self.endpoint.format(group_id=group.get('id')))

            transformed_resources = humps.decamelize(resources)
            owners_result.extend(transformed_resources)
        yield owners_result


class Channels(GraphStream):
    name = 'channels'
    version = GraphVersion.V1.value
    key_properties = ['id']
    replication_method = 'FULL_TABLE'
    replication_key = None
    endpoint = 'teams/{group_id}/channels'
    valid_replication_keys = []
    date_fields = []
    orderby = 'displayName'

    def sync(self, client, startdate=None):
        channels_result = []
        for group in Groups().get_all_groups(client):
            resources = client.get_all_resources(
                self.version, self.endpoint.format(group_id=group.get('id')))

            transformed_resources = humps.decamelize(resources)
            channels_result.extend(transformed_resources)
            yield channels_result

    def get_all_channels_for_group(self, client, group_id):
        return client.get_all_resources(
            self.version, self.endpoint.format(group_id=group_id))


class ChannelMembers(GraphStream):
    name = 'channel_members'
    version = GraphVersion.BETA.value
    key_properties = ['id']
    replication_method = 'FULL_TABLE'
    replication_key = None
    endpoint = 'chats/{channel_id}/members'
    valid_replication_keys = []
    date_fields = []
    orderby = 'displayName'

    def sync(self, client, startdate=None):
        result = []

        for group in Groups().get_all_groups(client):
            group_id = group.get('id')

            for channel in Channels().get_all_channels_for_group(
                    client, group_id):
                channel_id = channel.get('id')

                for member in self.get_channel_members(client, channel_id):
                    member['channel_id'] = channel.get('id')
                    result.append(member)

        yield humps.decamelize(result)

    def get_channel_members(self, client, channel_id):
        return client.get_all_resources(
            self.version, self.endpoint.format(channel_id=channel_id))


class ChannelTabs(GraphStream):
    name = 'channel_tabs'
    version = GraphVersion.V1.value
    key_properties = ['id']
    replication_method = 'FULL_TABLE'
    replication_key = None
    endpoint = 'teams/{group_id}/channels/{channel_id}/tabs'
    valid_replication_keys = []
    date_fields = []

    def sync(self, client, startdate=None):
        result = []

        for group in Groups().get_all_groups(client):
            group_id = group.get('id')

            for channel in Channels().get_all_channels_for_group(
                    client, group_id):
                channel_id = channel.get('id')

                channel_tabs = client.get_all_resources(
                    self.version,
                    self.endpoint.format(group_id=group_id,
                                         channel_id=channel_id))
                for tab in channel_tabs:
                    tab['group_id'] = group_id
                    tab['channel_id'] = channel_id

                result.extend(channel_tabs)
        yield humps.decamelize(result)


class ChannelMessages(GraphStream):
    name = 'channel_messages'
    version = GraphVersion.BETA.value
    key_properties = ['id']
    replication_method = 'INCREMENTAL'
    replication_key = 'last_modified_date_time'
    endpoint = 'teams/{group_id}/channels/{channel_id}/messages/delta'
    valid_replication_keys = [
        'last_modified_date_time', 'created_date_time', 'deleted_date_time'
    ]
    date_fields = []
    orderby = 'displayName'
    filter_param = '{replication_key} gt {startdate}'

    def get_bookmark(self, stream, default):
        # default only populated on initial sync
        if (self.state is None) or ('bookmarks' not in self.state):
            return default
        return self.state.get('bookmarks', {}).get(stream, default)

    def sync(self, client, startdate=None):
        result = []
        for group in Groups().get_all_groups(client):

            channels = client.get_all_resources(
                Channels.version,
                Channels.endpoint.format(group_id=group.get('id')))

            for channel in channels:
                channel_messages = self.get_messages_for_group_channel(
                    client,
                    group_id=group.get('id'),
                    channel_id=channel.get('id'),
                    startdate=startdate)

                transformed_channel_messages = humps.decamelize(
                    channel_messages)
                result.extend(transformed_channel_messages)
        yield result

    def get_messages_for_group_channel(self, client, group_id, channel_id,
                                       startdate):
        filter_param = self.filter_param.format(replication_key=humps.camelize(
            self.replication_key), startdate=startdate)
        endpoint = self.endpoint.format(group_id=group_id,
                                        channel_id=channel_id,
                                        top=self.top)
        return client.get_all_resources(self.version,
                                        endpoint,
                                        filter_param=filter_param)


class ChannelMessageReplies(GraphStream):
    name = 'channel_message_replies'
    version = GraphVersion.BETA.value
    key_properties = ['id']
    replication_method = 'INCREMENTAL'
    replication_key = 'created_date_time'
    endpoint = 'teams/{group_id}/channels/{channel_id}/messages/{message_id}/replies'
    valid_replication_keys = [
        'created_date_time', 'last_modified_date_time', 'deleted_date_time'
    ]
    date_fields = []
    orderby = None

    def sync(self, client, startdate=None):
        results = []

        for group in Groups().get_all_groups(client):
            group_id = group.get('id')

            for channel in Channels().get_all_channels_for_group(
                    client, group_id=group_id):
                channel_id = channel.get('id')

                for message in ChannelMessages(
                        client).get_messages_for_group_channel(
                            client,
                            group_id=group_id,
                            channel_id=channel_id,
                            startdate=startdate):
                    message_id = message.get('id')

                    replies = client.get_all_resources(
                        self.version,
                        self.endpoint.format(group_id=group_id,
                                             channel_id=channel_id,
                                             message_id=message_id))
                    results.extend(replies)

        yield humps.decamelize(results)


class Conversations(GraphStream):
    name = 'conversations'
    version = GraphVersion.V1.value
    key_properties = ['id']
    replication_method = 'INCREMENTAL'
    replication_key = 'last_delivered_date_time'
    endpoint = 'groups/{group_id}/conversations'
    valid_replication_keys = ['last_delivered_date_time']
    date_fields = []
    orderby = 'displayName'

    def sync(self, client, startdate=None):
        results = []
        for group in Groups().get_all_groups(client):
            group_id = group.get('id')
            conversations = self.get_conversations_for_group(
                client, group_id=group.get('id'))
            for conversation in conversations:
                conversation['group_id'] = group_id
            results.extend(conversations)

        yield humps.decamelize(results)

    def get_conversations_for_group(self, client, group_id):
        return client.get_all_resources(
            self.version, self.endpoint.format(group_id=group_id))


class ConversationThreads(GraphStream):
    name = 'conversation_threads'
    version = GraphVersion.V1.value
    key_properties = ['id']
    replication_method = 'INCREMENTAL'
    replication_key = 'last_delivered_date_time'
    endpoint = 'groups/{group_id}/conversations/{conversation_id}/threads'
    valid_replication_keys = ['last_delivered_date_time']
    date_fields = []
    orderby = 'displayName'

    def sync(self, client, startdate=None):
        result = []
        for group in Groups().get_all_groups(client):
            group_id = group.get('id')
            for conversation in Conversations().get_conversations_for_group(
                    client, group_id=group_id):
                conversation_id = conversation.get('id')
                threads = self.get_threads_for_group(client, group_id,
                                                     conversation_id)
                for thread in threads:
                    thread['group_id'] = group_id
                    thread['conversation_id'] = conversation_id

                result.extend(threads)
        yield humps.decamelize(result)

    def get_threads_for_group(self, client, group_id, conversation_id):
        return client.get_all_resources(
            self.version,
            self.endpoint.format(group_id=group_id,
                                 conversation_id=conversation_id))


class ConversationPosts(GraphStream):
    name = 'conversation_posts'
    version = GraphVersion.V1.value
    key_properties = ['id', 'change_key']
    replication_method = 'INCREMENTAL'
    replication_key = 'last_modified_date_time'
    endpoint = 'groups/{group_id}/conversations/{conversation_id}/threads/{thread_id}/posts'
    valid_replication_keys = ['last_modified_date_time', 'received_date_time']
    date_fields = []
    orderby = 'displayName'

    def sync(self, client, startdate=None):
        result = []

        for group in Groups().get_all_groups(client):
            group_id = group.get('id')

            for conversation in Conversations().get_conversations_for_group(
                    client, group_id=group_id):
                conversation_id = conversation.get('id')

                for thread in ConversationThreads().get_threads_for_group(
                        client, group_id=group_id,
                        conversation_id=conversation_id):
                    thread_id = thread.get('id')
                    posts = client.get_all_resources(
                        self.version,
                        self.endpoint.format(group_id=group_id,
                                             conversation_id=conversation_id,
                                             thread_id=thread_id))
                    for post in posts:
                        post['thread_id'] = thread_id
                        post['conversation_id'] = conversation_id
                        post['group_id'] = group_id

                    result.extend(posts)
        yield humps.decamelize(result)


class TeamDeviceUsageReport(GraphStream):
    name = 'team_device_usage_report'
    version = GraphVersion.BETA.value
    key_properties = ['user_principal_name', 'report_refresh_date']
    replication_method = 'INCREMENTAL'
    replication_key = 'report_refresh_date'
    endpoint = 'reports/getTeamsDeviceUsageUserDetail(date={date})?$format=text/csv'
    valid_replication_keys = ['report_refresh_date']
    date_fields = []
    orderby = None
    DATE_WINDOW_SIZE = 1

    def sync(self, client, startdate=None):
        last_dttm = strptime_to_utc(startdate)
        abs_start, abs_end = self.get_absolute_start_end_time(
            last_dttm, self.config.get('attribution_widnow', 7))
        window_start = abs_start
        while window_start != abs_end:
            report_date_str = window_start.strftime("%Y-%m-%d")
            for page in self.client.get_report(
                    self.version, self.endpoint.format(date=report_date_str)):
                transformed = transform(page)
                yield humps.decamelize(transformed)
            window_start = window_start + timedelta(days=self.DATE_WINDOW_SIZE)


AVAILABLE_STREAMS = {
    "users": Users,
    "groups": Groups,
    "group_members": GroupMembers,
    "group_owners": GroupOwners,
    "channels": Channels,
    "channel_members": ChannelMembers,
    "channel_tabs": ChannelTabs,
    "channel_messages": ChannelMessages,
    "channel_message_replies": ChannelMessageReplies,
    "conversations": Conversations,
    "conversation_threads": ConversationThreads,
    "conversation_posts": ConversationPosts,
    "team_drives": TeamDrives,
    "team_device_usage_report": TeamDeviceUsageReport
}
