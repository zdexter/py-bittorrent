import bencode
import math
import util
import urllib2
from collections import OrderedDict
from client import Client, Peer
from tracker import Tracker

class Block(object):
    """Abstract away data storage.
    """
    def __init__(self, piece, begin, data):
        self._begin = begin
        self._length = len(data)
        self._data = data
        base_pos = piece.index*piece.block_size
        piece.torrent.out_file.seek(base_pos + begin)
        # print 'Writing block from piece[{}] to position {}'.format(
        #        piece.index, base_pos+begin)
        piece.torrent.out_file.write(data)

class Piece(object):
    """A piece consists of block_size/file_length+1 blocks.
    """
    def __init__(self, torrent, index, piece_hash, block_size=16384):
        # Set up the expected begin indices of all blocks.
        self.received = False
        self.torrent = torrent
        self.index = index
        self.piece_hash = piece_hash
        self._pieces_added = 0
        self._blocks = []
        num_blocks = self.torrent.piece_length / block_size
        if self.torrent.piece_length % num_blocks != 0:
            num_blocks += 1 # Compensate for partially full last block
        self.block_size = block_size
    def add_block(self, begin, data):
        length = len(data)
        end = begin + length
        new_block = Block(self, begin, data)
        self._blocks.append(new_block)
        try:
            assert length == self.block_size
        except AssertionError:
            self.torrent.out_file.close()

class Torrent(object):
    def __init__(self, reactor, file_name, info_dict=None):
        """Reads existing metainfo file, or writes a new one.
           Builds client, fetches peer list, and construct peers.
        """
        with open(file_name, 'r') as f:
            contents = f.read()
        self.info_dict = info_dict or bencode.bdecode(contents) # If read, bdecode
        self.info_hash = util.sha1_hash(
            bencode.bencode(self.info_dict['info']) # metainfo file is bencoded
            )
        self.out_file = open(self.info_dict['info']['name'], 'w')
        self.piece_length = self.info_dict['info']['piece length']
        pieces = self.info_dict['info']['pieces']
        self.pieces_hashes = list(self._read_pieces_hashes(pieces))
        self.num_pieces = len(self.pieces_hashes)
        try:
            file_length = self.info_dict['info']['length']
        except KeyError: # Multi-file
            file_length = self.info_dict['info']['files'][0]['length']
        self.last_piece_length = file_length % self.piece_length or self.piece_length
        assert len(self.pieces_hashes) == self.num_pieces
        assert (self.num_pieces-1) * self.piece_length + self.last_piece_length \
                == file_length
        """ Data structure for easy lookup of piece rarity
            pieces[hash] has list of Peer instances with that piece
            Get rarity: len(pieces[hash])
        """
        self.pieces = [
                (Piece(self, i, self.pieces_hashes[i]), []) for i in range(self.num_pieces)]
        self._pieces_added = 0
        self.client = Client(reactor, {self.info_hash: self})
        self.tracker = Tracker(self, self.client)
        resp = self.tracker.connect()
        self.client.connect_to_peers(
                self._new_peers(self._get_peers(resp), self.client)
                )
    def mark_block_received(self, index, begin, block):
        """If block isn't already stored, store it.

        Number of pieces is fixed; no need for Piece instance to know
         what its index is.

        """
        piece = self.pieces[index][0]
        if piece.received:
            return

        piece.add_block(begin, block)
        piece.received = True
        self._pieces_added += 1
        if self._pieces_added >= self.num_pieces:
            print '*****ALL PIECES RECEIVED*****'
        else:
            pass
            # print '* {} of {} pieces received*'.format(
            #        self._pieces_added, self.num_pieces)
    def pieces_by_rarity(self, peer_id=None):
        """Return list of piece indices, where
            the i-th item is the i-th rarest.

            Optionally return such a list for a single peer.

        """
        print 'Sorting {} pieces'.format(len(self.pieces))
        pieces = sorted(self.pieces, key=lambda x: len(x[1]))
        if peer_id:
            pieces = filter(lambda x: peer_id in x[1], pieces)
        return pieces
    def decrease_rarity(self, i, peer_id):
        """Record that peer with peer_id has the i-th piece of this torrent.
        """
        # print 'Decreasing rarity of piece {} because {} has it.'.format(
        #        i, peer_id)
        # print 'in decrease_rarity, i was {}'.format(i)
        self.pieces[i][1].append(peer_id)
    def _new_peers(self, peer_list, client):
        own_ext_ip = urllib2.urlopen('http://ifconfig.me/ip').read() # HACK
        return [Peer(p[0], p[1], client) for p in peer_list if p[0] != own_ext_ip]

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
    def _read_pieces_hashes(self, pieces):
        """Return array built from 20-byte SHA1 hashes
            of the string's pieces.
        """
        for i in range(0, len(pieces), 20):
            yield pieces[i:i+20]

    @classmethod
    def _pieces_hashes(cls, string, piece_length):
        """Return array built from 20-byte SHA1 hashes
            of the string's pieces.
        """
        output = ""
        current_pos = 0
        num_bytes = len(string)
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
