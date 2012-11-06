import bencode
import math
import util

class TorrentFile():
    def __init__(self, file_name, info_dict=None):
        """Constructs a TorrentFile by reading a .torrent file or
        using a info_dict.

        Args:
            file_name (str)
        Kwargs:
            info_dict (dict)
        """
        # TODO: Error checking
        with open(file_name, 'r') as f:
            contents = f.read()

        if not info_dict:
            self.info_dict = bencode.bdecode(contents)
        else:
            self.info_dict = info_dict
            self._generate(info_dict)

        # self.info_hash = util.sha1_hash(self.info_dict['info'])

    @classmethod
    def write_torrent(cls, file_name, tracker_url, content, piece_length=512):
        info_dict = {
            'name': file_name,
            'length': len(contents),
            # Fields common to single and multi-file below
            'piece_length': piece_length * 1024,
            'pieces': cls._pieces_hashes(contents)
        }

        metainfo = {
            'info': info_dict,
            'announce': tracker_url
        }

        with open(file_name, 'w') as f:
            f.write(bencode.bencode(metainfo))

        return cls(file_name, info_dic)

    @classmethod
    def _pieces_hashes(cls, string, piece_lenth):
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
