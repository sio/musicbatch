'''
Workers for transcoding music into different target formats
'''


import os.path
import re
from shutil import copyfile

from pydub import AudioSegment

from transcoder.util import (
    make_target_directory,
    safe_filepath,
    skip_action,
)



class Transcoder:
    '''Generic base class for transcoders'''


    def __init__(self, quality=None, *a, **ka):
        self.export_params = self.configure(quality, *a, **ka)
        self.extension = self.export_params['format']
        self.quality = quality


    def configure(self, quality, *a, **ka):
        '''
        Configure export parameters.

        Must be implemented in each child class.
        Must return dictionary with valid values for self.export_params.
        '''
        raise NotImplementedError


    def __call__(self, input_filename, output_filename):
        '''Transcode file from one format to another'''
        extension = '.' + self.extension.lower()
        if not output_filename.lower().endswith(extension):
            output_filename += extension

        output_filename = safe_filepath(output_filename)
        make_target_directory(output_filename)
        skip = skip_action(input_filename, output_filename)
        if not skip:
            # ffmpeg format names usually match extension
            input_format = os.path.splitext(input_filename)[1][1:].lower()
            AudioSegment \
                .from_file(input_filename, input_format) \
                .export(output_filename, **self.export_params)
        return output_filename, skip


    def __repr__(self):
        return '<{cls}(quality={quality!r}})>'.format(
            cls = self.__class__.__name__,
            quality = self.quality,
        )



class VorbisTranscoder(Transcoder):
    '''Transcoder for Ogg Vorbis target'''
    valid_quality = re.compile('^q\s*([0-9]0?)$')


    def configure(self, quality, *a, **ka):
        '''Configure export to Vorbis audio'''
        if quality is None: quality = 'q7'
        parsed = self.valid_quality.match(quality.lower())
        if parsed:
            numeric_quality = parsed.group(1)
        else:
            raise ValueError('Invalid quality value: {}'.format(quality))
        return {
            'format': 'ogg',
            'codec': 'libvorbis',
            'parameters': ['-aq', numeric_quality],
        }



class VerbatimFileCopy:
    '''
    Transcoder-like object that does no transcoding but instead just copies the
    source files.

    This is useful for avoiding bad transcodes (lossy to lossy)
    '''
    def __init__(self, quality=None, *a, **ka):
        pass


    def __call__(self, input_filename, output_filename):
        extension = '.' + os.path.splitext(input_filename)[1][1:].lower()
        if not output_filename.lower().endswith(extension):
            output_filename += extension
        output_filename = safe_filepath(output_filename)
        make_target_directory(output_filename)
        skip = skip_action(input_filename, output_filename)
        if not skip:
            copyfile(input_filename, output_filename)
        return output_filename, skip


    def __repr__(self):
        return '<{cls}()>'.format(
            cls = self.__class__.__name__,
        )
