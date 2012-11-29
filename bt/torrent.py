import bencode
import math
import util
from files import File, Piece, Block
import logging

class Torrent(object):
    def __init__(self, file_name, info_dict=None):
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
        self.files = [f for f in self._create_files()]
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
        #reactor.add_callback(self.update_peers)
    def _create_files(self):
        """Generate a new File object for every file the metainfo
            file told us about.
        """
        try:
            yield (File(
                self.piece_length,
                self.info_dict['info']['name'],
                self.info_dict['info']['length']))
            self.logger.info('Appended file {} of length {}'.format(
                    self.info_dict['info']['name'], self.info_dict['info']['length']))
        except KeyError:
            for f in self.info_dict['info']['files']:
                self.logger.info('Appending file {} of length {}'.format(
                        f['path'][len(f['path'])-1], f['length']))
                yield (File(self.piece_length, f['path'], f['length']))
    def get_block(self, index, begin, length):
        # Assumption: length is <= our block size
        piece = self.pieces[index][0]
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
