'''
CLI application for transcoding music files
'''


import os
import time
from queue import Queue
from threading import Thread

import mutagen
from ruamel import yaml

from transcoder import (
    DEFAULT_CONFIG,
    KNOWN_EXTENSIONS,
    LOSSLESS_EXTENSIONS,
    LOSSY_EXTENSIONS,
)
from transcoder.encoders import (
    VerbatimFileCopy,
    VorbisTranscoder,
)
from transcoder.queue import (
    TranscodingQueue,
    TranscodingTask,
)



import logging
log = logging.getLogger(__name__)



def run(config_file):
    '''
    CLI entry point
    '''
    # 1. Load config from YAML
    # 2. Find relevant music files and add them to queue
    # 3. Concurrently process each file in the queue:
    #    - Calculate target location
    #    - Transcode
    #    - Fill tags
    #    - Copy lyrics
    #    - Copy cover art

    job = TranscodingJob(config_file)
    TranscodingTask.pattern = job.output_pattern  # TODO: refactor to avoid messing with class attributes
    tasks = TranscodingQueue(job.inputs)

    execute_in_threadqueue(job.transcode, tasks, buffer_size=20)



def execute_in_threadqueue(function, args_seq,
                           num_threads=None, buffer_size=None, break_value=None):
    '''
    Execute a function with each argument from a given sequence.

    Execution in done in threads, args_seq is consumed lazily with a sensible
    lookahead (use buffer_size). break_value is a singleton object that can
    never occur in the args_seq - it is used to signal the end of the sequence
    to each thread.
    '''
    # NOTE: ThreadPoolExecutor and multiprocessing.Pool.imap_unordered are greedy.
    #       They consume the whole generator before starting processing its values,
    #       hence the Queue approach.

    if num_threads is None:
        num_threads = os.cpu_count()
    if buffer_size is None:
        buffer_size = num_threads * 5

    queue = Queue(maxsize=buffer_size)  # ensure there is enough tasks scheduled, but not too many
    threads = []

    def worker():
        while True:
            log.debug('Requesting a task from the queue (size={})'.format(queue.qsize()))
            task = queue.get()
            if task is break_value:
                break
            function(task)
            queue.task_done()

    for i in range(num_threads):  # create worker threads
        t = Thread(target=worker)
        t.start()
        threads.append(t)

    for task in args_seq:  # queue tasks at the sane pace
        queue.put(task)

    queue.join()  # block until all tasks are done

    for i in range(num_threads):  # stop workers
        queue.put(break_value)
    for t in threads:
        t.join()



class TranscodingJob:
    '''Store essential parameters of the transcoding job'''

    ENCODERS = {
        None: VorbisTranscoder,
        'vorbis': VorbisTranscoder,
    }


    def __init__(self, config_file):
        '''Initialize transcoding job'''
        self.config_file = config_file
        self._timestamp = None

        # TODO: validate config file against schema

        with open(config_file) as f:
            config = yaml.load(f, Loader=yaml.RoundTripLoader)
            output = config.get('output', {})

        self.job_id = config.get('name', DEFAULT_CONFIG['name'])
        self.inputs = config.get('input', [])
        self.output_dir = output.get('directory')
        self.output_pattern = output.get('pattern', DEFAULT_CONFIG['pattern'])

        encoder = output.get('format', DEFAULT_CONFIG['format'])
        quality = output.get('quality', DEFAULT_CONFIG['quality'])
        self.transcoder = self.ENCODERS.get(encoder)(quality)

        lossy_action = output.get('lossy_source', DEFAULT_CONFIG['lossy_source'])
        if lossy_action == 'allow_bad_transcodes':
            self.lossy_action = self.transcoder
        elif lossy_action == 'copy':
            self.lossy_action = VerbatimFileCopy()

        if not os.path.isdir(self.output_dir):
            os.makedirs(self.output_dir)

        log.debug('Initialized {}'.format(self))
        # TODO: handle 'extras' section (lyrics, cover, etc)


    def __repr__(self):
        return '{cls}({config!r})'.format(
            cls=self.__class__.__name__,
            config=self.config_file,
        )


    def transcode(self, task):
        '''Execute a single transcoding task'''
        log.debug('Started {task}'.format(task=task))

        source_format = os.path.splitext(task.source)[1][1:].lower()
        if source_format in LOSSLESS_EXTENSIONS:
            worker = self.transcoder
        else:
            worker = self.lossy_action

        if self._timestamp is None:  # record the time of first transcoding task
            self._timestamp = int(time.time())

        # TODO: cleverly skip target if it's already done (check timestamp)

        # Step 1: Transcode
        result_filename = worker(
            task.source,
            os.path.join(self.output_dir, task.target)
        )

        # Step 2: Copy music tags
        result = mutagen.File(result_filename, easy=True)
        result.tags.update(task.tags)
        result.save()

        log.debug('Finished {task}'.format(task=task))


    @property
    def timestamp(self):
        '''
        Date and time of starting the first transcoding task in this job
        (in Unix time format)
        '''
        # TODO: Use TranscodingJob.timestamp for detecting destination duplicates
        return self._timestamp
