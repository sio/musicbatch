'''
Handle cover art
'''

import os
import random
import re

from PIL import Image

from musicbatch.transcoder.util import make_target_directory, skip_action



COVER_KEYWORDS = ['cover', 'folder', 'front', 'thumb', 'thumbnail']  # order matters
COVER_EXT = ['jpg', 'jpeg', 'tiff', 'tif', 'png', 'gif']
COVER_TEMPLATE = r'.*{keyword}\.({extensions})*$'
COVER_REGEX = [
    re.compile(
        COVER_TEMPLATE.format(keyword=k, extensions='|'.join(COVER_EXT)),
        re.IGNORECASE
    ) for k in COVER_KEYWORDS
]



def locate_coverart(music_file):
    '''
    Find cover art image for a music file

    Return file path or None if nothing is found
    '''
    directory = os.path.dirname(music_file)
    subdirs = [  # order matters
        'what.cd-metadata',
        os.path.join('..', 'what.cd-metadata'),
        '.',
        '..',
        os.path.basename(music_file), # just in case
    ]

    # Search for valid cover filenames in relevant subdirs
    files = {}
    for subdir in subdirs:
        try:
            files[subdir] = os.listdir(os.path.join(directory, subdir))
        except (FileNotFoundError, NotADirectoryError):
            continue
        for regex in COVER_REGEX:
            for filename in files[subdir]:
                if regex.match(filename):
                    return os.path.join(directory, subdir, filename)

    # Fallback: use a random image from relevant subdirs
    extensions = set('.{}'.format(e) for e in COVER_EXT)
    for subdir, filenames in files.items():
        images = [f for f in filenames if os.path.splitext(f)[1] in extensions]
        if images:
            return os.path.join(directory, subdir, random.choice(images))



def copy_coverart(task, size=250, name='cover.jpg', format='jpeg'):
    '''
    Copy cover art for the transcoding task
    '''
    if not task.result:
        raise ValueError('can not process a task that is not finished yet')
    source = locate_coverart(task.source)
    if source:
        destination = os.path.join(os.path.dirname(task.result), name)
        if not skip_action(source, destination):
            make_target_directory(destination)
            image = Image.open(source)
            image.thumbnail((size, size))
            image.save(destination, format=format)
