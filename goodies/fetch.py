'''
Interact with remote data sources
'''


import requests
import lxml.html

from api import RateLimiter


class FetcherMeta(type):
    '''
    Metaclass for data fetchers

    Creates class attributes unique to each subclass
        rate_limit: RateLimiter object
        _requests:  requests.Session object
    '''

    def __init__(cls, name, bases, dct):
        '''Initiate class attributes for each subclass'''
        # Rate limits apply to all instances on the class
        cls.rate_limit = RateLimiter(
            calls = cls.RATELIMIT_CALLS,
            interval = cls.RATELIMIT_INTERVAL,
        )

        # Share session object between all instances of class
        session = requests.Session()
        session.headers.update({'user-agent': cls.USER_AGENT})
        session.timeout = cls.TIMEOUT
        cls._requests = session


class BaseDataFetcher(metaclass=FetcherMeta):
    '''Base class for data fetchers'''

    ENCODING_FALLBACK = 'utf-8'
    RATELIMIT_CALLS = 20
    RATELIMIT_INTERVAL = 20
    TIMEOUT = 5
    USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:65.0) Gecko/20100101 Firefox/65.0'


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