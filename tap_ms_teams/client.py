import codecs
import csv
import json
import threading
import urllib
from enum import Enum
import time

import backoff
import requests
import singer
import singer.metrics

LOGGER = singer.get_logger()  # noqa

TOKEN_URL = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
BASE_GRAPH_URL = 'https://graph.microsoft.com'
TOKEN_EXPIRATION_PERIOD = 3599
TOP_API_PARAM_DEFAULT = 500

class GraphVersion(Enum):
    BETA = 'beta'
    V1 = 'v1.0'


class Server5xxError(Exception):
    pass


class Server42xRateLimitError(Exception):
    pass


class MicrosoftGraphClient:

    MAX_TRIES = 5

    def __init__(self, config_path, config):
        self.config_path = config_path
        self.config = config
        self.session = requests.Session()
        self.login_timer = None
        self.access_token = None
        self.client_secret = None
        self.client_id = None
        self.tenant_id = None
        self.refresh_token = None

    @staticmethod
    def build_url(baseurl, version, path, args_dict):
        # Returns a list in the structure of urlparse.ParseResult
        url_parts = list(urllib.parse.urlparse(baseurl))
        url_parts[2] = version + '/' + path
        url_parts[4] = urllib.parse.urlencode(args_dict)
        return urllib.parse.urlunparse(url_parts)

    def login(self):
        LOGGER.info("Refreshing token")
        self.client_id = self.config.get('client_id')
        self.client_secret = self.config.get('client_secret')
        self.tenant_id = self.config.get('tenant_id')
        # Use the in-memory refresh_token if already rotated, else fall back to config
        if self.refresh_token is None:
            self.refresh_token = self.config.get('refresh_token')

        try:
            body = {
                'grant_type': 'refresh_token',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'refresh_token': self.refresh_token,
            }

            with singer.http_request_timer('POST get access token'):
                result = self.make_request(
                    method='POST',
                    url=TOKEN_URL.format(tenant_id=self.tenant_id),
                    data=body)

            self.access_token = result.get('access_token')
            # Microsoft may rotate the refresh_token; keep the latest one in memory
            new_refresh_token = result.get('refresh_token')
            if new_refresh_token and new_refresh_token != self.refresh_token:
                self.refresh_token = new_refresh_token
                self._write_config(new_refresh_token)

        finally:
            self.login_timer = threading.Timer(TOKEN_EXPIRATION_PERIOD,
                                               self.login)
            self.login_timer.start()


    def _write_config(self, refresh_token):
        LOGGER.info("Credentials Refreshed")
        with open(self.config_path, encoding='utf-8') as f:
            config = json.load(f)
        config['refresh_token'] = refresh_token
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)

    def get_all_resources(self,
                          version,
                          endpoint,
                          top=None,
                          orderby=None,
                          filter_param=None):
        args = {}

        if top:
            args['$top'] = top
        if orderby:
            args["$orderby"] = orderby
        if filter_param:
            args["$filter"] = filter_param

        next_url = self.build_url(BASE_GRAPH_URL, version, endpoint, args)

        response = []
        while next_url:
            LOGGER.info("Making request GET %s", next_url)
            body = self.make_request('GET', url=next_url)
            if body:
                next_url = body.get('@odata.nextLink', None)
                data = body.get('value')
                response.extend(data)
            else:
                next_url = None
        return response


    @backoff.on_exception(
        backoff.expo,
        (Server5xxError, ConnectionError, Server42xRateLimitError),
        max_tries=5,
        factor=2)
    def get_report(self, version, endpoint):
        headers = {'Authorization': 'Bearer {}'.format(self.access_token)}
        if self.config.get('user_agent'):
            headers['User-Agent'] = self.config['user_agent']

        url = self.build_url(BASE_GRAPH_URL, version, endpoint, {})

        LOGGER.info("Making request to %s", url)
        response = self.session.get(url, headers=headers, allow_redirects=True)

        if response.status_code == 401:
            LOGGER.info("Received unauthorized error code, retrying: %s", response.text)
            self.login()
        elif response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After'))
            LOGGER.info("Received rate limit response sleeping for : %s", retry_after)
            time.sleep(retry_after)
            raise Server42xRateLimitError()
        elif response.status_code >= 500:
            raise Server5xxError()

        if response.status_code not in [200, 201, 202]:
            raise RuntimeError(response.text)

        return self.stream_csv(response.url)


    # Stream CSV in batches of lines for transform and Singer write
    @backoff.on_exception(backoff.expo, (Server5xxError, ConnectionError),
                          max_tries=5,
                          factor=2)
    def stream_csv(self, url, batch_size=1024): # pylint: disable = no-self-use
        with requests.get(url, stream=True) as data:
            reader = csv.DictReader(
                # Correctly decoded for BOM which are produced by the API
                # See, https://docs.python.org/2.5/lib/module-encodings.utf-8-sig.html
                codecs.iterdecode(data.iter_lines(chunk_size=1024), "utf-8-sig"))
            batch = []

            for record in reader:
                batch.append(record)
                if len(batch) == batch_size:
                    yield batch
                    batch = []
            if batch:
                yield batch


    @backoff.on_exception(
        backoff.expo,
        (Server5xxError, ConnectionError, Server42xRateLimitError),
        max_tries=5,
        factor=2)
    def make_request(self, method, url=None, params=None, data=None):

        headers = {'Authorization': 'Bearer {}'.format(self.access_token)}

        if self.config.get('user_agent'):
            headers['User-Agent'] = self.config['user_agent']

        if method == "GET":
            LOGGER.info("Making %s request to %s with params: %s", method, url, params)
            response = self.session.get(url, headers=headers, allow_redirects=True)
        elif method == "POST":
            LOGGER.info("Making %s request to %s", method, url)
            response = self.session.post(url, data=data)
        else:
            raise Exception("Unsupported HTTP method")

        if response.status_code == 401:
            LOGGER.info(
                "Received unauthorized error code, retrying: %s", response.text)
            self.login()
        elif response.status_code == 429:
            LOGGER.info("Received rate limit response: %s", response.headers)
            retry_after = int(response.headers.get('Retry-After'))
            time.sleep(retry_after)
            raise Server42xRateLimitError()
        elif response.status_code >= 500:
            raise Server5xxError()

        if response.status_code not in [200, 201, 202]:
            raise RuntimeError(response.text)

        return response.json()
