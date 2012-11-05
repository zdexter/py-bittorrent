#!/usr/bin/env python

from tracker import Tracker
import torrent_file
import argparse

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
        default='173.230.132.32',
        help='URL of tracker'
    )
    parser.add_argument(
        '--gen',
        action='store_true',
        help='Generate new torrent file with random data.'
    )
    parser.add_argument(
        '--fname',
        metavar='filename',
        default='myfile.torrent',
        help='File to use for generation or reading.'
    )
    args = parser.parse_args()
    
    if args.gen:
        # Generate new torrent file and save to ./fname
        torrent_file.generate(args.url, args.fname)
    if args.tests:
        import doctest
        doctest.testmod()

    tracker = Tracker(args.url, args.fname)
    tracker.connect()
