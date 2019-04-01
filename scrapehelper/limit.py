'''
Rate limit access to sensitive resources
'''

import threading
import time
from functools import wraps



class RateLimitReachedError(RuntimeError):
    '''Raised when rate limit is reached'''



class RateLimiter:
    '''
    Honor rate limits when using third party API

    RateLimiter objects can be used in any of three ways:
        - Through decorator interface
        - Through context manager interface
        - Manually registering new_call() before sending an API request
    '''
    # TODO: write tests for RateLimiter

    REFRESH_INTERVAL = 0.5  # seconds (minimum sleep interval)


    def __init__(self, calls=15, interval=15*60, wait=True):
        '''
        Create a new RateLimiter object

        calls:
            Maximum number of API calls allowed within time period
        interval:
            The time period (in seconds) for which the number of calls is
            limited
        wait:
            Boolean. If True the RateLimiter will wait until limit terms are
            satisfied before registering a new call. Will raise
            RateLimitReachedError otherwise.
        '''
        self.call_limit = calls
        self.call_log = []
        self.interval = interval
        self.wait = wait
        self.clock = time.monotonic
        self.lock = threading.RLock()
        self.next_cleanup = 0


    def new_call(self):
        '''
        Register new API call

        If self.wait is True, wait until rate limit terms are satisfied.
        Raise RateLimitReachedError otherwise.
        '''
        while True:
            try:
                self._call_attempt()
                break
            except RateLimitReachedError as e:
                if self.wait:
                    time.sleep(max(
                        self.REFRESH_INTERVAL,
                        self.next_cleanup - self.clock()
                    ))
                else:
                    raise e


    def _call_attempt(self):
        '''
        Try to add a new item to the call log.

        Raises RateLimitReachedError if the log is full.
        '''
        with self.lock:
            self._cleanup()
            if len(self.call_log) >= self.call_limit:
                raise RateLimitReachedError(
                    'can not make more than {num} calls in {interval} seconds'.format(
                        num = self.call_limit,
                        interval = self.interval,
                    )
                )
            self.call_log.append(self.clock())


    def _cleanup(self):
        '''
        Maintain the call log: remove obsolete entries, schedule next cleanup
        '''
        if self.call_log and not self.next_cleanup:
            self.next_cleanup = self.call_log[0] + self.interval
        while self.next_cleanup\
        and self.clock() > self.next_cleanup:
            try:
                self.call_log.pop(0)
                self.next_cleanup = self.call_log[0] + self.interval
            except IndexError:  # pop from empty list
                self.next_cleanup = 0


    def __enter__(self):
        '''Context manager interface for RateLimiter'''
        self.new_call()


    def __exit__(self, exc_type, exc_val, exc_tb):
        '''Context manager interface for RateLimiter'''
        return False


    def __call__(self, function):
        '''Function decorator interface for RateLimiter'''
        @wraps(function)
        def decorated(*a, **kw):
            self.new_call()
            return function(*a, **kw)
        return decorated
