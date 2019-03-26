import threading
import time



class RateLimitReachedError(RuntimeError):
    '''Raised when rate limit is reached'''



class RateLimiter:
    # TODO: write docstrings for RateLimiter
    # TODO: write tests for RateLimiter

    REFRESH_INTERVAL = 0.5  # seconds


    def __init__(self, calls=15, interval=15*60):
        self.call_limit = calls
        self.call_log = []
        self.interval = interval
        self.clock = time.monotonic
        self.lock = threading.RLock()
        self.next_cleanup = 0


    def wait(self):
        while True:
            try:
                self.record_call()
                break
            except RateLimitReachedError:
                time.sleep(max(
                    self.REFRESH_INTERVAL,
                    self.next_cleanup - self.clock()
                ))
                self.cleanup()


    def record_call(self):
        with self.lock:
            if len(self.call_log) >= self.call_limit:
                raise RateLimitReachedError
            self.call_log.append(self.clock())


    def cleanup(self):
        with self.lock:
            if self.call_log and not self.next_cleanup:
                self.next_cleanup = self.call_log[0] + self.interval
            while self.next_cleanup\
            and self.clock() > self.next_cleanup:
                try:
                    self.next_cleanup = self.call_log.pop(0) + self.interval
                except IndexError:  # pop from empty list
                    self.next_cleanup = 0
