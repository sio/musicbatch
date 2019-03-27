'''
Handle lyrics associated with the transcoding task
'''


import os.path
from shutil import copyfile

from transcoder.util import safe_filepath



def locate_lyrics(task):  # TODO: finish this stub
    '''
    Find lyrics file related to the transcoding task

    Return file path or None if nothing is found
    '''
    # Detect lyrics storage
    lyrics_dir = '' # stub

    # Detect artist and title
    artist, title = '', ''  # stub

    # Build candidate path (use safe_filepath)
    path = os.path.join(lyrics_dir, safe_filepath('{artist}-{title}.txt'.format(**locals())))  # handle os.sep()

    # Return filename (break early from loop)
    if os.path.exists(path):
        return path



def copy_lyrics(task):
    '''
    Copy lyrics for the transcoding task
    '''
    if not task.result:
        raise ValueError('can not process a task that is not finished yet')
    source = locate_lyrics(task)
    if source:
        destination = os.path.splitext(task.result)[0] + '.txt'
        if not skip_action(source, destination):
            make_target_directory(destination)
            copyfile(source, destination)
