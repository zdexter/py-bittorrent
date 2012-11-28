import socket
import time
import util
from conn import MsgConnection, AcceptConnection
from message import WireMessage
from util import Bitfield
import logging

class Peer(object):
    def __init__(self, ip, port, client, peer_id=None, conn=None):
        self.logger = logging.getLogger('bt.peer.Peer')
        self.ip = ip
        self.port = port
        self.client = client
        self.outstanding_requests = 0

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
    def request_pieces(self):
        """Ask this peer for each piece it has that we're interested in.
        """
        peer_has_pieces = self.client.torrent.pieces_by_rarity()
        if len(peer_has_pieces) > 0:
            # Declare interest to remote peer
            self.logger.debug('Peer "{}" has {} of {} pieces.'.format(
                    self.peer_id,
                    len(peer_has_pieces),
                    len(self.client.torrent.pieces)
                    ))
            self.request_blocks(peer_has_pieces)
            self.set_interested(True)
    def _is_valid_piece(self, piece, index):
        piece_hash = util.sha1_hash(piece)
        expected_hash = self.client.torrent.pieces[index][0].piece_hash
        return piece_hash == expected_hash
    # Message callbacks
    def handshake(self, info_hash, peer_id):
        self.logger.debug('info_hash was', info_hash)
        assert info_hash in self.client.torrents.keys()
        self.logger.debug('Received handshake resp from peer:', peer_id)
        # Replace old key in dictionary
        temp_peer_id = self.peer_id
        self.peer_id = peer_id
        self.client.peers[self.peer_id] = self.client.peers[temp_peer_id]
        del self.client.peers[temp_peer_id]
        try:
            self.client.torrents[info_hash]
        except KeyError, e:
            self.logger.warning(
                    'Closing conn; client not serving torrent {}.'.format(info_hash))
            self.conn.close()
        self.conn.enqueue_msg(WireMessage.construct_msg(2)) # Interested

        pieces_received = [x[0].received for x in self.client.torrent.pieces]
        if len(filter(lambda x: x, pieces_received)) > 0:
            bitfield = Bitfield(pieces_received, self.client.torrent.num_pieces).byte_array
            self.conn.enqueue_msg(WireMessage.construct_msg(5, bitfield)) # Bitfield

    def bitfield(self, bitfield):
        Bitfield.parse(self, bitfield)
    def keep_alive(self):
        self.logger.debug('Received keep-alive')
    def choke(self):
        self.logger.debug('Received choke')
        self.choking = True
    def unchoke(self):
        self.logger.debug('Received unchoke')
        self.request_pieces()
    def interested(self):
        self.logger.debug('Received interested')
        raise Exception("got interested msg")
        self.interested = True
    def not_interested(self):
        self.logger.debug('Received not interested')
        self.interested = False
    def have(self, piece_index):
        try:
            assert piece_index < len(self.client.torrent.pieces)
        except AssertionError:
            raise Exception('Peer reporting too many pieces in "have."')
        self.client.torrent.decrease_rarity(piece_index,self.peer_id)
    def request(self, index, begin, length):
        self.logger.debug('Got request')
        block_data = self.torrent.get_block(index, begin, length)
        msg = WireMessage.construct_msg(7, index, begin, block_data)
        self.conn.enqueue_msg(msg)
    def piece(self, index, begin, block):
        self.logger.debug(
                'Got piece from {} with index {}; begin {}; length {}'.format(
                    self.peer_id, index, begin, len(block)))
        if self.client.torrent.mark_block_received(index, begin, block):
            # If piece is now complete
            self.send_have(index)
        self.outstanding_requests -= 1
        self.request_pieces()
        #self.send_cancel(index, begin, len(block))
    def cancel(self, index, begin, length):
        self.logger.debug('Got cancel')
        pass
    def port(self, listen_port):
        self.logger.debug('Got port')
        pass
    # Begin outbound messages
    def send_keep_alive(self):
        msg = WireMessage.construct_msg(-1)
        self.conn.enqueue_msg(msg)
    def send_have(self, index):
        """Tell all peers that client has all blocks in piece[index].
        """
        msg = WireMessage.construct_msg(4, index)
        self.conn.enqueue_msg(msg) # TODO: all peers
    def send_cancel(self, index, begin, length):
        msg = WireMessage.construct_msg(8, index, begin, length)
        self.conn.enqueue_msg(msg)
    def request_blocks(self, pieces, max_requests=1):
        if self.outstanding_requests > max_requests:
            return False
        for piece, peer_id in pieces:
            blocks = piece.suggest_blocks(max_requests)
            self.outstanding_requests += len(blocks)
            for block in blocks:
                self.logger.debug('% Requesting pi {}, offset {} and block length {} %'.format(
                       piece.index, block.begin, block.length))

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
        self.logger = logging.getLogger('bt.peer.client')
        self._reactor = reactor
        self.peer_id = self._gen_peer_id()
        self.peers = {}
        self._pending_peers = []
        self.torrents = torrents
        self.torrent = torrents.itervalues().next()
        self.conn = AcceptConnection(self)

    def handshake(self, new_conn, addr, msg):
        peer_id = repr(msg[20:])
        self.logger.debug('Testing for peer existence:', self.peers[peer_id])
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
        self.logger.debug('Removed {} from peers.'.format(peer_id))
    def register_callback(self, callback):
        self._reactor.add_callback(callback)
    def connect_to_peers(self, peer_list):
        for peer in peer_list:
            handshake = WireMessage.build_handshake(self, peer, self.torrent)
            try:
                peer.conn.connect(peer.ip, peer.port)
            except socket.error, e:
                self.logger.debug('Socket error while connecting to {}:{}: {}'.format(
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
