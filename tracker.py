import urllib2
import torrent_file
import client

class Tracker():
    def __init__(self, url, file_name):
        self._url = url
        self._file_name = file_name
        self._peer = _create_peer()
    
    def _create_peer():
        """Return a new client.
        """
        return client.Client()

    def connect(self, port=6969):
        """Make HTTP GET to tracker
        """
        file_contents = torrent_file.read(self._file_name)
        info_dict = dict(file_contents)
        print file_contents

        params = {
            'info_hash': torrent_file.do_hash(info_dict['info']),
            'peer_id': self._peer.peer_id,
            'port': port,
            'uploaded': 0,
            'downloaded': 0,
            'left': info_dict['length'],
            'event': 'started'
        }
        params = bencode.encode(params)
        full_url = self._url + str(port)
        req = urllib2.urlopen(full_url, params)

    def parse_response(self, response):
        response = bencode.decode(response)
        return response
