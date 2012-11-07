import bencode
import math
import util
from client import Client
from tracker import Tracker

class Torrent():
    def __init__(self, file_name, info_dict=None):
        """Reads existing metainfo file, or writes a new one.
           Builds client, fetches peer list, and construct peers.
        """
        # TODO: Error checking
        with open(file_name, 'r') as f:
            contents = f.read()

        if not info_dict:
            self.info_dict = bencode.bdecode(contents)
        else:
            self.info_dict = info_dict

        # self.info_hash = util.sha1_hash(self.info_dict['info'])
        self.client = Client([self])
        self.tracker = Tracker(self, self.client)
        resp = self.tracker.connect()
        print resp

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

        return cls(file_name, info_dict)

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
