

import os

import transcoder


class TranscodingQueue:
    '''Queue of files to be transcoded'''

    def __init__(self, directories):
        self.prev_task = None
        self.files = self.traverse(directories)


    def __next__(self):
        next_file = next(self.files)
        prev_task = self.prev_task
        number = 0
        next_target_dir = None


        if prev_task is not None \
        and os.path.dirname(next_file) == prev_task.source_dir:
            # files from same directory always go to the same target
            next_target_dir = prev_task.target_dir
            number = prev_task.number

        next_task = TranscodingTask(
                        filename = next_file,
                        seq_number = number + 1,
                        target_dir = next_target_dir
        )
        self.prev_task = next_task
        return next_task


    def __iter__(self):
        return self


    def traverse(self, directories):
        '''Traverse file tree in alphabetical order (top down)'''
        for directory in sorted(directories):
            for root, dirs, files in os.walk(directory, followlinks=True, topdown=True):
                dirs.sort()  # ensure alphabetical traversal
                for filename in sorted(files):
                    if self.validate(filename):
                        yield os.path.join(root, filename)


    def validate(self, filename):
        '''Check if file is eligible for transcoding'''
        try:
            extension = filename.rsplit('.')[1].lower()
            return extension in transcoder.KNOWN_EXTENSIONS
        except IndexError:
            return False
