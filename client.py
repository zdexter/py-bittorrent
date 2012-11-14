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
        self._have = []

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

    def handshake(self, msg):
        print 'Received handshake resp from peer:', msg, len(msg)
        info_hash = msg[0:20]
        try:
            self.client.torrents[info_hash]
        except KeyError, e:
            print 'Closing conn; client not serving torrent {}.'.format(info_hash)
            self.conn.close()
        self.conn.enqueue_msg(WireMessage.construct_msg(2))
    def keep_alive(self):
        print 'Received keep-alive'
    def choke(self):
        print 'Received choke'
        self.choking = True
    def unchoke(self):
        print 'Received unchoke'
        self.choking = False
    def interested(self):
        print 'Received interested'
        self.interested = True
    def not_interested(self):
        print 'Received not interested';
        self.interested = False
    def have(self, piece_index):
        print 'Received have'
        piece_index = struct.unpack("i", piece_index)[0]
        self._have.append(piece_index)
    def _bits(self, data):
        data_bytes = (ord(b) for b in data)
        for b in data_bytes:
            """Get bit by reducing b by 2^i.
               Bitwise AND outputs 1s and 0s as strings.
            """
            for i in reversed(xrange(8)): # msb on left
                yield (b >> i) & 1
    def bitfield(self, bitfield):
        print 'Received bitfield'
        bitfield_length = len(bitfield)
        bits = ''.join(str(bit) for bit in self._bits(bitfield))
        # Trim spare bits
        pieces_length = len(self.client.torrent.pieces)
        # but first, sanity check: do peer & client expect same # of pieces?
        for bit in bits[pieces_length:]: # check extra bits only
            if bit == '1': raise Exception('Peer reporting too many pieces.')
        bits = bits[:pieces_length]
        # Modify torrent state with new information
        for i in range(len(bits)):
            bit = bits[i]
            if bit == '1':
                self.client.mark_piece(i,peer) 
    def request(self, index, begin, length):
        pass
    def piece(self, index, begin, block):
        pass
    def cancel(self, index, begin, length):
        pass
    def port(self, listen_port):
        pass

class Client(object):
    def __init__(self, torrents):
        self.peer_id = self._gen_peer_id()
        self.peers = {}
        self._pending_peers = []
        self.torrents = torrents
        self.torrent = torrents.itervalues().next()
        self.conn = AcceptConnection(self)

    def handshake(self, new_conn, addr, msg):
        peer_id = msg[20:]
        print 'Testing for peer existence:', self.peers[peer_id]
        self.peers[peer_id] = Peer(addr[0], addr[1], peer_id, conn)

    def start_serving(self, torrent, info_hash):
        self.torrents[info_hash] = torrent

    def stop_serving(self, info_hash):
        del self.torrents[info_hash]

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
