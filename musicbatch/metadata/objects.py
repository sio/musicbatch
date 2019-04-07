'''
Reusable metadata objects for music files
'''


import os
import json
import logging
from collections import OrderedDict, defaultdict

import mutagen

from hods import Metadata
from musicbatch.transcoder.util import is_music
from musicbatch.metadata import (
    METADATA_WHATCD,
    METADATA_YAML,
    VARIOUS_ARTISTS,
)
from musicbatch.metadata.whatcd import WhatAPIResponse

log = logging.getLogger(__name__)



class MusicAlbumInfo(Metadata):
    '''
    Manipulate music metadata with HODS
    '''
    _SUPPORTED_SCHEMAS = [  # first one is used for creating empty objects
        'https://hods.ml/schemas/music-album-v1.json',
    ]
    _EMPTY_JSON = '''
        {
          "album": "...",
          "artist": "",
          "year": "0000",
          "image_url": "",
          "genre": "",
          "comment": "",
          "composer": "",
          "orig_artist": "",
          "cd": "",
          "tracks": []
        }
    '''

    def __init__(self, data=None, filename=None, fileformat=None, fromdir=None):
        if data is None and filename is None:
            load = lambda x: json.loads(x, object_pairs_hook=OrderedDict)
            payload = load(self._EMPTY_JSON)
            data = load(Metadata._EMPTY_JSON)
            data['data'] = payload
            data['info']['schema']['data'] = self._SUPPORTED_SCHEMAS[0]

        super().__init__(data, filename, fileformat)

        schema = self.info.schema.data
        if schema not in self._SUPPORTED_SCHEMAS:
            raise ValueError('schema is not supported: {}'.format(schema))

        if fromdir:
            self._parsedir(fromdir)


    def _parsedir(self, dirname):
        '''Parse tags for all files in the directory (non-recursive)'''
        album_info = OrderedDict((
            # MusicAlbumInfo field: mutagen easy field
            ('album', 'album'),
            ('artist', 'albumartist'),
            ('year', 'date'),
            ('genre', 'genre'),
            ('cd', 'discnumber'),
            ('comment', 'comment'),
        ))
        track_info = OrderedDict((
            ('number', 'tracknumber'),
            ('title', 'title'),
            ('artist', 'artist'),
        ))

        basedir, _, files = next(os.walk(dirname))
        album_collected = defaultdict(set)
        tracks_collected = list()

        # Read information from music files
        for filename in sorted(files):
            filename = os.path.join(basedir, filename)
            if not is_music(filename):
                continue
            audio = mutagen.File(filename, easy=True)
            if not audio or not audio.tags:
                continue
            tags = audio.tags
            for meta_attr, tag_attr in album_info.items():
                value = tags.get(tag_attr)
                if value and not isinstance(value, str):
                    value = value.pop()  # use first of multiple values
                if value:
                    album_collected[meta_attr].add(value)
            track = OrderedDict()
            for meta_attr, tag_attr in track_info.items():
                value = tags.get(tag_attr)
                if value and not isinstance(value, str):
                    value = value.pop()  # use first of multiple values
                if not value:
                    value = ''
                track[meta_attr] = value
            tracks_collected.append(track)

        # Analyze and extract information about the whole album
        for field, values in album_collected.items():
            if len(values) == 1:
                value = values.pop()
            elif len(values) == 0:
                value = ''
            elif len(values) > 1:
                value = ', '.join(sorted(values))
            setattr(self.data, field, value)

        # Detect album artist
        if not self.data.artist and len(tracks_collected):
            track_artists = set()
            for track in tracks_collected:
                track_artists.add(track['artist'])
            if len(track_artists) == 1:
                self.data.artist = track_artists.pop()
            elif len(track_artists) > 1:
                self.data.artist = VARIOUS_ARTISTS
            else:
                raise ValueError('no artist defined for: {}'.format(dirname))

        # Do not write the same artist name into each track
        for track in tracks_collected:
            if track['artist'] == self.data.artist:
                track['artist'] = ''

        # Parse archived What.CD API response (if any)
        json_file = os.path.join(dirname, METADATA_WHATCD)
        if os.path.exists(json_file):
            whatcd = WhatAPIResponse(json_file)
            for field in ('album', 'artist', 'year'):
                value = str(getattr(whatcd, field))
                if value:
                    setattr(self.data, field, value)

        # Write the results
        self.data.tracks = tracks_collected
        self.validate_hashes(write_updates=True)



def generate(directories, target=None, recursive=False):
    '''Generate album metadata files for given directories'''
    if target is None:
        target = METADATA_YAML
    if isinstance(directories, str):
        directories = (directories,)
    for dirname in directories:
        filename = os.path.join(dirname, target)
        if os.path.exists(filename):
            log.debug('Metadata file already exists: {}'.format(filename))
            continue
        meta = MusicAlbumInfo(fromdir=dirname)
        if len(meta.data.tracks):
            meta_dir = os.path.dirname(filename)
            if not os.path.exists(meta_dir):
                os.makedirs(meta_dir)
            meta.write(filename)
            log.debug('Metadata written: {}'.format(filename))

        if recursive:
            parent, subdirs, files = next(os.walk(dirname))
            generate(
                (os.path.join(parent, subdir) for subdir in subdirs),
                recursive=recursive,
            )
