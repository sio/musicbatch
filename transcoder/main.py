'''
CLI application for transcoding music files
'''


import os
import time
import sys
from contextlib import contextmanager
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
from transcoder.cover import copy_coverart
from transcoder.progress import (
    TranscodingStats,
    show_progress,
)
from transcoder.queue import (
    TranscodingQueue,
    TranscodingTask,
    execute_in_threadqueue,
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

    with restore_stdin():
        show_progress(job)   # start progress report thread
        execute_in_threadqueue(job.transcode, tasks, buffer_size=20)
        job.finished = True  # terminate progress report thread



@contextmanager
def restore_stdin():
    stdin, stdout, stderr = sys.stdin, sys.stdout, sys.stderr
    yield
    sys.stdin, sys.stdout, sys.stderr = stdin, stdout, stderr



class TranscodingJob:
    '''Store essential parameters of the transcoding job'''

    ENCODERS = {
        None: VorbisTranscoder,
        'vorbis': VorbisTranscoder,
    }


    def __init__(self, config_file):
        '''Initialize transcoding job'''
        self.stats = TranscodingStats()
        self.finished = False
        self.config_file = config_file
        self._timestamp = None

        # TODO: validate config file against schema

        with open(config_file) as f:
            config = yaml.load(f, Loader=yaml.RoundTripLoader)
            output = config.get('output', {})
            extras = config.get('extras', {})

        self.job_id = config.get('name', DEFAULT_CONFIG['name'])
        self.inputs = config.get('input', [])
        self.output_dir = output.get('directory')
        self.output_pattern = output.get('pattern', DEFAULT_CONFIG['pattern'])
        self.cover_size = extras.get('cover', DEFAULT_CONFIG['cover'])

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

        # Step 1: Transcode
        task.result, task.skipped = worker(
            task.source,
            os.path.join(self.output_dir, task.target)
        )

        # Step 1a: Process extras (cover art, lyrics)
        if self.cover_size:
            Thread(
                target=copy_coverart,
                kwargs=dict(task=task, size=self.cover_size)
            ).start()

        # Handle skipped transcodes
        if task.skipped:
            if os.path.getmtime(task.result) > self.timestamp:
                raise RuntimeError('Target path collision for {}'.format(task.result))
            self.stats.record_skip()
            log.debug('Skipped {task}'.format(task=task))
            return

        # Step 2: Copy music tags
        result = mutagen.File(task.result, easy=True)
        result.tags.update(task.tags)  # TODO: drop blacklisted tags (embedded image)
        result.save()

        self.stats.record_done()
        log.debug('Finished {task}'.format(task=task))


    @property
    def timestamp(self):
        '''
        Date and time of starting the first transcoding task in this job
        (in Unix time format)
        '''
        return self._timestamp
