import urllib2, urllib
import client
import util
import bencode
from struct import unpack

class Tracker():
    def __init__(self, torrent, client):
        self.torrent = torrent
        self.client = client
    def _make_req(self, url):
        """Return bdecoded response of an
            HTTP GET request to url.
        """
        return bencode.bdecode(
            urllib2.urlopen(url).read()
            )
    def connect(self, port=6881):
        """Try to connect to tracker.
           Return tracker's response.
        """
        params = {
            'info_hash': util.sha1_hash(str(
                bencode.bencode(self.torrent.info_dict['info'])
                )),
            'peer_id': self.client.peer_id,
            'port': port,
            'uploaded': 0,
            'downloaded': 0,
            'left': self.torrent.length(),
            'event': 'started'
        }
        announce_url = self.torrent.info_dict['announce']
        #print 'announce_url was', announce_url
        get_url = announce_url + "?" + urllib.urlencode(params)
        return self._make_req(get_url)
