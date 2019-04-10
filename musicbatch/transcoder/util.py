'''
Utilities for internal use
'''


import os
import re

from musicbatch import transcoder



def find_music(directories):
    '''Traverse file tree in alphabetical order (top down) and return music file paths'''
    for directory in sorted(directories):
        for root, dirs, files in os.walk(directory, followlinks=True, topdown=True):
            dirs.sort()  # ensure alphabetical traversal
            for filename in sorted(files):
                if is_music(filename):
                    yield os.path.join(root, filename)



def is_music(filename):
    '''Check if file is a music file'''
    try:
        extension = os.path.splitext(filename)[1][1:].lower()
        return extension in transcoder.KNOWN_EXTENSIONS
    except IndexError:
        return False



def mtime(filename):
    '''
    Get modification time of file (unix timestamp).
    Return zero if file does not exist.
    '''
    try:
        return os.lstat(filename).st_mtime
    except FileNotFoundError:
        return 0



def skip_action(input_filename, output_filename):
    '''Detect whether the transcoding can be skipped'''
    input_mtime, output_mtime = map(
        mtime,
        (input_filename, output_filename)
    )
    return input_mtime <= output_mtime



def make_target_directory(output_filename):
    '''Make sure that directory for this file exists'''
    target = os.path.dirname(output_filename)
    os.makedirs(target, exist_ok=True)



_bad_characters = re.compile(r'[^\w\d !.()_+-]')
def safe_filename(name, placeholder=''):
    '''Convert arbitrary filename into a safe version suitable for any file system'''
    return _bad_characters.sub(placeholder, name)
