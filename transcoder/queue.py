'''
Non-greedy queueing of transcoding tasks
'''


import os
from queue import Queue
from threading import Thread

import mutagen
import transcoder

from hods import Metadata, TreeStructuredData


import logging
log = logging.getLogger(__name__)



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
            try:
                function(task)
            finally:
                queue.task_done()

    def safe_worker():
        try:
            worker()
        except Exception as e:
            start_worker_thread()
            raise e

    def start_worker_thread():
        t = Thread(target=safe_worker)
        t.start()
        threads.append(t)

    for i in range(num_threads):  # create worker threads
        start_worker_thread()

    for task in args_seq:  # queue tasks at the sane pace
        if task is break_value:
            raise ValueError('Break value can never occur in the args_seq')
        queue.put(task)

    queue.join()  # block until all tasks are done

    for i in range(num_threads):  # stop workers
        queue.put(break_value)
    for t in threads:
        t.join()



class TranscodingQueue:
    '''Queue of files to be transcoded'''

    def __init__(self, directories, pattern):
        self.directories = directories
        self.pattern = pattern
        self.prev_task = None
        self.files = self.traverse(directories)
        log.debug('Initialized {}'.format(self))


    def __repr__(self):
        return '{cls}({dirs})'.format(
            cls = self.__class__.__name__,
            dirs = list(self.directories),
        )


    def __next__(self):
        next_file = next(self.files)
        prev_task = self.prev_task
        number = 0
        next_target_dir = None
        metadata = {}


        if prev_task is not None \
        and os.path.dirname(next_file) == prev_task.source_dir:
            # files from same directory always go to the same target
            # and share the same Metadata object
            metadata = prev_task.metadata
            next_target_dir = prev_task.target_dir
            number = prev_task.number

        next_task = TranscodingTask(
                        filename = next_file,
                        pattern = self.pattern,
                        seq_number = number + 1,
                        target_dir = next_target_dir
        )
        next_task.metadata = metadata
        self.prev_task = next_task
        return next_task


    def __iter__(self):
        return self


    def traverse(self, directories):
        '''Traverse file tree in alphabetical order (top down)'''
        for directory in sorted(directories):
            for root, dirs, files in os.walk(directory, followlinks=True, topdown=True):
                dirs.sort()  # ensure alphabetical traversal
                for filename in sorted(files):
                    if self.validate(filename):
                        yield os.path.join(root, filename)


    def validate(self, filename):
        '''Check if file is eligible for transcoding'''
        try:
            extension = os.path.splitext(filename)[1][1:].lower()
            return extension in transcoder.KNOWN_EXTENSIONS
        except IndexError:
            return False



class TranscodingTask:
    '''Stores information required to transcode a single music file'''


    def __init__(self, filename, pattern, seq_number=1, target_dir=None):
        self.source = filename
        self.source_dir = os.path.dirname(filename)
        self.pattern = pattern
        self.number = seq_number

        self.result = None  # store full path to the result when task is done
        self.skipped = None # indicate skipped task

        self._metadata = None
        self._tags = None
        self._path_elements = None
        self._target = None
        self._target_dir = target_dir

        log.debug('Initialized {}'.format(self))


    def __repr__(self):
        return '{cls}({filename!r})'.format(
            cls = self.__class__.__name__,
            filename = self.source,
        )


    @property
    def target(self):
        '''Relative path to the transcoding destination file'''
        if self._target is not None:
            return self._target

        target = self.pattern.format(**self.path_elements)
        if self._target_dir is not None:
            target = os.path.join(self._target_dir, os.path.basename(target))

        self._target = target
        return self._target


    @property
    def target_dir(self):
        if self._target_dir is None:
            self._target_dir = os.path.dirname(self.target)
        return self._target_dir


    @property
    def tags(self):
        '''Read music tags from file headers'''
        # Values from metadata file are ignored intentionally:
        #  - There is no point using "Various Artists" placeholder for
        #    individual tracks
        #  - Track title and album name are assumed to be correct in source
        #    tags
        #  - Genre, year and other less important tags are not worth the
        #    special treatment
        if self._tags is None:
            self._tags = mutagen.File(self.source, easy=True).tags
        return self._tags


    @property
    def metadata(self):
        '''Metadata object (if any)'''
        if self._metadata is not None:
            return self._metadata

        metadata_filename = 'album_hods.yml'
        possible_paths = ['.', '..']

        for subdir in possible_paths:
            candidate_path = os.path.join(self.source_dir, subdir, metadata_filename)
            if os.path.exists(candidate_path):
                # TODO: handle jsonschema.exceptions.ValidationError
                # TODO: handle hash mismatch in metadata file
                log.debug('Reading metadata from {}'.format(candidate_path))
                self._metadata = Metadata(filename=candidate_path).data
        if self._metadata is None:
            self._metadata = {}  # fallback value
        return self._metadata


    @metadata.setter
    def metadata(self, value):
        if isinstance(value, TreeStructuredData):
            log.debug('Reusing metadata object for {}'.format(self.source))
            self._metadata = value
        elif value == {}:
            pass
        else:
            raise TypeError('Expected a TreeStructuredData object, got {}'.format(
                value.__class__.__name__
            ))


    @property
    def path_elements(self):
        '''Calculate target path elements for transcoding this file'''
        if self._path_elements is not None:
            return self._path_elements

        allowed_fields = {
            'artist',
            'album',
            'year',
            'title',
            'genre',
            # 'number' field is calculated by sort order
        }

        elements = {}
        elements['number'] = '{:02d}'.format(self.number)
        for field in allowed_fields:
            for container in (self.metadata, self.tags):
                if elements.get(field):
                    continue
                elements[field] = value(get(container, field))

        self._path_elements = elements
        return self._path_elements



def value(string_or_list):
    '''
    Get string value from a variable that might contain string or list of
    strings
    '''
    if isinstance(string_or_list, str):
        result = string_or_list
    elif string_or_list is None or len(string_or_list) == 0:
        result = ''
    elif len(string_or_list) == 1:
        result = str(string_or_list[0])
    else:
        result = ', '.join(string_or_list)
    return result.strip()



def get(container, key, default=None):
    '''Helper function for dict-like access to object attributes'''
    try:
        return container.get(key, default)
    except AttributeError:
        try:
            return getattr(container, key)
        except AttributeError:
            return default
