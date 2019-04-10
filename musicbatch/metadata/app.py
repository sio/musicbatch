'''
Command line interface for managing album metadata
'''

import os
from argparse import ArgumentParser

from musicbatch.metadata import METADATA_YAML
from musicbatch.metadata.objects import generate, MusicAlbumInfo



def run(*a, **ka):
    '''CLI entry point for metadata manager'''
    args = parse_args(*a, **ka)
    if args.recursive:
        directories = find_subdirs(args.directory)
    else:
        directories = (args.directory, )
    if args.generate:
        generate(directories, target=args.location)
    else:  # edit category list
        for dirpath in directories:
            meta_file = os.path.join(dirpath, args.location)
            if not os.path.exists(meta_file):
                continue
            meta = MusicAlbumInfo(filename=meta_file)
            try:
                meta.extra
            except AttributeError:
                meta.extra = {}
            try:
                meta.extra.categories
            except AttributeError:
                meta.extra.categories = []
            if args.set_categories:
                meta.extra.categories = args.categories
            elif args.add_categories:
                meta.extra.categories = list(set(meta.extra.categories).union(args.categories))
            elif args.del_categories:
                meta.extra.categories = list(set(meta.extra.categories).difference(args.categories))
            elif args.clear_categories:
                meta.extra.categories = []
            else:
                raise RuntimeError('Impossible branching, invalid arguments')
            meta.validate_hashes(write_updates=True)
            meta.write()



def parse_args(*a, prog=None, **ka):
    parser = ArgumentParser(description='Manage music metadata with YAML files', prog=prog)
    parser.add_argument(
        'directory',
        metavar='DIR',
        help='Directory with music files',
    )
    parser.add_argument(
        '--recursive',
        action='store_true',
        default=False,
        help='Process all nested directories within DIR',
    )
    parser.add_argument(
        '--location',
        default=METADATA_YAML,
        help='Relative path to metadata file (default={})'.format(METADATA_YAML)
    )
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument(
        '--generate',
        action='store_true',
        default=False,
        help='Create metadata file(s) for specified directory',
    )
    actions.add_argument(
        '--add-categories',
        metavar='CATEGORIES',
        help='Add specified category or categories (comma-separated list) to metadata file',
    )
    actions.add_argument(
        '--set-categories',
        metavar='CATEGORIES',
        help='Replace categories in metadata file with specified values',
    )
    actions.add_argument(
        '--del-categories',
        metavar='CATEGORIES',
        help='Remove specified categories from metadata file(s)',
    )
    actions.add_argument(
        '--clear-categories',
        action='store_true',
        default=False,
        help='Remove all categories from metadata file(s)',
    )
    args = parser.parse_args(*a, **ka)
    categories = None
    for option in (args.add_categories, args.set_categories, args.del_categories):
        if option:
            categories = [c.strip() for c in option.split(',') if c.strip()]
            break
    if categories is not None and not categories:
        parser.error('Invalid list of categories: {}'.format(option))
    args.categories = categories
    return args



def find_subdirs(directory):
    for path, dirs, files in os.walk(directory):
        for directory in dirs:
            yield os.path.join(path, directory)
