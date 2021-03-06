'''
CLI application for transcoding music files
'''


import os
import json
import platform
import time
import sys
from argparse import ArgumentParser
from contextlib import contextmanager
from datetime import datetime
from functools import partial
from pkg_resources import resource_string
from subprocess import Popen, DEVNULL
from threading import Thread

import mutagen
from jsonschema import Draft7Validator as JSONSchemaValidator
from ruamel import yaml

from musicbatch.transcoder import (
    CONFIG_ENCODING,
    DEFAULT_CONFIG,
    LOSSLESS_EXTENSIONS,
)
from musicbatch.transcoder.encoders import (
    AACTranscoder,
    LameTranscoder,
    OpusTranscoder,
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

    if args.newconfig:
        with open(args.config, 'wb') as config:
            config.write(resource_string(__name__.rsplit('.', 1)[0], 'sample.yml'))
        edit_file(args.config)
        return

    job = TranscodingJob(args.config)
    tasks = TranscodingQueue(job.inputs, job.output_pattern)

    with restore_stdin():
        show_progress(job)   # start progress report thread
        execute_in_threadqueue(job.transcode, tasks, buffer_size=20)
        job.finished = True  # terminate progress report thread
        job.write_report()



def parse_args(*a, prog=None, **ka):
    parser = ArgumentParser(
        description='Batch transcode music files according to the provided configuration file',
        epilog='This program relies on FFmpeg <http://ffmpeg.org> for audio encoding. Please make sure it\'s installed',
        prog=prog,
    )
    parser.add_argument(
        'config',
        metavar='CONFIG',
        help='Path to YAML description of the transcoding job',
    )
    parser.add_argument(
        '--newconfig',
        action='store_true',
        default=False,
        help='Create new configuration file from template and open it for editing',
    )
    args = parser.parse_args(*a, **ka)
    if args.newconfig and os.path.exists(args.config):
        parser.error('File already exists: {}'.format(args.config))
    return args



@contextmanager
def restore_stdin():
    '''Restore standard input in terminal (pydub's subprocesses mess with it)'''
    stdin, stdout, stderr = sys.stdin, sys.stdout, sys.stderr
    yield
    try:
        Popen(['stty', 'echo'], stdout=DEVNULL, stderr=DEVNULL)
    except Exception:
        pass
    sys.stdin, sys.stdout, sys.stderr = stdin, stdout, stderr



def edit_file(path):
    '''
    Open text file for editing in default application. Current script process
    will be immediately terminated and replaced with editor.
    '''
    try:
        os.startfile(path)
    except AttributeError:
        if platform.system() == 'Darwin':
            command = ['open', path]
        elif os.environ.get('EDITOR'):
            command = [os.environ.get('EDITOR'), path]
        elif os.environ.get('VISUAL'):
            command = [os.environ.get('VISUAL'), path]
        else:
            command = ['xdg-open', path]
        os.execvp(command[0], command)



class TranscodingJob:
    '''Store essential parameters of the transcoding job'''

    ENCODERS = {
        None: VorbisTranscoder,
        'copy': VerbatimFileCopy,
        'symlink': SymlinkCreator,
        'vorbis': VorbisTranscoder,
        'lame': LameTranscoder,
        'mp3': LameTranscoder,
        'aac': AACTranscoder,
        'm4a': AACTranscoder,
        'opus': OpusTranscoder,
    }


    def __init__(self, config_file):
        '''Initialize transcoding job'''
        self.stats = TranscodingStats()
        self.finished = False
        self.config_file = config_file
        self._timestamp = None

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
        if output.get('category_blacklist'):
            self.select_mode = 'blacklist'
            self.select = set(output.get('category_blacklist'))
        elif output.get('category_whitelist'):
            self.select_mode = 'whitelist'
            self.select = set(output.get('category_whitelist'))
        else:
            self.select_mode = None
            self.select = set()

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
        elif lossy_action == 'skip':
            skip_marker = self.transcoder.STATUS_SKIP
            self.lossy_action = lambda infile, outfile: (infile, skip_marker)
            self.lossy_action.STATUS_SKIP = skip_marker

        os.makedirs(self.output_dir, exist_ok=True)
        log.debug('Initialized {}'.format(self))


    def __repr__(self):
        return '{cls}({config!r})'.format(
            cls=self.__class__.__name__,
            config=self.config_file,
        )


    def transcode(self, task):
        '''Execute a single transcoding task'''
        log.debug('Started {task}'.format(task=task))

        if (self.select_mode == 'blacklist' and self.select.intersection(task.categories)) \
        or (self.select_mode == 'whitelist' and not self.select.intersection(task.categories)):
            self.stats.record_skip()
            log.debug('Skipped {task}'.format(task=task))
            return

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
            for key in task.tags.keys():  # mutagen is inconsistent about `for k in t.tags`
                if hasattr(result.tags, 'valid_keys') \
                and key not in result.tags.valid_keys:
                    continue
                result.tags[key] = task.tags[key]
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
        '''Validate transcoding job configuration'''
        try:
            self.validator
        except AttributeError:
            package = __name__.rsplit('.', 1)[0]
            path = 'schema.json'
            schema = json.loads(resource_string(package, path).decode())
            self.validator = JSONSchemaValidator(schema)

        error_messages = []
        for error in self.validator.iter_errors(config):
            error_messages.append(' - {}: {}'.format(
                    '.'.join(error.path) if error.path else '[config]',
                    error.message
            ))
        if error_messages:
            raise ValueError('invalid configuration values:\n{}'.format(
                    '\n'.join(sorted(error_messages))
            ))
