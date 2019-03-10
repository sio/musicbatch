'''
CLI application for transcoding music files
'''


from ruamel import yaml

from transcoder.encoders import (
    VorbisTranscoder,
)



def run():
    '''
    CLI entry point
    '''


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


def find_files(directory):
    '''
    Find valid music files in a given directory
    '''


def copy_with_tags():
    ''''''
