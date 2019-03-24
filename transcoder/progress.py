'''
Show progress of the transcoding job
'''


from threading import Lock, Thread
from time import sleep



class ThreadSafeCounter:
    '''
    A counter that can be safely incremented by multiple threads
    '''

    def __init__(self, initial=0):
        self.value = initial
        self.lock = Lock()


    def increment(self, number=1):
        with self.lock:
            self.value += number
            return self.value



class TranscodingStats:
    '''
    Numberic statistics of the transcoding job
    '''

    def __init__(self):
        self._done = ThreadSafeCounter()
        self._skipped = ThreadSafeCounter()


    def __repr__(self):
        return '<{cls}(done={done}, skipped={skip})>'.format(
            cls = self.__class__.__name__,
            skip = self.skipped,
            done = self.done,
        )


    def show(self):
        return '{total: 5d} files processed ({done} transcoded, {skip} skipped)'.format(
            total = self.total,
            done = self.done,
            skip = self.skipped,
        )


    @property
    def total(self):
        '''Total number of tasks processed'''
        return self.done + self.skipped


    @property
    def done(self):
        '''Number of finished tasks'''
        return self._done.value


    @property
    def skipped(self):
        '''Number of skipped tasks'''
        return self._skipped.value


    def record_skip(self):
        '''Record a skipped task'''
        self._skipped.increment()


    def record_done(self):
        '''Record a finished task'''
        self._done.increment()



class DotTicker:
    '''Simple throbber-like object for showing unknown amounts of progress'''

    def __init__(self, pattern='.', max_length=3):
        self.length = 0
        self.pattern = pattern
        self.max_length = max_length


    def __str__(self):
        result = self.pattern * self.length
        self.tick()
        return result


    def __format__(self, format_spec):
        return str(self).__format__(format_spec)


    def tick(self):
        if self.length < self.max_length:
            self.length += 1
        else:
            self.length = 0



def show_progress(job, refresh_delay=0.5):
    '''Show progress of the TranscodingJob from a background thread'''
    def background():
        ticker = DotTicker()
        last_time = False
        while not last_time:
            last_time = job.finished
            print(' {stats}{ticker: <3}\r'.format(
                stats = job.stats.show(),
                ticker = ticker,
            ), end='')
            sleep(refresh_delay)
        print('')
    ui_thread = Thread(target=background)
    ui_thread.start()
    return ui_thread
