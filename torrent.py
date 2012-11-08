import bencode
import math
import util
import urllib2
from client import Client, Peer
from tracker import Tracker

class Torrent():
    def __init__(self, file_name, info_dict=None):
        """Reads existing metainfo file, or writes a new one.
           Builds client, fetches peer list, and construct peers.
        """
        # TODO: Error checking
        with open(file_name, 'r') as f:
            contents = f.read()
        self.info_dict = info_dict or bencode.bdecode(contents)
        self.info_hash = util.sha1_hash(
            bencode.bencode(self.info_dict['info']) # metainfo file is bencoded
            )
        self.client = Client([self])
        self.tracker = Tracker(self, self.client)
        resp = self.tracker.connect()
        self.client.connect_to_peers(
            self._new_peers(
                self._get_peers(resp)
                )
            )
    def _new_peers(self, peer_list):
        own_ext_ip = urllib2.urlopen('http://whatsmyip.org').read() # HACK
        return [Peer(p[0], p[1]) for p in peer_list if p[0] != own_ext_ip]
        
        for peer in peer_list:
            # Is overwriting memory in this manner bad?
            # What does changing the size of each array item
            #   lead to in terms of memory allocation?
            peer = Peer(peer[0], peer[1])
        return peer_list

    def _get_peers(self, resp):
        raw_bytes = [ord(c) for c in resp['peers']]
        peers = []
        for i in range(0,len(raw_bytes) / 6):
            start = i*6
            end = start + 6
            ip = ".".join(str(i) for i in raw_bytes[start:end-2])
            port = raw_bytes[end-2:end]
            port = (port[1]) + (port[0] * 256)
            peers.append([ip,port])
        return peers
    def length(self):
        if 'length' in self.info_dict['info']:
            return self.info_dict['info']['length']
        return sum(f['length'] for f in self.info_dict['info']['files'])

    @classmethod
    def write_metainfo_file(cls, file_name, tracker_url, contents, piece_length=512):
        info_dict = {
            'name': file_name,
            'length': len(contents),
            # Fields common to single and multi-file below
            'piece_length': piece_length * 1024,
            'pieces': cls._pieces_hashes(contents, piece_length)
        }
        metainfo = {
            'info': info_dict,
            'announce': tracker_url
        }

        with open(file_name, 'w') as f:
            f.write(bencode.bencode(metainfo))
        
        return cls(file_name, metainfo)

    @classmethod
    def _pieces_hashes(cls, string, piece_length):
        """Return array built from 20-byte SHA1 hashes
            of the string's pieces.
        """
        output = ""
        current_pos = 0
        num_bytes= len(string)
        while current_pos < num_bytes:
            if current_pos + piece_length > num_bytes:
                to_position = num_bytes
            else:
                to_position = current_pos + piece_length

            piece_hash = util.sha1_hash(string[current_pos:to_position])
            output += piece_hash
            current_pos += piece_length

        return output

    def _num_pieces(self, contents):
        length = len(contents)
        if length < self.piece_length:
            return 1
        else:
            return int(math.ceil(float(length) / self.piece_length))
