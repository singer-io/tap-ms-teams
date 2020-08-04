

import os

import singer
import singer.metrics
from tap_ms_teams.client import GraphVersion


class Base:

    def __init__(self, client, config=None, catalog=None, state=None, write_to_singer=True):
        self.client = client
        self.config = config
        self.catalog = catalog
        self.state = state
        self.write_to_singer = write_to_singer
        self.top = 100

    @staticmethod
    def get_abs_path(path):
        return os.path.join(os.path.dirname(os.path.realpath(__file__)), path)

    def load_schema(self):
        schema_path = self.get_abs_path('schemas')
        # pylint: disable=no-member
        return singer.utils.load_json('{}/{}.json'.format(schema_path, self.name))

    def write_schema(self):
        schema = self.load_schema()
        # pylint: disable=no-member
        return singer.write_schema(stream_name=self.name, schema=schema,
                                   key_properties=self.key_properties)

    def write_state(self):
        return singer.write_state(self.state)

    def update_bookmarks(self, stream, value):
        if 'bookmarks' not in self.state:
            self.state['bookmarks'] = {}
        self.state['bookmarks'][stream] = value
        LOGGER.info('Stream: {} - Write state, bookmark value: {}'.format(stream, value))
        self.write_state()

    def get_bookmark(self, stream, default):
        # default only populated on initial sync
        if (self.state is None) or ('bookmarks' not in self.state):
            return default
        return self.state.get('bookmarks', {}).get(stream, default)


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

    def sync(self, mdata):

        schema = self.load_schema()
        bookmark = singer.get_bookmark(state=self.state, tap_stream_id=self.name, key=None)
        if bookmark is None:
            bookmark = self.config.get('start_date')
        new_bookmark = bookmark

        # pylint: disable=unused-variable
        with singer.metrics.job_timer(job_type='list_users') as timer:
            with singer.metrics.record_counter(endpoint=self.name) as counter:
                users_list = self.client.get_resource(self.version, self.endpoint, top=10, orderby=self.orderby)
                for page in users_list:
                    yield page

AVAILABLE_STREAMS = {
    "users": Users
}
