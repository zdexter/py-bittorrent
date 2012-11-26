import socket
import time
import util
import struct
from conn import MsgConnection, AcceptConnection
from message import WireMessage

class Peer(object):
    def __init__(self, ip, port, client, peer_id=None, conn=None):
        self.ip = ip
        self.port = port
        self.client = client

        if peer_id:
            self.peer_id = peer_id
        else:
            seed = self.ip + str(time.time())
            self.peer_id = util.sha1_hash(self.ip) # Until handshake

        self.am_choking = True # Client choking remote
        self.am_interested = False # Client interested
        self.choking = True # Remote choking client
        self.interested = False # Remote interested
        if conn:
            self.conn = MsgConnection(self, conn)
        else:
            self.conn = MsgConnection(self)
        
    def add_conn(self, conn):
        self.conn = conn
    def _request_peer_pieces(self):
        """Ask this peer for each piece it has that we're interested in.
        """
        peer_has_pieces = self.client.torrent.pieces_by_rarity(self.peer_id)
        if len(peer_has_pieces) > 0:
            # Declare interest to remote peer
            self.set_interested(True)
            print 'Peer "{}" has {} of {} pieces.'.format(
                    self.peer_id,
                    len(peer_has_pieces),
                    len(self.client.torrent.pieces)
                    )
            self.request_pieces(peer_has_pieces)
    def _is_valid_piece(self, piece, index):
        piece_hash = util.sha1_hash(piece)
        expected_hash = self.client.torrent.pieces[index][0].piece_hash
        # print 'block_hash was', block_hash
        # print 'expected_hash was', expected_hash
        return piece_hash == expected_hash
    def _build_bitfield(self):
        """Return at least len(pieces) bits as complete bytes.

           Bit at position i represents client's posession (1)
            or lack (0) of the data at pieces[i].

        """
        received = [x[0].received for x in self.client.torrent.pieces]
        assert len(received) == self.client.torrent.num_pieces
        str_output = ""
        for b in received:
            str_output += "1" if b else "0"
        difference = self.client.torrent.num_pieces - len(str_output)
        while len(str_output) % 8 != 0:
            str_output += "0"
        #print 'len(str_output) was', len(str_output)
        byte_array = ""
        for i in range(0, len(str_output), 8):
            # Convert string of 1's and 0's to base 2 integer
            # print 'adding', repr(struct.pack('>B', int(str_output[i:i+8], 2)))
            byte_array += \
                    struct.pack('>B', int(str_output[i:i+8], 2))
        """
        print type(byte_array)
        print 'byte array len was', len(byte_array)
        bits = ''.join(str(bit) for bit in self._bits(byte_array))
        assert len(byte_array) == self.client.torrent.num_pieces / 8
        """
        return byte_array
    # Message callbacks
    def handshake(self, info_hash, peer_id):
        print 'info_hash was', info_hash
        assert info_hash in self.client.torrents.keys()
        print 'Received handshake resp from peer:', peer_id
        # Replace old key in dictionary
        temp_peer_id = self.peer_id
        self.peer_id = peer_id
        self.client.peers[self.peer_id] = self.client.peers[temp_peer_id]
        del self.client.peers[temp_peer_id]
        try:
            self.client.torrents[info_hash]
        except KeyError, e:
            print 'Closing conn; client not serving torrent {}.'.format(info_hash)
            self.conn.close()
        self.conn.enqueue_msg(WireMessage.construct_msg(2)) # Interested
        bitfield = self._build_bitfield()
        # print 'bitfield repr was', repr(bitfield)
        self.conn.enqueue_msg(WireMessage.construct_msg(5, bitfield)) # Bitfield
    def keep_alive(self):
        print 'Received keep-alive'
    def choke(self):
        print 'Received choke'
        self.choking = True
    def unchoke(self):
        print 'Received unchoke'
        self._request_peer_pieces()
    def interested(self):
        print 'Received interested'
        self.interested = True
    def not_interested(self):
        print 'Received not interested';
        self.interested = False
    def have(self, piece_index):
        try:
            assert piece_index < len(self.client.torrent.pieces)
        except AssertionError:
            raise Exception('Peer reporting too many pieces in "have."')
        # print 'Received have {}'.format(piece_index)
        self.client.torrent.decrease_rarity(piece_index,self.peer_id)
        self._request_peer_pieces()
    def _bits(self, data):
        data_bytes = (ord(b) for b in data)
        for b in data_bytes:
            """Get bit by reducing b by 2^i.
               Bitwise AND outputs 1s and 0s as strings.
            """
            for i in reversed(xrange(8)): # msb on left
                yield (b >> i) & 1
    def bitfield(self, bitfield):
        """Decrease piece rarity for each piece the peer reports it has.
        """
        # print 'Received bitfield'
        bitfield_length = len(bitfield)
        bits = ''.join(str(bit) for bit in self._bits(bitfield))
        # Trim spare bits
        pieces_length = len(self.client.torrent.pieces)
        try:
            """ Sanity check: do peer & client expect same # of pieces?
                Check extra bits only.
            """
            assert len(filter(lambda b: b=='1', bits[pieces_length:])) == 0
        except AssertionError:
            raise Exception('Peer reporting too many pieces in "bitfield."')

        bits = bits[:pieces_length]
        # Modify torrent state with new information
        for i in range(len(bits)):
            bit = bits[i]
            if bit == '1':
                self.client.torrent.decrease_rarity(i,self.peer_id)
    def request(self, index, begin, length):
        print 'Got request'
        pass
    def piece(self, index, begin, block):
        print 'Got piece from {} with index {}; begin {}; length {}'.format(
                self.peer_id, index, begin, len(block))
        if self.client.torrent.mark_block_received(index, begin, block):
            self.send_have(index)
        self.send_cancel(index, begin, len(block))
    def cancel(self, index, begin, length):
        print 'Got cancel'
        pass
    def port(self, listen_port):
        print 'Got port'
        pass
    # Begin outbound messages
    def send_have(self, index):
        """Tell all peers that client has all blocks in piece[index].
        """
        msg = WireMessage.construct_msg(4, index)
        self.conn.enqueue_msg(msg) # TODO: all peers
    def send_cancel(self, index, begin, length):
        msg = WireMessage.construct_msg(8, index, begin, length)
        self.conn.enqueue_msg(msg)
    def request_pieces(self, pieces):
        for piece, peer_id in pieces:
            # print 'num blocks', len(piece.blocks)
            for block in piece.blocks.values():
                #print 'block was', block
                print '% Requesting pi {}, offset {} and block length {} %'.format(
                       piece.index, block.begin, block.length)

                msg = WireMessage.construct_msg(
                        6, piece.index, block.begin, block.length)
                self.conn.enqueue_msg(msg)
    def set_interested(self, am_interested):
        """Change client's interest in peer based upon
            value of am_interested argument.
           Communicate new interest to remote peer.
        """
        try:
            assert am_interested != self.interested # Detect misuse
        except AssertionError:
            raise Exception('Error: No change in am_interested')
        self.am_interested = am_interested
        msg_id = None
        if self.am_interested:
            msg_id = 2
        else:
            msg_id = 3
        msg = WireMessage.construct_msg(msg_id)
        self.conn.enqueue_msg(msg)
    def set_choking(self, am_choking):
        """Change client's choking status of peer based upon
            value of am_choking argument.
           Communicate new choking value to remote peer.
        """
        try:
            assert am_choking != self.choking # Detect misuse
        except AssertionError:
            raise Exception('Error: No change in am_choking')
        self.am_choking = am_choking
        msg_id = None
        if self.am_choking:
            msg_id = 0
        else:
            msg_id = 1
        msg = WireMessage.construct_msg(msg_id)
        self.conn.enqueue_msg(msg)
