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
