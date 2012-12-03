#!/usr/bin/env python

from bt.torrent import Torrent
import argparse, logging
from bt.client import Client

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Bittorrent client'
    )
    parser.add_argument(
        '--tests',
        action='store_true',
        help='Run doctests'
    )
    parser.add_argument(
        '--url',
        default='http://173.230.132.32:6969/announce',
        help='Base URL of tracker'
    )
    parser.add_argument(
        '--gen',
        action='store_true',
        help='Generate new metainfo (.torrent) file with random data.'
    )
    parser.add_argument(
        '--metainfo',
        metavar='metainfo',
        default='mytorrent.torrent',
        help='Name for the metainfo file to read or write.',
    )
    parser.add_argument(
        '--logging',
        default='INFO',
        help='{debug,info,warning,error,critical}'
    )

    args = parser.parse_args()

    # Choose log level
    LEVELS = {
            'debug': logging.DEBUG,
            'info': logging.INFO,
            'warning': logging.WARNING,
            'error': logging.ERROR,
            'critical': logging.CRITICAL
            }
    log_level = LEVELS.get(args.logging, logging.INFO)
    logger = logging.getLogger('bt')
    logger.setLevel(log_level)
    # Output logging to console
    ch = logging.StreamHandler()
    formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # Run BitTorrent client
    client = Client(Torrent(args.metainfo))
    client.start()

    if args.tests:
        import doctest
        doctest.testmod()

