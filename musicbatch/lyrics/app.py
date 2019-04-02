'''
Command line application for local lyrics database
'''

import os.path
import logging
from argparse import ArgumentParser
from threading import Thread
from time import sleep

from musicbatch.transcoder.progress import DotTicker
from musicbatch.lyrics.db import LyricsStorage



log = logging.getLogger('musicbatch.lyrics.app')



def run(*a, **ka):
    args = parse_args(*a, **ka)
    path = os.path.expandvars(args.database)
    db = LyricsStorage(path)
    ui = UIThread(db)
    if args.retry_scheduled:
        with ui:
            db.get_scheduled()
    elif args.scan_library:
        with ui:
            db.build_library(args.scan_library)
    elif args.artist and args.title:
        lyrics = db.get(args.artist, args.title)
        print(lyrics)
    else:
        parse_args(['--help'])



def parse_args(*a, **ka):
    parser = ArgumentParser(description='Interact with local lyrics database')
    parser.add_argument(
        'artist',
        nargs='?',
        default=None,
        help='Song artist',
    )
    parser.add_argument(
        'title',
        nargs='?',
        default=None,
        help='Song title',
    )
    parser.add_argument(
        '--database',
        default='$HOME/.lyrics.db',
        help='Path to local lyrics database',
    )
    parser.add_argument(
        '--scan-library',
        default=None,
        help='Populate local lyrics database with text for all songs in this library',
    )
    parser.add_argument(
        '--retry-scheduled',
        action='store_true',
        default=False,
        help='Retry fetchig lyrics that were unavailable in previous runs',
    )
    args = parser.parse_args(*a, **ka)
    if  not args.scan_library \
    and not args.retry_scheduled \
    and not (args.artist or args.title):
        parser.error('No action requested')
    elif (args.scan_library or args.retry_scheduled) \
    and  (args.artist or args.title):
        parser.error('Choose either one of batch actions or a single song')
    elif (args.scan_library and args.retry_scheduled):
        parser.error('Only one batch action can be selected')
    elif (args.artist or args.title) \
    and not (args.artist and args.title):
        parser.error('Can not specify artist without title')
    return args



class UIThread:
    '''User interface thread for long running tasks'''


    def __init__(self, lyrics_db, refresh_delay=0.5):
        self.db = lyrics_db
        self.refresh_delay = refresh_delay
        self.terminated = False
        self.throbber = DotTicker()
        def background():
            last_time = False
            while not last_time:
                last_time = self.terminated
                if last_time: self.throbber.length = 0
                print(' {stats}{ticker: <3}\r'.format(
                    stats = self.db.stats,
                    ticker = self.throbber,
                ), end='')
                sleep(self.refresh_delay)
            print('')
        self.thread = Thread(target=background)


    def start(self):
        self.thread.start()


    def stop(self):
        self.terminated = True
        self.thread.join()


    def __enter__(self):
        self.start()


    def __exit__(self, *a, **ka):
        self.stop()



if __name__ == '__main__':
    run()
