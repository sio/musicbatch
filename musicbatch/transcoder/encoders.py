'''
Workers for transcoding music into different target formats
'''


import os
import re
from shutil import copyfile

from pydub import AudioSegment

from musicbatch.transcoder.util import (
    make_target_directory,
    skip_action,
)
from musicbatch.metadata import METADATA_DIRECTORY



class SpecialValue:
    '''Dummy objects that are always compared via "is-a" instead of "equals"'''
    __slots__ = ()



class TranscoderConstants:
    '''Some constants for all transcoder-like objects'''
    STATUS_OK = SpecialValue()
    STATUS_SKIP = SpecialValue()
    STATUS_SKIPTAGS = SpecialValue()


class Transcoder(TranscoderConstants):
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

        make_target_directory(output_filename)
        if not skip_action(input_filename, output_filename):
            # ffmpeg format names usually match extension
            input_format = os.path.splitext(input_filename)[1][1:].lower()
            AudioSegment \
                .from_file(input_filename, input_format) \
                .export(output_filename, **self.export_params)
            status = self.STATUS_OK
        else:
            status = self.STATUS_SKIP
        return output_filename, status


    def __repr__(self):
        return '<{cls}(quality={quality!r})>'.format(
            cls = self.__class__.__name__,
            quality = self.quality,
        )



class VorbisTranscoder(Transcoder):
    '''Transcoder for Ogg Vorbis target'''
    valid_quality = re.compile(r'^q\s*([0-9]0?)$')


    def configure(self, quality, *a, **ka):
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



class LameTranscoder(Transcoder):
    '''Transcoder for LAME MP3 target'''
    valid_quality = re.compile(r'^V\s*([0-9])$', re.IGNORECASE)


    def configure(self, quality, *a, **ka):
        if quality is None: quality = 'V0'
        parsed = self.valid_quality.match(quality.strip())
        if parsed:
            numeric_quality = parsed.group(1)
        else:
            raise ValueError('Invalid quality value: {}'.format(quality))
        return {
            'format': 'mp3',
            'codec': 'libmp3lame',
            'parameters': ['-aq', numeric_quality],
        }



class AACTranscoder(Transcoder):
    '''Transcoder for AAC target'''
    valid_quality = re.compile(r'^V\s*([12345])$', re.IGNORECASE)


    def __init__(self, quality=None, *a, **ka):
        super().__init__(quality, *a, **ka)
        self.extension = 'm4a'


    def configure(self, quality, *a, **ka):
        if quality is None: quality = 'V5'
        parsed = self.valid_quality.match(quality.strip())
        if parsed:
            numeric_quality = parsed.group(1)
        else:
            raise ValueError('Invalid quality value: {}'.format(quality))
        return {
            'format': 'aac',
            'codec': 'libfdk_aac',
            'parameters': ['-vbr', numeric_quality],
        }



class OpusTranscoder(Transcoder):
    '''Transcoder for Opus target'''
    valid_quality = re.compile(r'^([0-9]+)\s*k$', re.IGNORECASE)


    def configure(self, quality, *a, **ka):
        if quality is None: quality = '96k'
        parsed = self.valid_quality.match(quality.strip())
        if parsed:
            numeric_quality = parsed.group(1)
        else:
            raise ValueError('Invalid quality value: {}'.format(quality))
        return {
            'format': 'opus',
            'codec': 'libopus',
            'parameters': ['-ab', numeric_quality],
        }



class VerbatimFileCopy(TranscoderConstants):
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
        make_target_directory(output_filename)
        if not skip_action(input_filename, output_filename):
            copyfile(input_filename, output_filename)
            status = self.STATUS_SKIPTAGS  # no need to copy tags
        else:
            status = self.STATUS_SKIP
        return output_filename, status


    def __repr__(self):
        return '<{cls}()>'.format(
            cls = self.__class__.__name__,
        )



class SymlinkCreator(VerbatimFileCopy):
    '''
    Transcoder-like object that does no transcoding but instead creates
    symlinks to original music files

    This is useful for organizing a nice file layout from messy storage
    (e.g. torrents directory)
    '''

    def __call__(self, input_filename, output_filename):
        extension = os.path.splitext(input_filename)[1].lower()
        if not output_filename.lower().endswith(extension):
            output_filename += extension
        make_target_directory(output_filename)
        if not skip_action(input_filename, output_filename):
            if os.path.exists(output_filename):
                os.remove(output_filename)
            os.symlink(input_filename, output_filename)
            status = self.STATUS_SKIPTAGS
        else:
            status = self.STATUS_SKIP
        meta_dir = os.path.join(os.path.dirname(input_filename), METADATA_DIRECTORY)
        if os.path.exists(meta_dir) :
            meta_dest = os.path.join(os.path.dirname(output_filename), METADATA_DIRECTORY)
            try:
                os.symlink(meta_dir, meta_dest)
            except OSError:
                pass
        return output_filename, status
