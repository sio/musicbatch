'''
Handle lyrics associated with the transcoding task
'''


import os.path
from shutil import copyfile

from musicbatch.transcoder.util import safe_filepath



def read_lyrics(artist, title, lyricsdir='$HOME/.lyrics'):  # TODO: finish this stub
    '''
    Get song lyrics from text files in lyrics directory
    '''
    filenames = [
        '{artist}-{title}.txt',
        '{artist} - {title}.txt',
    ]
    if not artist or not title:
        return
    for artist, title in (
        (artist, title),
        map(safe_filepath, (artist, title)),
    ):
        for filename in filenames:
            fullpath = os.path.join(
                os.path.expandvars(lyricsdir),
                filename.format(artist=artist, title=title)
            )
            if os.path.exists(fullpath):
                with open(fullpath) as lyrics:
                    return lyrics.read()



def copy_lyrics(task, lyrics_finder=None):
    '''
    Copy lyrics for the transcoding task
    '''
    if not task.result:
        raise ValueError('can not process a task that is not finished yet')
    if lyrics_finder is None:
        lyrics_finder = read_lyrics
    destination = os.path.splitext(task.result)[0] + '.txt'
    if not os.path.exists(destination):
        try:
            artist = task.tags['artist'][0]
            title = task.tags['title'][0]
        except Exception:
            artist = task.path_elements['artist']
            title = task.path_elements['title']
        text = lyrics_finder(artist, title)
        if text:
            make_target_directory(destination)
            with open(destination, 'w') as f:
                f.write(text)
