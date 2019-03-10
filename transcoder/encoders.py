'''
Workers for transcoding music into different target formats
'''


import os.path
import re

import mutagen
from pydub import AudioSegment



class Transcoder:
    '''Generic base class for transcoders'''


    def __init__(self, quality=None, copy_tags=False, *a, **ka):
        self.export_params = self.configure(quality, *a, **ka)
        self.copy_tags = copy_tags


    def configure(self, quality, *a, **ka):
        '''
        Configure export parameters.

        Must be implemented in each child class.
        Must return dictionary with valid values for self.export_params.
        '''
        raise NotImplementedError


    def __call__(self, input_filename, output_filename):
        '''Transcode file from one format to another'''
        input_format = input_filename.rsplit('.')[1].lower()  # ffmpeg format names usually match extension
        audio = AudioSegment.from_file(input_filename, input_format)

        self.make_target_directory(output_filename)
        audio.export(output_filename, **self.export_params)

        if self.copy_tags:
            # Do not copy tags unless explicitly asked to
            tags = mutagen.File(input_filename, easy=True).tags
            exported = mutagen.File(output_filename, easy=True)
            exported.tags.update(tags)
            exported.save()


    @staticmethod
    def make_target_directory(output_filename):
        target = os.path.dirname(output_filename)
        if not os.path.exists(target):
            os.makedirs(target)



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
