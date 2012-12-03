import hashlib
import struct
import logging

class DownloadCompleteException(Exception):
    pass

def sha1_hash(string):
    """Return 20-byte sha1 hash of string.
    """
    return hashlib.sha1(string).digest()

class Bitfield(object):
    def __init__(self, bool_array):
        """Return at least len(bool_array) bits as complete bytes.

           Bit at position i represents client's posession (1)
            or lack (0) of the data at bool_array[i].

        """
        self.logger = logging.getLogger('bt.util.Bitfield')
        str_output = "".join(map(str, bool_array))
        difference = total_length - len(str_output)
        while len(str_output) % 8 != 0:
            str_output += "0"
        byte_array = ""
        for i in range(0, len(str_output), 8):
            # Convert string of 1's and 0's to base 2 integer
            byte_array += struct.pack('>B', int(str_output[i:i+8], 2))
        self.byte_array = byte_array
    @classmethod
    def _bits(cls, data):
        data_bytes = (ord(b) for b in data)
        for b in data_bytes:
            """Get bit by reducing b by 2^i.
               Bitwise AND outputs 1s and 0s as strings.
            """
            for i in reversed(xrange(8)): # msb on left
                yield (b >> i) & 1
    @classmethod
    def parse(cls, peer, bitfield):
        """Decrease piece rarity for each piece the peer reports it has.
        """
        bitfield_length = len(bitfield)
        bits = list(cls._bits(bitfield))
        # Trim spare bits
        pieces_length = len(peer.client.torrent.pieces)
        try:
            """ Sanity check: do peer & client expect same # of pieces?
                Check extra bits only.
            """
            assert bits.count(1)
        except AssertionError:
            raise Exception('Peer reporting too many pieces in "bitfield."')

        # Modify torrent state with new information
        for i, bit in enumerate(bits):
            if bit:
                peer.client.torrent.decrease_rarity(i, peer.peer_id)
