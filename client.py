import socket
import time
import util
from conn import MsgConnection, AcceptConnection
from message import WireMessage

class Peer(object):
    def __init__(self, ip, port, peer_id=None, conn=None):
        self.ip = ip
        self.port = port

        if peer_id:
            self.peer_id = peer_id
        else:
            seed = self.ip + str(time.time())
            self.peer_id = util.sha1_hash(self.ip) # Until handshake

        self.am_choking = True
        self.am_interested = False
        self.choking = True
        self.interested = False
        if conn:
            self.conn = MsgConnection(self, conn)
        else:
            self.conn = MsgConnection(self)
        
    def add_conn(self, conn):
        self.conn = conn

    def handshake(self, msg):
        print 'Received handshake:', msg, len(msg)
    def keep_alive(self):
        print 'Received keep-alive'
    def choke(self):
        self.choking = True
    def unchoke(self):
        self.choking = False
    def interested(self):
        self.interested = True
    def not_interested(self):
        self.interested = False
    def have(self, piece_index):
        pass
    def bitfield(self, bitfield):
        print 'Received bitfield'
    def request(self, index, begin, length):
        pass
    def piece(self, index, begin, block):
        pass
    def cancel(self, index, begin, length):
        pass
    def port(self, listen_port):
        pass

class Client(object):
    def __init__(self, torrent_list):
        self.peer_id = self._gen_peer_id()
        self.peers = {}
        self._pending_peers = []
        self.torrents = torrent_list
        self.torrent = torrent_list[0]
        self.conn = AcceptConnection(self)

    def handshake(self, new_conn, addr, msg):
        peer_id = msg[20:]
        self.peers[peer_id] = Peer(addr[0], addr[1], peer_id, conn)

    def start_serving(self, torrent):
        self.info_hashes[torrent] = torrent_file

    def stop_serving(self, torrent):
        del self.torrents[torrent]

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
