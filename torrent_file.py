import bencode
import math
import util

class TorrentFile():
    def __init__(self, file_name, tracker_url, write=False, piece_length=512):
        self.file_name = file_name
        self.tracker_url = tracker_url
        self._write = write
        self._piece_length = piece_length
        if self._write:
            self._generate()

    def read(self):
        """Return info dictionary based upon .torrent file's contents.
        """
        f = open(self.file_name, 'r')
        contents = f.read()
        f.seek(0, 2)
        length = f.tell()
        f.close()
        info_dict = bencode.bdecode(contents) # Protocol: Metainfo file is an info dict.
        print 'info dict in torrent_file.py:', info_dict
        return info_dict

    def pieces_hashes(self, string, num_pieces):
        """Break string into num_pieces parts.
           Return array built from 20-byte SHA1 hashes
            of those parts.
        """
        split_interval = len(string) / num_pieces
        assert split_interval * num_pieces == len(string)

        output = ""
        current_pos = 0
        while current_pos < len(string):
            piece_hash = util.sha1_hash(string[current_pos:current_pos+split_interval])
            output += piece_hash
            current_pos += split_interval
        return output

    def _generate(self):
        """Write a metainfo file of name file_name to 
            current directory.
        """

        contents = 'Some random data!'
        length = len(contents)
        if length < self._piece_length:
            num_pieces = 1 
        else:
            num_pieces = math.ceil(
                length / self._piece_length
                )

        info_dict = {
            'name': self.file_name,
            'length': length,
            # Fields common to single and multi-file below
            'piece_length': self._piece_length,
            'pieces': self.pieces_hashes(contents, num_pieces)
        }

        metainfo = {
            'info': info_dict,
            'announce': self.tracker_url
        }

        f = open(self.file_name, 'w')
        f.write(bencode.bencode(metainfo))
        f.close()

        return True