class Client(object):
    def __init__(self, reactor, torrents):
        self._reactor = reactor
        self.peer_id = self._gen_peer_id()
        self.peers = {}
        self._pending_peers = []
        self.torrents = torrents
        self.torrent = torrents.itervalues().next()
        self.conn = AcceptConnection(self)
    def handshake(self, new_conn, addr, msg):
        peer_id = repr(msg[20:])
        print 'Testing for peer existence:', self.peers[peer_id]
        # Python will use repr(peer_id) in data structures; store it as such.
        self.peers[peer_id] = Peer(addr[0], addr[1], peer_id, conn)
    def start_serving(self, torrent, info_hash):
        self.torrents[info_hash] = torrent
    def stop_serving(self, info_hash):
        del self.torrents[info_hash]
    def notify_closed(self, peer_id):
        """Callback for peer to inform client that it has
            disconnected.
        """
        self._reactor.remove_subscriber(peer_id)
        del self.peers[peer_id]
        print 'Removed {} from peers.'.format(peer_id)
    def register_callback(self, callback):
        self._reactor.add_callback(callback)
    def connect_to_peers(self, peer_list):
        for peer in peer_list:
            handshake = WireMessage.build_handshake(self, peer, self.torrent)
            try:
                peer.conn.connect(peer.ip, peer.port)
            except socket.error, e:
                print('Socket error while connecting to {}:{}: {}'.format(
                    peer.ip, peer.port, e
                    ))
            else:
                peer.conn.enqueue_msg(handshake)
                self.peers[peer.peer_id] = peer
    def _gen_peer_id(self):
        """Return a hash of the (not necessarily fully qualified)
            hostname of the machine the Python interpreter
            is running on, plus a timestamp.
        """
        seed = socket.gethostname() + str(time.time())
        return util.sha1_hash(seed) 
