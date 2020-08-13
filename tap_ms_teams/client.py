import codecs
import csv
import threading
import urllib
from enum import Enum

import backoff
import requests
import singer
import singer.metrics
from requests.models import Response

LOGGER = singer.get_logger()  # noqa

TOKEN_URL = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
SCOPE = "https://graph.microsoft.com/.default"
BASE_GRAPH_URL = 'https://graph.microsoft.com'
TOKEN_EXPIRATION_PERIOD = 3599
LOGGER = singer.get_logger()


class GraphVersion(Enum):
    BETA = 'beta'
    V1 = 'v1.0'


class Server5xxError(Exception):
    pass


class Server42xRateLimitError(Exception):
    pass


class MicrosoftGraphClient:

    MAX_TRIES = 5

    def __init__(self, config):
        self.config = config
        self.session = requests.Session()
        self.login_timer = None
        self.access_token = None

    def build_url(self, baseurl, version, path, args_dict):
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

        try:
            body = {
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'scope': SCOPE
            }

            with singer.http_request_timer('POST get access token'):
                result = self.make_request(
                    method='POST',
                    url=TOKEN_URL.format(tenant_id=self.tenant_id),
                    data=body)

            # result = response.json()
            self.access_token = result.get('access_token')

        finally:
            self.login_timer = threading.Timer(TOKEN_EXPIRATION_PERIOD,
                                               self.login)
            self.login_timer.start()

    def get_all_resources(self,
                          version,
                          endpoint,
                          top=None,
                          orderby=None,
                          filter=None):
        args = {}
        if top:
            args['$top'] = top
        if orderby:
            args["$orderby"] = orderby
        if filter:
            args["$filter"] = filter
        next = self.build_url(BASE_GRAPH_URL, version, endpoint, args)
        response = []
        while next:
            LOGGER.info(f"Making request GET {next}")
            body = self.make_request('GET', url=next)
            if body and len(body.get('value')) > 0:
                next = body.get('@odata.nextLink', None)
                data = body.get('value')
                response.extend(data)
            else:
                next = None
        return response

    def get_resource_page(self, version, endpoint, top=500, params=None):
        args = {
            '$top': top,
        }
        if orderby:
            args.update['$orderby'] = orderby

        next = self.build_url(BASE_GRAPH_URL, version, endpoint, args)
        while next:
            body = self.make_request('GET', url=next)
            next = body.get('@odata.nextLink', None)
            data = body.get('value')
            yield data
        return []

    @backoff.on_exception(
        backoff.expo,
        (Server5xxError, ConnectionError, Server42xRateLimitError),
        max_tries=5,
        factor=2)
    def make_request(self,
                     method,
                     url=None,
                     params=None,
                     data=None,
                     stream=False):

        headers = {'Authorization': 'Bearer {}'.format(self.access_token)}

        if method == "GET":
            LOGGER.info(
                f"Making {method} request to {url} with params: {params}")
            response = self.session.get(url, headers=headers)
        elif method == "POST":
            LOGGER.info(f"Making {method} request to {url} with body {data}")
            response = self.session.post(url, data=data)
        else:
            raise Exception("Unsupported HTTP method")

        LOGGER.info("Received code: {}".format(response.status_code))

        if response.status_code == 401:
            LOGGER.info(
                "Received unauthorized error code, retrying: {}".format(
                    response.text))
            self.login()
        elif response.status_code == 404:
            return []
        elif response.status_code == 429:
            LOGGER.info("Received rate limit response: {}".format(
                response.headers))
            raise Server42xRateLimitError()
        elif response.status_code >= 500:
            raise Server5xxError()

        if response.status_code not in [200, 201, 202]:
            raise RuntimeError(response.text)

        return response.json()
