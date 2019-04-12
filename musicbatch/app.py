'''
Top-level commandline entry point that relays all the work to subcommands
'''

import sys
from argparse import ArgumentParser
from importlib import import_module


SUBCOMMANDS = ('lyrics', 'metadata', 'transcoder')


def run(*a, **ka):
    prog, subcommand, args = parse_args(*a, **ka)
    app = import_module('musicbatch.{}.app'.format(subcommand))
    app.run(args, prog=prog)


def parse_args(*a, **ka):
    parser = ArgumentParser(description='Batch processing tools for music files')
    parser.add_argument(
        'subcommand',
        metavar='SUBCOMMAND',
        choices=SUBCOMMANDS,
        help='One of the following subcommands: {}'.format(', '.join(sorted(SUBCOMMANDS))),
    )
    parser.add_argument(
        '_',
        metavar='ARG',
        nargs='*',
        help='All extra parameters will be passed to subcommand',
    )
    if a:
        subcommand = a[0][:1]
        args = a[0][1:]
        a = a[1:]
    elif 'args' in ka:
        subcommand = ka['args'][:1]
        args = ka['args'][1:]
        ka.pop('args')
    else:
        subcommand = sys.argv[1:2]
        args = sys.argv[2:]
    result = parser.parse_args(subcommand, *a, **ka)
    prog = '{} {}'.format(parser.prog, result.subcommand)
    return prog, result.subcommand, args
