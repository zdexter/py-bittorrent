import urllib2, urllib
import torrent_file
import client
import util
import bencode

class Tracker():
    def __init__(self, torrent_file):
        self._torrent_file = torrent_file
        self._info_dict = torrent_file.info_dict
        self._peer = self._create_peer()

    def connect(self, port=6969):
        """Make HTTP GET to tracker
        """
        params = {
            'info_hash': util.sha1_hash(str(
                bencode.bencode(self._info_dict['info'])
                )),
            'peer_id': self._peer.peer_id,
            'port': port,
            'uploaded': 0,
            'downloaded': 0,
            'left': info_dict['info']['length'],
            'event': 'started'
        }
        full_url = self._torrent_file.tracker_url + ":" + str(port)
        get_url = full_url + "?" + urllib.urlencode(params)
        print get_url
        req = urllib2.urlopen(get_url)

    def parse_response(self, response):
        response = bencode.bdecode(response)
        return response
