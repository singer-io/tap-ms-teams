import inspect
import os

import humps
import singer
import singer.metrics
from singer.utils import strptime_to_utc
from tap_ms_teams.client import GraphVersion

LOGGER = singer.get_logger()


class Base:
    def __init__(self, client=None, config=None, catalog=None, state=None):
        self.client = client
        self.config = config
        self.catalog = catalog
        self.state = state
        self.top = 50

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
        LOGGER.info('Stream: {} - Write state, bookmark value: {}'.format(
            stream, value))
        self.write_state()

    def get_bookmark(self, stream, default):
        # default only populated on initial sync
        if (self.state is None) or ('bookmarks' not in self.state):
            return default
        return self.state.get('bookmarks', {}).get(stream, default)

    # Returns max key and date time for all replication key data in record
    def max_from_replication_dates(self, record):
        date_times = {
            dt: strptime_to_utc(record[dt])
            for dt in self.valid_replication_keys if record[dt] is not None
        }
        max_key = max(date_times)
        return date_times[max_key]

    def sync(self, mdata):
        resources = self.client.get_all_resources(self.version,
                                                  self.endpoint,
                                                  top=self.top,
                                                  orderby=self.orderby)

        transformed_resources = humps.decamelize(resources)
        yield resources


class Users(Base):
    name = 'users'
    version = GraphVersion.V1.value
    key_properties = ['id']
    replication_method = 'FULL_TABLE'
    replication_key = None
    endpoint = 'users'
    valid_replication_keys = []
    date_fields = []
    orderby = 'displayName'


class Groups(Base):
    name = 'groups'
    version = GraphVersion.V1.value
    key_properties = ['id']
    replication_method = 'FULL_TABLE'
    replication_key = None
    endpoint = 'groups'
    valid_replication_keys = []
    date_fields = []
    orderby = 'displayName'

    def get_all_groups(self):
        return self.client.get_all_resources(self.version,
                                             Groups.endpoint,
                                             top=self.top,
                                             orderby='displayName')


class GroupMembers(Groups):
    name = 'group_members'
    version = GraphVersion.V1.value
    key_properties = ['id']
    replication_method = 'FULL_TABLE'
    replication_key = None
    endpoint = 'groups/{group_id}/members'
    valid_replication_keys = []
    date_fields = []
    orderby = 'displayName'

    def sync(self, mdata):
        owners_result = []
        for group in Groups(self.client).get_all_groups():
            resources = self.client.get_all_resources(
                self.version, self.endpoint.format(group_id=group.get('id')))

            # Inject group id
            for owner in resources:
                owner['group_id'] = group.get('id')

            transformed_resources = humps.decamelize(resources)
            owners_result.extend(transformed_resources)
        yield owners_result


class GroupOwners(Groups):
    name = 'group_owners'
    version = GraphVersion.V1.value
    key_properties = ['id']
    replication_method = 'FULL_TABLE'
    replication_key = None
    endpoint = 'groups/{group_id}/owners'
    valid_replication_keys = []
    date_fields = []
    orderby = 'displayName'

    def sync(self, mdata):
        owners_result = []
        for group in Groups(self.client).get_all_groups():
            resources = self.client.get_all_resources(
                self.version, self.endpoint.format(group_id=group.get('id')))

            # Inject group id
            for owner in resources:
                owner['group_id'] = group.get('id')

            transformed_resources = humps.decamelize(resources)
            owners_result.extend(transformed_resources)
        yield owners_result


class TeamDrives(Groups):
    name = 'team_drives'
    version = GraphVersion.V1.value
    key_properties = ['id']
    replication_method = 'INCREMENTAL'
    replication_key = 'last_modified_date_time'
    endpoint = 'groups/{group_id}/drives'
    valid_replication_keys = ['last_modified_date_time']
    date_fields = []
    orderby = 'displayName'

    def sync(self, mdata, statedate=None):
        owners_result = []
        for group in Groups(self.client).get_all_groups():
            resources = self.client.get_all_resources(
                self.version, self.endpoint.format(group_id=group.get('id')))

            transformed_resources = humps.decamelize(resources)
            owners_result.extend(transformed_resources)
        yield owners_result


