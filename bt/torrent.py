import bencode
import math
import util
import urllib2
from collections import OrderedDict
from client import Client, Peer
from tracker import Tracker
import logging

class Block(object):
    """Abstract away data storage.
    """
    def __init__(self, piece, begin, length):
        self.logger = logging.getLogger('bt.torrent.Block')
        self.piece = piece
        self.begin = begin
        self.length = length
        self.received = False
        self.times_requested = 0
    def _seek_start(self):
        """Moves temp file to start of this block.
        """
        self.piece.torrent.tmp_file.seek(self.piece.start_pos + self.begin)
    def write(self, data):
        self._seek_start()
        self.logger.debug('WRITE to {}: start_pos {}, begin {}'.format(
            self.piece.index, self.piece.start_pos, self.begin))
        self.piece.torrent.tmp_file.write(data)
        self.received = True
    def read(self, length):
        assert length <= self.length
        self._seek_start()
        self.piece.torrent.tmp_file.read(length)

class Piece(object):
    """A piece consists of block_size/file_length+1 blocks.
    """
    def __init__(self, torrent, index, piece_hash, block_size=16384):
        self.logger = logging.getLogger('bt.torrent.Piece')
        # Set up the expected begin indices of all blocks.
        self.received = False
        self.torrent = torrent
        self.index = index
        self.piece_hash = piece_hash
        self.block_size = block_size
        self.blocks = {}
        
        self.last_block_length = self.block_size
        # Last piece may have fewer blocks
        self.piece_length = self.torrent.piece_length
        if self.index == self.torrent.num_pieces - 1:
            self.piece_length = self.torrent.last_piece_length
            self.last_block_length = self.torrent.last_piece_length % \
                    self.block_size or self.block_size
        # Last block may have fewer bytes
        self.num_blocks = self.piece_length / self.block_size
        
        # If piece length == block length, first condition will be true
        #  If so, short-circuit
        if self.num_blocks == 0 \
                or self.piece_length % self.num_blocks != 0:
            self.num_blocks += 1
        begin = 0
        for i in range(self.num_blocks):
            length = self.block_size
            if self.index == self.torrent.num_pieces - 1:
                if i == self.num_blocks - 1: # Last block
                    length = self.last_block_length
            self.blocks[begin] = Block(self, begin, length)
            begin += self.block_size
        self.num_blocks_received = 0
        # Even if this is the last piece, we start at a multiple
        #  of the non-last piece length.
        self.start_pos = self.index * self.torrent.piece_length
    def write_to_block(self, begin, data):
        length = len(data)
        end = begin + length
        self.blocks[begin].write(data)
        self.num_blocks_received += 1
        if self.num_blocks_received == self.num_blocks:
            return True
        return False
    def suggest_blocks(self, num_to_suggest):
        """Suggest those X blocks which have been requested
            the fewest number of times, and have not been received.
        """
        blocks = sorted(
                self.blocks.values(), key=lambda b: b.times_requested)
        s = filter(lambda b: b.received==False, blocks)[:num_to_suggest]
        for b in s:
            b.times_requested += 1
        self.logger.debug('&&& Suggesting {} blocks'.format(len(s)))
        return s

    def is_valid(self):
        """Return true if the hash of this entire piece is what we expected.
        """
        self.torrent.tmp_file.seek(self.start_pos)
        # ... but we read only the # of bytes this piece actually has.
        f = self.torrent.tmp_file.read(self.piece_length)
        self.logger.debug('HASH: length of piece {} was {}'.format(
                self.index, len(f)))
        actual_hash = util.sha1_hash(f)
        return actual_hash == self.piece_hash

class File(object):
    def __init__(self, piece_length, path, length):
        self.path = ''.join(path)
        self.last_piece_length = length % piece_length or piece_length
        self.ref = open(self.path, 'w+')
        self.length = length

