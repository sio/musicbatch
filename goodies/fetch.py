'''
Interact with remote data sources
'''


import requests
import lxml.html

from api import RateLimiter


class BaseDataFetcher:
    '''Base class for data fetchers'''


    ENCODING_FALLBACK = 'utf-8'
    RATELIMIT_CALLS = 20
    RATELIMIT_INTERVAL = 20
    TIMEOUT = 5
    USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:65.0) Gecko/20100101 Firefox/65.0'


    def __init__(self):
        session = requests.Session()
        session.headers.update({'user-agent': self.USER_AGENT})
        session.timeout = self.TIMEOUT
        self._requests = session

        self.rate_limit = RateLimiter(
            calls = self.RATELIMIT_CALLS,
            interval = self.RATELIMIT_INTERVAL,
        )


    def get(self, url, *a, **ka):
        with self.rate_limit:
            response = self._requests.get(url, *a, **ka)
            response.raise_for_status()  # fail early
            if response.encoding is None:
                response.encoding = self.ENCODING_FALLBACK
            return response


    def parse_html(self, url, *a, **ka):
        response = self.get(url, *a, **ka)
        html = lxml.html.fromstring(response.text)
        html.make_links_absolute(response.url)
        return html
