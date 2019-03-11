'''
CLI application for transcoding music files
'''


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

    def __init__(self, filename, metadata=None):
        self.source = filename
        self.metadata = metadata.data if metadata else {}  # hods object
        self.tags = self.read_tags()
        self.path_elements = self.calculate_path_elements()


    def __repr__(self):
        return '{cls}({filename})'.format(
            cls = self.__class__.__name__,
            filename = self.source,
        )


    def read_tags(self):
        '''Read music tags from file headers'''
        # Values from metadata file are ignored intentionally:
        #  - There is no point using "Various Artists" placeholder for
        #    individual tracks
        #  - Track title and album name are assumed to be correct in source
        #    tags
        #  - Genre, year and other less important tags are not worth the
        #    special treatment
        tags = mutagen.File(self.source, easy=True).tags
        return tags


    def calculate_path_elements(self):
        '''Calculate target path elements for transcoding this file'''
        allowed_fields = {
            'artist',
            'album',
            'year',
            'number',
            'title',
            'genre',
        }

        elements = {}
        for field in allowed_fields:
            meta_value = self.metadata.get(field)
            if meta_value:
                elements[field] = value(meta_value)
                continue

            if field == 'number': field = 'tracknumber'
            tag_value = self.tags.get(field)
            if tag_value:
                elements[field] = value(tag_value)
                # TODO: add zero-padding for tracknumber
                continue

        return elements



class TranscodingJob:
    '''Store essential parameters of the transcoding job'''

    ENCODERS = {
        None: VorbisTranscoder,
        'vorbis': VorbisTranscoder,
    }
    LOSSY_EXTENSIONS = {'ogg', 'mp3', 'aac'}
    LOSSLESS_EXTENSIONS = {'flac', 'ape', 'wav', 'pcm', 'raw'}
    KNOWN_EXTENSIONS = LOSSY_EXTENSIONS | LOSSLESS_EXTENSIONS


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
        return string_or_list
    elif len(string_or_list) == 1:
        return string_or_list[0]
    else:
        return ', '.join(string_or_list)


def find_files(directory):
    '''
    Find valid music files in a given directory
    '''


def copy_with_tags():
    ''''''