class Torrent(object):
    def __init__(self, reactor, file_name, info_dict=None):
        """Reads existing metainfo file, or writes a new one.
           Builds client, fetches peer list, and construct peers.
        """
        self.logger = logging.getLogger('bt.torrent.Torrent')
        with open(file_name, 'r') as f:
            contents = f.read()
        self.info_dict = info_dict or bencode.bdecode(contents) # If read, bdecode
        self.info_hash = util.sha1_hash(
            bencode.bencode(self.info_dict['info']) # metainfo file is bencoded
            )
        self.piece_length = self.info_dict['info']['piece length']
        self.last_piece_length = self.length() % self.piece_length or self.piece_length
        pieces = self.info_dict['info']['pieces']
        self.pieces_hashes = list(self._read_pieces_hashes(pieces))
        self.num_pieces = len(self.pieces_hashes)
        assert len(self.pieces_hashes) == self.num_pieces
        # assert (self.num_pieces-1) * self.piece_length + self.last_piece_length \
        #        == file_length
        self.files = []
        try:
            self.files.append(File(
                self.piece_length,
                self.info_dict['info']['name'],
                self.info_dict['info']['length']))
            self.logger.info('Appended file {} of length {}'.format(
                    self.info_dict['info']['name'], self.info_dict['info']['length']))
        except KeyError:
            for f in self.info_dict['info']['files']:
                self.files.append(File(self.piece_length, f['path'], f['length']))
                self.logger.info('Appended file {} of length {}'.format(
                        f['path'][len(f['path'])-1], f['length']))

        self.tmp_file = open(
                'temp.tmp', 'w+')
        """ Data structure for easy lookup of piece rarity
            pieces[hash] has list of Peer instances with that piece
            Get rarity: len(pieces[hash])
        """
        self.pieces = [
                (Piece(self, i, self.pieces_hashes[i]), []) for i in range(self.num_pieces)]
        for p, _ in self.pieces:
            logging.debug('Piece {} has length {}.'.format(p.index, p.piece_length))
        self._pieces_added = 0
        self.client = Client(reactor, {self.info_hash: self})
        self.tracker = Tracker(self, self.client)
        resp = self.tracker.connect()
        self.update_peers()
        #reactor.add_callback(self.update_peers)
    def update_peers(self, seconds=120):
        """Add peers we haven't tried to add yet.
            TODO: Make this happen only ever `seconds` seconds.
        """
        self.logger.debug('UPDATING PEERS >>>>>')
        resp = self.tracker.connect()
        self.client.connect_to_peers(
                self._new_peers(self._get_peers(resp), self.client)
                )
    def get_block(self, index, begin, length):
        # Assumption: length is <= our block size
        piece = self.pieces[i][0]
        block = piece.blocks[begin]
        return block.read(length)
    def mark_block_received(self, piece_index, begin, block):
        """Return true if entire piece received and verified; false if not.
        """
        piece = self.pieces[piece_index][0]
        if piece.blocks[begin].received: # Already have this block
            return False
        if not piece.write_to_block(begin, block):
            self.logger.info('Received {} of {} blocks in piece {}'.format(
                    piece.num_blocks_received,
                    piece.num_blocks,
                    piece.index))
            return False

        # Entire piece received
        self._pieces_added += 1
        piece.received = True
        assert piece.is_valid()
        if self._pieces_added >= self.num_pieces:
            self.logger.info('*****ALL PIECES RECEIVED*****')
            self._write_to_disk()
            raise util.DownloadCompleteException()
        else:
            self.logger.info('* {} of {} pieces received*'.format(
                    self._pieces_added, self.num_pieces))
        return True
    def _write_to_disk(self):
        start = 0
        for f in self.files:
            new_file = f.ref
            self.tmp_file.seek(start)
            new_file.write(self.tmp_file.read(f.length))
            self.logger.debug('Writing to {}, start {}, length {}'.format(
                    f.path, start, f.length))
            start += f.length

    def pieces_by_rarity(self, peer_id=None):
        """Return array of (piece objects, peers who have them)
            tuples where the i-th item is the i-th rarest.

            Optionally return such a list for a single peer.

        """
        pieces = sorted(self.pieces, key=lambda x: len(x[1]))
        if peer_id:
            pieces = filter(lambda x: peer_id in x[1], pieces)
        return pieces
    def decrease_rarity(self, i, peer_id):
        """Record that peer with peer_id has the i-th piece of this torrent.
        """
        self.logger.debug('Decreasing rarity of piece {} because {} has it.'.format(
                i, peer_id))
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
