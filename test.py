#!/usr/bin/env python

from torrent import Torrent
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
        default='http://173.230.132.32',
        help='Base URL of tracker'
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
        # Generate new torrent file
        torrent = Torrent.write_metainfo_file(args.fname, args.url, 'The lazy brown fox jumped over the fat cow.')
        pass
    else: # Read existing file
        torrent = Torrent(args.fname) 
    if args.tests:
        import doctest
        doctest.testmod()

