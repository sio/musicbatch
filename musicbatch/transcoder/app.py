'''
CLI application for transcoding music files
'''


import os
import json
import time
import sys
from argparse import ArgumentParser
from contextlib import contextmanager
from datetime import datetime
from functools import partial
from pkg_resources import resource_string
from subprocess import Popen, DEVNULL
from threading import Thread

import jsonschema
import mutagen
from ruamel import yaml

from musicbatch.transcoder import (
    CONFIG_ENCODING,
    DEFAULT_CONFIG,
    LOSSLESS_EXTENSIONS,
)
from musicbatch.transcoder.encoders import (
    SymlinkCreator,
    VerbatimFileCopy,
    VorbisTranscoder,
)
from musicbatch.transcoder.cover import copy_coverart
from musicbatch.transcoder.lyrics import copy_lyrics, read_lyrics
from musicbatch.transcoder.progress import (
    TranscodingStats,
    show_progress,
)
from musicbatch.transcoder.queue import (
    TranscodingQueue,
    execute_in_threadqueue,
)
from musicbatch.lyrics.db import LyricsStorage



import logging
log = logging.getLogger(__name__)



def run(*a, **ka):
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

    args = parse_args(*a, **ka)
    job = TranscodingJob(args.config)
    tasks = TranscodingQueue(job.inputs, job.output_pattern)

    with restore_stdin():
        show_progress(job)   # start progress report thread
        execute_in_threadqueue(job.transcode, tasks, buffer_size=20)
        job.finished = True  # terminate progress report thread
        job.write_report()



def parse_args(*a, **ka):
    parser = ArgumentParser(description='Batch transcode music files according to the provided config')
    parser.add_argument(
        'config',
        help='Path to YAML description of the transcoding job',
    )
    return parser.parse_args(*a, **ka)



@contextmanager
def restore_stdin():
    stdin, stdout, stderr = sys.stdin, sys.stdout, sys.stderr
    yield
    try:
        # Restore standard input in terminal (pydub's subprocesses mess with it)
        Popen(['stty', 'echo'], stdout=DEVNULL, stderr=DEVNULL)
    except Exception:
        pass
    sys.stdin, sys.stdout, sys.stderr = stdin, stdout, stderr



class TranscodingJob:
    '''Store essential parameters of the transcoding job'''

    ENCODERS = {
        None: VorbisTranscoder,
        'copy': VerbatimFileCopy,
        'symlink': SymlinkCreator,
        'vorbis': VorbisTranscoder,
    }


    def __init__(self, config_file):
        '''Initialize transcoding job'''
        self.stats = TranscodingStats()
        self.finished = False
        self.config_file = config_file
        self._timestamp = None

        # TODO: validate config file against schema

        with open(config_file, encoding=CONFIG_ENCODING) as f:
            config = yaml.load(f, Loader=yaml.RoundTripLoader)
            output = config.get('output', {})
            extras = config.get('extras', {})

        self.validate(config)

        self.job_id = config.get('name', DEFAULT_CONFIG['name'])
        self.inputs = config.get('input', [])
        self.output_dir = output.get('directory')
        self.output_pattern = output.get('pattern', DEFAULT_CONFIG['pattern'])
        self.cover_size = extras.get('cover', DEFAULT_CONFIG['cover'])

        lyrics_source = extras.get('lyrics', DEFAULT_CONFIG['lyrics'])
        if not lyrics_source:
            self.get_lyrics = None
        elif os.path.isdir(lyrics_source):
            self.get_lyrics = partial(read_lyrics, lyricsdir=lyrics_source)
        elif os.path.isfile(lyrics_source):
            database = LyricsStorage(lyrics_source)
            self.get_lyrics = database.get
        else:
            self.get_lyrics = None

        encoder = output.get('format', DEFAULT_CONFIG['format'])
        quality = output.get('quality', DEFAULT_CONFIG['quality'])
        self.transcoder = self.ENCODERS.get(encoder)(quality)

        lossy_action = output.get('lossy_source', DEFAULT_CONFIG['lossy_source'])
        if lossy_action == 'allow_bad_transcodes'\
        or encoder == 'symlink' \
        or encoder == 'copy':
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
        task.result, task.status = worker(
            task.source,
            os.path.join(self.output_dir, task.target)
        )

        # Step 1a: Process extras (cover art, lyrics)
        if self.cover_size:
            Thread(
                target=copy_coverart,
                kwargs=dict(task=task, size=self.cover_size)
            ).start()
        if self.get_lyrics:
            Thread(
                target=copy_lyrics,
                kwargs=dict(task=task, lyrics_finder=self.get_lyrics),
            ).start()

        # Handle skipped transcodes
        if task.status is worker.STATUS_SKIP:
            if os.path.getmtime(task.result) > self.timestamp:
                raise RuntimeError('Target path collision for {}'.format(task.result))
            self.stats.record_skip()
            log.debug('Skipped {task}'.format(task=task))
            return

        # Step 2: Copy music tags
        if not task.status is worker.STATUS_SKIPTAGS:
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


    def write_report(self):
        '''Keep a journal of transcoder runs'''
        log_entry = '{time}Z: {stats}\n'.format(
            time = datetime.utcnow().replace(microsecond=0),
            stats = self.stats.show().strip(),
        )
        with open(os.path.join(self.output_dir, 'transcoding.log'), 'a') as logfile:
            logfile.write(log_entry)


    def validate(self, config):
        try:
            schema = self.schema
        except AttributeError:
            package = __name__.rsplit('.', 1)[0]
            path = 'schema.json'
            schema = self.schema = json.loads(resource_string(package, path).decode())
        return jsonschema.validate(config, schema)
