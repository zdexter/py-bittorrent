#!/usr/bin/env python

from torrent import Torrent
import argparse
from reactor import Reactor

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
    args = parser.parse_args()
    reactor = Reactor()
    if args.gen:
        # Generate new torrent file
        torrent = Torrent.write_metainfo_file(args.metainfo, args.url, 'The lazy brown fox jumped over the fat cow.')
        pass
    else: # Read existing file
        torrent = Torrent(reactor, args.metainfo) 
    reactor.add_torrent(torrent)
    reactor.select()
    if args.tests:
        import doctest
        doctest.testmod()