class Channels(Groups):
    name = 'channels'
    version = GraphVersion.V1.value
    key_properties = ['id']
    replication_method = 'FULL_TABLE'
    replication_key = None
    endpoint = 'teams/{group_id}/channels'
    valid_replication_keys = []
    date_fields = []
    orderby = 'displayName'

    def sync(self, mdata):
        channels_result = []
        for group in Groups(self.client).get_all_groups():
            resources = self.client.get_all_resources(
                self.version, self.endpoint.format(group_id=group.get('id')))

            transformed_resources = humps.decamelize(resources)
            channels_result.extend(transformed_resources)
        yield channels_result

    def get_all_channels_for_group(self, group_id):
        return self.client.get_all_resources(
            self.version, self.endpoint.format(group_id=group_id))


class ChannelMembers(Channels):
    name = 'channel_members'
    version = GraphVersion.BETA.value
    key_properties = ['id']
    replication_method = 'FULL_TABLE'
    replication_key = None
    endpoint = 'chats/{channel_id}/members'
    valid_replication_keys = []
    date_fields = []
    orderby = 'displayName'

    def sync(self, mdata):
        channels_result = []
        result = []
        for group in Groups(self.client).get_all_groups():
            group_id = group.get('id')
            for channel in Channels(
                    self.client).get_all_channels_for_group(group_id):
                channel_id = channel.get('id')
                channel_members = self.client.get_all_resources(
                    self.version, self.endpoint.format(channel_id=channel_id))
                for member in channel_members:
                    member['channel_id'] = channel.get('id')

                transformed_channel_members = humps.decamelize(channel_members)
                result.extend(transformed_channel_members)
        yield result


class ChannelTabs(Channels):
    name = 'channel_tabs'
    version = GraphVersion.V1.value
    key_properties = ['id']
    replication_method = 'FULL_TABLE'
    replication_key = None
    endpoint = 'teams/{group_id}/channels/{channel_id}/tabs'
    valid_replication_keys = []
    date_fields = []

    def sync(self, mdata):
        channels_result = []
        result = []
        for group in Groups(self.client).get_all_groups():
            group_id = group.get('id')
            for channel in Channels(
                    self.client).get_all_channels_for_group(group_id):
                channel_id = channel.get('id')
                channel_tabs = self.client.get_all_resources(
                    self.version,
                    self.endpoint.format(group_id=group_id,
                                         channel_id=channel_id))
                for tab in channel_tabs:
                    tab['group_id'] = group_id
                    tab['channel_id'] = channel_id

                transformed_channel_members = humps.decamelize(channel_tabs)
                result.extend(transformed_channel_members)
        yield result


class ChannelMessages(Channels):
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

    def sync(self, mdata, startdate=None):
        result = []
        for group in Groups(self.client).get_all_groups():
            channels = self.client.get_all_resources(
                Channels.version,
                Channels.endpoint.format(group_id=group.get('id')))
            for channel in channels:
                channel_messages = self.get_messages_for_group_channel(
                    group_id=group.get('id'),
                    channel_id=channel.get('id'),
                    startdate=startdate)

                transformed_channel_messages = humps.decamelize(
                    channel_messages)
                result.extend(transformed_channel_messages)
        yield result

    def get_messages_for_group_channel(self, group_id, channel_id, startdate):
        filter_param = self.filter_param.format(
            replication_key=humps.camelize(self.replication_key),
            startdate=startdate
        )
        endpoint = self.endpoint.format(
            group_id=group_id,
            channel_id=channel_id,
            top=self.top,
            filter=filter_param
        )
        return self.client.get_all_resources(self.version, endpoint)


