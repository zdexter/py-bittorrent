## Zach's BitTorrent Client

A BitTorrent client written in Python. Supports multi-file torrents.

This client implements a rarest-first piece download strategy. That is, the client will attempt to download those pieces that are least common in the swarm before it downloads the more-common pieces.

Please see my blog for detailed technical explanations of what I learned, design decisions, algorithmic challenges, and more: http://zachdex.tumblr.com/post/36792592990/bitttorrent-client-lessons

### Usage

./btclient.py -h

To run using a .torrent (metainfo) file called myfile.torrent:

./btclient.py --metainfo myfile.torrent

The --url and --gen arguments only apply if you want to write a metainfo file that you can use for testing purposes. --url is the announce URL of the tracker you'd like to write into your new metainfo file.

--logging can be one of {debug,info,warning,error,critical}, and defaults to info.
