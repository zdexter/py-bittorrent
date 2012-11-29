import logging
import util

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