class ChannelMessageReplies(ChannelMessages):
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

    def sync(self, mdata, startdate=None):
        results = []
        for group in Groups(self.client).get_all_groups():
            group_id = group.get('id')
            for channel in Channels(
                    self.client).get_all_channels_for_group(group_id=group_id):
                channel_id = channel.get('id')
                for message in ChannelMessages(
                        self.client).get_messages_for_group_channel(
                            group_id=group_id,
                            channel_id=channel_id,
                            startdate=None):
                    message_id = message.get('id')
                    results.extend(
                        self.client.get_all_resources(
                            self.version,
                            self.endpoint.format(group_id=group_id,
                                                 channel_id=channel_id,
                                                 message_id=message_id)))
        transformed_results = humps.decamelize(results)
        yield transformed_results


class Conversations(Base):
    name = 'conversations'
    version = GraphVersion.V1.value
    key_properties = ['id']
    replication_method = 'INCREMENTAL'
    replication_key = 'last_delivered_date_time'
    endpoint = 'groups/{group_id}/conversations'
    valid_replication_keys = ['last_delivered_date_time']
    date_fields = []
    orderby = 'displayName'

    def sync(self, mdata, startdate=None):
        results = []
        for group in Groups(self.client).get_all_groups():
            group_id = group.get('id')
            conversations = self.get_conversations_for_group(
                group_id=group.get('id'))
            for conversation in conversations:
                conversation['group_id'] = group_id
            results.extend(conversations)

        transformed_results = humps.decamelize(results)
        yield transformed_results

    def get_conversations_for_group(self, group_id):
        return self.client.get_all_resources(
            self.version, self.endpoint.format(group_id=group_id))


class ConversationThreads(Conversations):
    name = 'conversation_threads'
    version = GraphVersion.V1.value
    key_properties = ['id']
    replication_method = 'INCREMENTAL'
    replication_key = 'last_delivered_date_time'
    endpoint = 'groups/{group_id}/conversations/{conversation_id}/threads'
    valid_replication_keys = ['last_delivered_date_time']
    date_fields = []
    orderby = 'displayName'

    def sync(self, mdata, startdate=None):
        result = []
        for group in Groups(self.client).get_all_groups():
            group_id = group.get('id')
            for conversation in Conversations(
                    self.client).get_conversations_for_group(
                        group_id=group_id):
                conversation_id = conversation.get('id')
                threads = self.get_threads_for_group_conversation(
                    group_id, conversation_id)
                for thread in threads:
                    thread['group_id'] = group_id
                    thread['conversation_id'] = conversation_id

                transformed_threads = humps.decamelize(threads)
                result.extend(transformed_threads)
        yield result

    def get_threads_for_group_conversation(self, group_id, conversation_id):
        return self.client.get_all_resources(
            self.version,
            self.endpoint.format(group_id=group_id,
                                 conversation_id=conversation_id))


class ConversationPosts(ConversationThreads):
    name = 'conversation_posts'
    version = GraphVersion.V1.value
    key_properties = ['id', 'change_key']
    replication_method = 'INCREMENTAL'
    replication_key = 'last_modified_date_time'
    endpoint = 'groups/{group_id}/conversations/{conversation_id}/threads/{thread_id}/posts'
    valid_replication_keys = ['last_modified_date_time', 'received_date_time']
    date_fields = []
    orderby = 'displayName'

    def sync(self, mdata, startdate=None):
        result = []
        for group in Groups(self.client).get_all_groups():
            group_id = group.get('id')
            for conversation in Conversations(
                    self.client).get_conversations_for_group(
                        group_id=group_id):
                conversation_id = conversation.get('id')
                for thread in ConversationThreads(
                        self.client).get_threads_for_group_conversation(
                            group_id=group_id,
                            conversation_id=conversation_id):
                    thread_id = thread.get('id')
                    posts = self.client.get_all_resources(
                        self.version,
                        self.endpoint.format(group_id=group_id,
                                             conversation_id=conversation_id,
                                             thread_id=thread_id))
                    for post in posts:
                        post['thread_id'] = thread_id
                        post['conversation_id'] = conversation_id
                        post['group_id'] = group_id

                    transformed_posts = humps.decamelize(posts)
                    result.extend(transformed_posts)
        yield result


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
    "team_drives": TeamDrives
}
