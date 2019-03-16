'''
CLI application for transcoding music files
'''


import os.path

import mutagen
from ruamel import yaml

from transcoder.encoders import (
    VorbisTranscoder,
)



def run():
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



class TranscodingTask:
    '''Stores information required to transcode a single music file'''


    pattern = None  # must set from outside once for all tasks


    def __init__(self, filename, seq_number=1, target_dir=None):
        self.source = filename
        self.source_dir = os.path.dirname(filename)
        self.number = seq_number

        self._metadata = None
        self._tags = None
        self._path_elements = None
        self._target = None
        self._target_dir = target_dir

        if self.pattern is None:
            raise ValueError(
                'Can not use {cls} without setting pattern value first'.format(
                    cls=self.__class__.__name__
                )
            )


    def __repr__(self):
        return '{cls}({filename})'.format(
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
                self._metadata = Metadata(filename=candidate_path).data
        if self._metadata is None:
            self._metadata = {}  # fallback value
        return self._metadata



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



class TranscodingJob:
    '''Store essential parameters of the transcoding job'''

    ENCODERS = {
        None: VorbisTranscoder,
        'vorbis': VorbisTranscoder,
    }


    def __init__(self, config_file):
        '''Initialize transcoding job'''
        self.config_file = config_file

        with open(config_file) as f:
            config = yaml.load(f, Loader=yaml.RoundTripLoader)
            output = config.get('output', {})

        self.job_id = config.get('name')
        self.inputs = config.get('input', [])
        self.output_dir = output.get('directory')
        self.output_pattern = output.get(
                                'pattern',
                                '{artist} - {year} - {album}/{number} {title}'
                              )
        self.lossy_action = output.get('lossy_source')  # TODO: replace with function

        encoder = output.get('format', 'vorbis')
        quality = output.get('quality')
        self.transcoder = self.ENCODERS.get(encoder)(quality)


    def __repr__(self):
        return '{cls}({config!r})'.format(
            cls=self.__class__.__name__,
            config=self.config_file,
        )



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


def find_files(directory):
    '''
    Find valid music files in a given directory
    '''


def copy_with_tags():
    ''''''
