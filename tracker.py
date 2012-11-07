import urllib2, urllib
import client
import util
import bencode

class Tracker():
    def __init__(self, torrent, client):
        self.torrent = torrent
        self.client = client
    def connect(self, port=6969):
        """Make HTTP GET to tracker
        """
        params = {
            'info_hash': util.sha1_hash(str(
                bencode.bencode(self.torrent.info_dict['info'])
                )),
            'peer_id': self.client.peer_id,
            'port': port,
            'uploaded': 0,
            'downloaded': 0,
            'left': self.torrent.info_dict['info']['length'],
            'event': 'started'
        }
        announce_url = self.torrent.info_dict['announce'] + \
             ":" + str(port) + "/announce"
        get_url = announce_url + "?" + urllib.urlencode(params)
        print get_url
        return bencode.bdecode(
            urllib2.urlopen(get_url).read()
            )

    def parse_response(self, response):
        response = bencode.bdecode(response)
        return response
