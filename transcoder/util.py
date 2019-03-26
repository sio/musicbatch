'''
Utilities for internal use
'''

import os
import re



def mtime(filename):
    '''
    Get modification time of file (unix timestamp).
    Return zero if file does not exist.
    '''
    try:
        return os.path.getmtime(filename)
    except FileNotFoundError:
        return 0



def skip_action(input_filename, output_filename):
    '''Detect whether the transcoding can be skipped'''
    input_mtime, output_mtime = map(
        mtime,
        (input_filename, output_filename)
    )
    return input_mtime < output_mtime



def make_target_directory(output_filename):
    '''Make sure that directory for this file exists'''
    target = os.path.dirname(output_filename)
    if not os.path.exists(target):
        try:
            os.makedirs(target)
        except FileExistsError:  # another thread has already created the directory
            pass



_bad_characters = re.compile(r'[^\w\d%s !.()_+-]' % os.sep)
def safe_filepath(path):
    '''Convert arbitrary file path into a safe version suitable for any file system'''
    placeholder = ''
    return _bad_characters.sub(placeholder, path)
