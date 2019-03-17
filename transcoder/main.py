'''
CLI application for transcoding music files
'''


import os
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

    workers_num = os.cpu_count()
    queue = Queue(maxsize=workers_num * 5)  # Ensure there is enough tasks scheduled, but not too many
    threads = []

    # NOTE: ThreadPoolExecutor and multiprocessing.Pool.imap_unordered are greedy.
    #       They consume the whole generator before starting processing its values,
    #       hence the Queue approach.

    def worker():
        while True:
            task = queue.get()
            if task is None:
                break
            job.transcode(task)
            queue.task_done()

    for i in range(workers_num):  # create worker threads
        t = Thread(target=worker)
        t.start()
        threads.append(t)

    for task in tasks:  # queue tasks at the sane pace
        queue.put(task)

    queue.join()  # block until all tasks are done

    for i in range(workers_num):  # stop workers
        queue.put(None)
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
