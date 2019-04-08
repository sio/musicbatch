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
    else:  # edit target list
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
                meta.extra.targets
            except AttributeError:
                meta.extra.targets = []
            if args.set_targets:
                meta.extra.targets = args.targets
            elif args.add_targets:
                meta.extra.targets = list(set(meta.extra.targets).union(args.targets))
            elif args.del_targets:
                meta.extra.targets = list(set(meta.extra.targets).difference(args.targets))
            elif args.clear_targets:
                meta.extra.targets = []
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
        '--add-targets',
        metavar='TARGETS',
        help='Add specified target or targets (comma-separated list) to metadata file',
    )
    actions.add_argument(
        '--set-targets',
        metavar='TARGETS',
        help='Replace targets in metadata file with specified values',
    )
    actions.add_argument(
        '--del-targets',
        metavar='TARGETS',
        help='Remove specified targets from metadata file(s)',
    )
    actions.add_argument(
        '--clear-targets',
        action='store_true',
        default=False,
        help='Remove all targets from metadata file(s)',
    )
    args = parser.parse_args(*a, **ka)
    targets = None
    for option in (args.add_targets, args.set_targets, args.del_targets):
        if option:
            targets = [t.strip() for t in option.split(',') if t.strip()]
            break
    if targets is not None and not targets:
        parser.error('Invalid list of targets: {}'.format(option))
    args.targets = targets
    return args



def find_subdirs(directory):
    for path, dirs, files in os.walk(directory):
        for directory in dirs:
            yield os.path.join(path, directory)
